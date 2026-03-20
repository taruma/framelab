from __future__ import annotations

from dataclasses import dataclass

from run import (
    build_phase1_transparency_preview,
    build_phase2_transparency_preview,
    build_default_media_tags,
    find_duplicate_media_tags,
    merge_media_tag_map,
    markdown_to_plain_text,
    summarize_media_kind,
    summarize_media_tag_map,
    truncate_words,
    validate_media_sizes,
    validate_media_size,
)


@dataclass
class FakeUploadedFile:
    data: bytes
    name: str = "sample.mp4"
    type: str = "video/mp4"

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


def test_truncate_words_short_text_unchanged() -> None:
    text = "one two three"
    assert truncate_words(text, limit=5) == "one two three"


def test_truncate_words_long_text_adds_ellipsis() -> None:
    text = "one two three four five"
    assert truncate_words(text, limit=3) == "one two three ..."


def test_validate_media_size_ignores_non_video() -> None:
    image = FakeUploadedFile(data=b"x" * 100, name="a.png", type="image/png")
    assert validate_media_size(image, max_video_size_mb=1) == ""


def test_validate_media_size_rejects_video_above_limit() -> None:
    video = FakeUploadedFile(data=b"x" * (2 * 1024 * 1024), name="a.mp4", type="video/mp4")
    msg = validate_media_size(video, max_video_size_mb=1)
    assert "too large" in msg
    assert "up to 1 MB" in msg


def test_validate_media_sizes_prefixes_filename_for_multi_media_errors() -> None:
    video = FakeUploadedFile(data=b"x" * (2 * 1024 * 1024), name="big.mp4", type="video/mp4")
    image = FakeUploadedFile(data=b"x" * 100, name="still.png", type="image/png")

    errors = validate_media_sizes([video, image], max_video_size_mb=1)

    assert len(errors) == 1
    assert errors[0].startswith("big.mp4:")


def test_markdown_to_plain_text_strips_common_markdown() -> None:
    md = "# Title\n\n**bold** and _italic_ with [link](https://example.com)\n- item"
    plain = markdown_to_plain_text(md)
    assert "Title" in plain
    assert "bold" in plain
    assert "italic" in plain
    assert "link" in plain
    assert "- item" not in plain


def test_phase1_transparency_preview_contains_expected_meta_and_payload() -> None:
    meta, payload = build_phase1_transparency_preview(
        provider_label="OpenRouter",
        endpoint="https://openrouter.ai/api/v1",
        model="xiaomi/mimo-v2-omni",
        reasoning="low",
        system_prompt="You are a tester",
        initial_prompt="Analyze this frame",
        reference_media_kind="image",
    )
    assert meta["provider"] == "OpenRouter"
    assert meta["model"] == "xiaomi/mimo-v2-omni"
    assert len(payload) == 3


def test_phase1_transparency_preview_adds_media_tags_chip_in_multi_mode() -> None:
    _, payload = build_phase1_transparency_preview(
        provider_label="OpenAI",
        endpoint="https://api.openai.com/v1",
        model="gpt-5-mini",
        reasoning="low",
        system_prompt="System",
        initial_prompt="Analyze",
        reference_media_kind="2 items (2 images)",
        reference_media_tags="@image1=image, @character=image",
    )

    assert len(payload) == 4
    assert any("@character=image" in chip for chip in payload)


def test_phase2_transparency_preview_contains_previous_output_chip() -> None:
    _, payload = build_phase2_transparency_preview(
        provider_label="OpenAI",
        endpoint="https://api.openai.com/v1",
        model="gpt-5-mini",
        reasoning="low",
        system_prompt="System",
        phase1_output="Prior answer",
        correction_prompt="Please refine",
        correction_media_kind="video",
    )
    assert len(payload) == 5
    assert any("Prior answer" in chip for chip in payload)


def test_build_default_media_tags_counts_images_and_videos_separately() -> None:
    items = [
        FakeUploadedFile(data=b"a", name="a.jpg", type="image/jpeg"),
        FakeUploadedFile(data=b"b", name="b.mp4", type="video/mp4"),
        FakeUploadedFile(data=b"c", name="c.png", type="image/png"),
    ]

    tags = build_default_media_tags(items)

    assert tags == ["@image1", "@video1", "@image2"]


def test_summarize_media_kind_uses_single_and_multi_formats() -> None:
    one = FakeUploadedFile(data=b"x", name="one.jpg", type="image/jpeg")
    multi = [
        FakeUploadedFile(data=b"x", name="one.jpg", type="image/jpeg"),
        FakeUploadedFile(data=b"y", name="two.mp4", type="video/mp4"),
    ]

    assert summarize_media_kind(None) == "not selected"
    assert summarize_media_kind(one) == "image"
    assert summarize_media_kind(multi) == "2 items (1 image, 1 video)"


def test_summarize_media_tag_map_omits_single_and_formats_multi_pairs() -> None:
    assert summarize_media_tag_map([{"tag": "@image1", "kind": "image"}]) == ""
    summary = summarize_media_tag_map(
        [
            {"tag": "@image1", "kind": "image"},
            {"tag": "@video1", "kind": "video"},
        ]
    )
    assert summary == "@image1=image, @video1=video"


def test_find_duplicate_media_tags_is_case_insensitive() -> None:
    dupes = find_duplicate_media_tags(
        [
            {"tag": "@Character", "kind": "image"},
            {"tag": "@character", "kind": "video"},
            {"tag": "@bg", "kind": "image"},
        ]
    )
    assert dupes == ["@Character", "@character"]


def test_merge_media_tag_map_preserves_existing_and_assigns_defaults_to_new() -> None:
    existing = {
        "a.jpg:10:image/jpeg": "@character",
        "removed.jpg:20:image/jpeg": "@old",
    }
    signatures = ["a.jpg:10:image/jpeg", "b.jpg:11:image/jpeg"]
    defaults = ["@image1", "@image2"]

    merged = merge_media_tag_map(existing, signatures, defaults)

    assert merged == {
        "a.jpg:10:image/jpeg": "@character",
        "b.jpg:11:image/jpeg": "@image2",
    }
