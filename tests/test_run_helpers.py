from __future__ import annotations

from dataclasses import dataclass

from run import (
    build_phase1_transparency_preview,
    build_phase2_transparency_preview,
    markdown_to_plain_text,
    truncate_words,
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
