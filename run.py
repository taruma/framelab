import os
import re
import json
import sys
import tomllib
import html as html_lib
from pathlib import Path
from typing import Any, Tuple

import streamlit as st
from streamlit.components.v1 import html as st_html
from openai import OpenAI

from app_state import (
    CONVERSATION_MESSAGES,
    IS_PROCESSING,
    LAST_ERROR,
    PENDING_ACTION,
    PHASE1_DONE,
    PHASE1_EDITED_BY_USER,
    PHASE1_OUTPUT,
    PHASE1_REASONING,
    PHASE1_USAGE,
    PHASE2_EDITED_BY_USER,
    PHASE2_OUTPUT,
    PHASE2_REASONING,
    PHASE2_USAGE,
    PREFER_RESPONSES_API,
    init_state,
)
from conversation import make_user_message
from llm_streaming import stream_response


DEFAULT_APP_CONFIG = {
    "defaults": {
        "provider": "",
        "reasoning_effort": "low",
    },
    "prompts": {
        "system_dir": "prompts/system",
        "initial_dir": "prompts/initial",
        "correction_dir": "prompts/correction",
        "default_system": "",
        "default_initial": "",
        "default_correction": "",
    },
    "notices": [],
    "providers": {},
}

TRANSPARENCY_PREVIEW_WORDS = 30
MAX_VIDEO_UPLOAD_MB = 30
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
SUPPORTED_VIDEO_TYPES = ["mp4"]
SUPPORTED_MEDIA_TYPES = SUPPORTED_IMAGE_TYPES + SUPPORTED_VIDEO_TYPES
DEFAULT_INITIAL_PROMPT = "Analyze this reference image in highly detailed technical and creative terms."
DEFAULT_CORRECTION_PROMPT = "Use this new media and refinement notes to refine your previous analysis."
ALLOWED_BADGE_COLORS = {"blue", "green", "orange", "red", "violet", "gray"}


@st.cache_resource
def load_spacy_pos_tagger() -> Any:
    import spacy

    return spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer"])


def _escape_streamlit_color_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


FENCED_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
INLINE_PROTECTED_MD_RE = re.compile(
    r"(`[^`\n]+`|!\[[^\]]*\]\([^\)]*\)|\[[^\]]+\]\([^\)]*\)|\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|_[^_\n]+_|~~[^~\n]+~~)"
)
LINE_PREFIX_MD_RE = re.compile(r"^(\s{0,3}(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+))")


def _highlight_plain_segment_with_pos(
    nlp: Any,
    text: str,
    highlight_pos_tags: set[str],
    color_map: dict[str, str],
) -> str:
    if not text.strip():
        return text

    doc = nlp(text)
    chunks: list[str] = []
    for token in doc:
        token_text = _escape_streamlit_color_text(token.text)
        color = color_map.get(token.pos_)
        if color and token.pos_ in highlight_pos_tags:
            chunks.append(f":{color}[{token_text}]")
        else:
            chunks.append(token_text)
        chunks.append(token.whitespace_)

    return "".join(chunks)


def _highlight_markdown_aware_with_pos(
    nlp: Any,
    text: str,
    highlight_pos_tags: set[str],
    color_map: dict[str, str],
) -> str:
    def highlight_non_fenced_text(non_fenced_text: str) -> str:
        highlighted_lines: list[str] = []
        for line in non_fenced_text.splitlines(keepends=True):
            prefix_match = LINE_PREFIX_MD_RE.match(line)
            if prefix_match:
                prefix = prefix_match.group(1)
                rest = line[len(prefix):]
            else:
                prefix = ""
                rest = line

            parts = INLINE_PROTECTED_MD_RE.split(rest)
            rebuilt_parts: list[str] = []
            for idx, part in enumerate(parts):
                if not part:
                    continue
                if idx % 2 == 1:
                    rebuilt_parts.append(part)
                else:
                    rebuilt_parts.append(
                        _highlight_plain_segment_with_pos(nlp, part, highlight_pos_tags, color_map)
                    )

            highlighted_lines.append(prefix + "".join(rebuilt_parts))

        return "".join(highlighted_lines)

    result_parts: list[str] = []
    last_end = 0
    for match in FENCED_CODE_BLOCK_RE.finditer(text):
        before = text[last_end:match.start()]
        if before:
            result_parts.append(highlight_non_fenced_text(before))
        result_parts.append(match.group(0))
        last_end = match.end()

    tail = text[last_end:]
    if tail:
        result_parts.append(highlight_non_fenced_text(tail))

    return "".join(result_parts)


def pos_highlight_to_markdown(text: str, highlight_pos_tags: set[str]) -> tuple[str, str]:
    try:
        nlp = load_spacy_pos_tagger()
    except ImportError:
        return "", (
            "spaCy is not installed. Run `uv sync` (or install dependencies) and retry."
        )
    except Exception as exc:
        if "Can't find model 'en_core_web_sm'" in str(exc):
            return "", (
                "spaCy model `en_core_web_sm` is missing. Run `uv sync` to install project "
                "dependencies (including the model wheel), then retry."
            )
        return "", f"POS highlighter unavailable: {exc}"

    if not highlight_pos_tags:
        return text, ""

    color_map = {
        "VERB": "red-background",
        "ADJ": "blue-background",
        "NOUN": "green-background",
    }

    try:
        return _highlight_markdown_aware_with_pos(nlp, text, highlight_pos_tags, color_map), ""
    except Exception as exc:
        return "", f"POS parsing failed: {exc}"


def render_answer_with_optional_pos_highlight(
    answer_placeholder: st.delta_generator.DeltaGenerator,
    note_placeholder: st.delta_generator.DeltaGenerator,
    text: str,
    enable_highlight: bool,
    selected_pos_tags: set[str],
) -> None:
    if not enable_highlight or not selected_pos_tags or not text.strip():
        note_placeholder.empty()
        answer_placeholder.markdown(text)
        return

    highlighted_text, error = pos_highlight_to_markdown(text, selected_pos_tags)
    if error:
        note_placeholder.warning(error)
        answer_placeholder.markdown(text)
        return

    selected_labels = []
    if "VERB" in selected_pos_tags:
        selected_labels.append(":red-background[Verb]")
    if "ADJ" in selected_pos_tags:
        selected_labels.append(":blue-background[Adjective]")
    if "NOUN" in selected_pos_tags:
        selected_labels.append(":green-background[Noun]")

    note_placeholder.caption(
        "POS highlight (English only): " + " ".join(selected_labels)
    )
    answer_placeholder.markdown(highlighted_text)


def render_usage(usage: dict | None, placeholder: st.delta_generator.DeltaGenerator) -> None:
    placeholder.caption(build_usage_caption(usage))


def build_usage_caption(usage: dict | None) -> str:
    if not usage:
        return "Usage: not returned by this model/provider."

    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")

    parts = ["Usage"]
    if isinstance(input_tokens, int):
        parts.append(f"input: {input_tokens}")
    if isinstance(output_tokens, int):
        parts.append(f"output: {output_tokens}")
    if isinstance(total_tokens, int):
        parts.append(f"total: {total_tokens}")

    return " · ".join(parts)


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def truncate_words(text: str, limit: int = TRANSPARENCY_PREVIEW_WORDS) -> str:
    compact = one_line(text)
    if not compact:
        return ""
    words = compact.split(" ")
    if len(words) <= limit:
        return compact
    return " ".join(words[:limit]) + " ..."


def transparency_chip(label: str, color: str, content: str) -> str:
    safe_content = html_lib.escape(content)
    return (
        f"<span style='color:{color};font-weight:600'>[{safe_content}]</span>"
        if content
        else f"<span style='color:{color};font-weight:600'>[...]</span>"
    )


def get_media_kind(uploaded_file: Any) -> str:
    if uploaded_file is None:
        return "not selected"
    mime = getattr(uploaded_file, "type", "") or ""
    return "video" if mime.startswith("video/") else "image"


def normalize_uploaded_files(uploaded_files: Any) -> list[Any]:
    if uploaded_files is None:
        return []
    if isinstance(uploaded_files, list):
        return [f for f in uploaded_files if f is not None]
    return [uploaded_files]


def build_default_media_tags(uploaded_files: list[Any]) -> list[str]:
    image_count = 0
    video_count = 0
    tags: list[str] = []

    for uploaded in uploaded_files:
        if get_media_kind(uploaded) == "video":
            video_count += 1
            tags.append(f"@video{video_count}")
        else:
            image_count += 1
            tags.append(f"@image{image_count}")

    return tags


def summarize_media_kind(uploaded_files: Any) -> str:
    files = normalize_uploaded_files(uploaded_files)
    if not files:
        return "not selected"
    if len(files) == 1:
        return get_media_kind(files[0])

    image_count = sum(1 for f in files if get_media_kind(f) == "image")
    video_count = len(files) - image_count
    parts: list[str] = []
    if image_count:
        parts.append(f"{image_count} image{'s' if image_count > 1 else ''}")
    if video_count:
        parts.append(f"{video_count} video{'s' if video_count > 1 else ''}")

    return f"{len(files)} items ({', '.join(parts)})"


def summarize_media_tag_map(media_items: list[dict[str, Any]]) -> str:
    if len(media_items) <= 1:
        return ""

    pairs: list[str] = []
    for item in media_items:
        tag = str(item.get("tag", "")).strip()
        kind = str(item.get("kind", "media")).strip() or "media"
        if tag:
            pairs.append(f"{tag}={kind}")

    return ", ".join(pairs)


def find_duplicate_media_tags(media_items: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: set[str] = set()

    for item in media_items:
        tag = str(item.get("tag", "")).strip()
        if not tag:
            continue

        normalized = tag.lower()
        if normalized in seen:
            duplicates.add(seen[normalized])
            duplicates.add(tag)
        else:
            seen[normalized] = tag

    return sorted(duplicates)


def make_media_signature(uploaded_file: Any) -> str:
    return (
        f"{getattr(uploaded_file, 'name', '')}:"
        f"{getattr(uploaded_file, 'size', '')}:"
        f"{getattr(uploaded_file, 'type', '')}"
    )


def merge_media_tag_map(
    existing_tag_map: dict[str, str],
    signatures: list[str],
    default_tags: list[str],
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for idx, signature in enumerate(signatures):
        existing = str(existing_tag_map.get(signature, "")).strip()
        merged[signature] = existing or default_tags[idx]
    return merged


def collect_tagged_media_inputs(
    uploaded_files: Any,
    *,
    phase_key_prefix: str,
) -> list[dict[str, Any]]:
    files = normalize_uploaded_files(uploaded_files)
    default_tags = build_default_media_tags(files)

    tag_map_key = f"{phase_key_prefix}_media_tag_map"
    existing_tag_map = st.session_state.get(tag_map_key, {})
    if not isinstance(existing_tag_map, dict):
        existing_tag_map = {}

    signatures = [make_media_signature(f) for f in files]
    merged_tag_map = merge_media_tag_map(existing_tag_map, signatures, default_tags)
    st.session_state[tag_map_key] = merged_tag_map

    items: list[dict[str, Any]] = []
    for idx, uploaded in enumerate(files):
        kind = get_media_kind(uploaded)
        source_name = str(getattr(uploaded, "name", "")).strip() or f"media_{idx + 1}"
        signature = signatures[idx]
        final_tag = merged_tag_map.get(signature, default_tags[idx])
        items.append(
            {
                "file": uploaded,
                "tag": final_tag,
                "kind": kind,
                "name": source_name,
                "signature": signature,
                "default_tag": default_tags[idx],
            }
        )

    return items


def render_multi_media_thumbnail_strip(media_items: list[dict[str, Any]]) -> None:
    if not media_items:
        return

    col_count = min(4, len(media_items))
    cols = st.columns(col_count, gap="small")

    for idx, item in enumerate(media_items):
        with cols[idx % col_count]:
            if item["kind"] == "video":
                st.markdown("🎬 **Video**")
                st.caption(item["name"])
            else:
                st.image(item["file"], width=130)
            st.caption(item["tag"])


def media_dialog_input_key(phase_key_prefix: str, signature: str) -> str:
    safe_signature = re.sub(r"[^a-zA-Z0-9_]", "_", signature)
    return f"{phase_key_prefix}_media_dialog_tag_{safe_signature}"


def clear_media_dialog_inputs(phase_key_prefix: str, media_items: list[dict[str, Any]]) -> None:
    for item in media_items:
        st.session_state.pop(media_dialog_input_key(phase_key_prefix, item["signature"]), None)


def render_media_tag_dialog_body(
    *,
    phase_key_prefix: str,
    media_items: list[dict[str, Any]],
    ui_locked: bool,
) -> None:
    if not media_items:
        st.info("No media uploaded.")
        if st.button("Close", key=f"{phase_key_prefix}_media_dialog_close_empty", width="stretch"):
            clear_media_dialog_inputs(phase_key_prefix, media_items)
            st.rerun()
        return

    st.caption("Edit tags below. Full-size previews are shown in this dialog.")

    for idx, item in enumerate(media_items):
        st.markdown(f"**{idx + 1}. {item['name']}**")
        if item["kind"] == "video":
            st.video(item["file"])
        else:
            st.image(item["file"], width="stretch")

        input_key = media_dialog_input_key(phase_key_prefix, item["signature"])
        if input_key not in st.session_state:
            st.session_state[input_key] = item["tag"]

        st.text_input(
            "Tag/annotation",
            key=input_key,
            disabled=ui_locked,
            help="Used in request payload to reference this media item.",
        )
        st.divider()

    apply_col, cancel_col = st.columns(2)
    if apply_col.button("Apply tags", type="primary", disabled=ui_locked, width="stretch"):
        updated_map: dict[str, str] = {}
        for item in media_items:
            input_key = media_dialog_input_key(phase_key_prefix, item["signature"])
            typed = str(st.session_state.get(input_key, "")).strip()
            updated_map[item["signature"]] = typed or item["default_tag"]
        st.session_state[f"{phase_key_prefix}_media_tag_map"] = updated_map
        clear_media_dialog_inputs(phase_key_prefix, media_items)
        st.rerun()

    if cancel_col.button("Cancel", disabled=ui_locked, width="stretch"):
        clear_media_dialog_inputs(phase_key_prefix, media_items)
        st.rerun()


@st.dialog("Manage Phase 1 Media Tags")
def manage_phase1_media_dialog(media_items: list[dict[str, Any]], ui_locked: bool) -> None:
    render_media_tag_dialog_body(
        phase_key_prefix="phase1",
        media_items=media_items,
        ui_locked=ui_locked,
    )


@st.dialog("Manage Phase 2 Media Tags")
def manage_phase2_media_dialog(media_items: list[dict[str, Any]], ui_locked: bool) -> None:
    render_media_tag_dialog_body(
        phase_key_prefix="phase2",
        media_items=media_items,
        ui_locked=ui_locked,
    )


def make_request_media_input(media_items: list[dict[str, Any]]) -> Any:
    if not media_items:
        return None

    if len(media_items) == 1:
        return media_items[0]["file"]

    return [{"file": item["file"], "tag": item.get("tag", "")} for item in media_items]


def validate_media_size(uploaded_file: Any, max_video_size_mb: int = MAX_VIDEO_UPLOAD_MB) -> str:
    if uploaded_file is None:
        return ""

    if get_media_kind(uploaded_file) != "video":
        return ""

    max_bytes = max_video_size_mb * 1024 * 1024
    file_size = getattr(uploaded_file, "size", None)
    if not isinstance(file_size, int):
        try:
            file_size = len(uploaded_file.getvalue())
        except Exception:
            file_size = None

    if isinstance(file_size, int) and file_size > max_bytes:
        actual_mb = file_size / (1024 * 1024)
        return (
            f"Uploaded video is too large ({actual_mb:.1f} MB). "
            f"Please upload an MP4 up to {max_video_size_mb} MB."
        )
    return ""


def validate_media_sizes(uploaded_files: Any, max_video_size_mb: int = MAX_VIDEO_UPLOAD_MB) -> list[str]:
    files = normalize_uploaded_files(uploaded_files)
    errors: list[str] = []
    for idx, uploaded in enumerate(files):
        err = validate_media_size(uploaded, max_video_size_mb=max_video_size_mb)
        if not err:
            continue

        if len(files) == 1:
            errors.append(err)
            continue

        source_name = str(getattr(uploaded, "name", "")).strip() or f"media_{idx + 1}"
        errors.append(f"{source_name}: {err}")

    return errors


def render_transparency_block(
    metadata: dict[str, str],
    payload_chips: list[str],
    *,
    key: str,
    expanded: bool = True,
) -> None:
    with st.expander("🔎 Request Transparency", expanded=expanded):
        metadata_line = (
            "<div style='font-size:0.86rem;line-height:1.35;'>"
            "⚙️ "
            f"<span style='color:#60a5fa;'><b>{html_lib.escape(metadata.get('provider', '-'))}</b></span>"
            " · "
            f"<span style='color:#f59e0b;'><i>{html_lib.escape(metadata.get('endpoint', '-'))}</i></span>"
            " · "
            f"<span style='color:#34d399;'><b>{html_lib.escape(metadata.get('model', '-'))}</b></span>"
            " · "
            f"<span style='color:#a78bfa;'><u>{html_lib.escape(metadata.get('reasoning', '-'))}</u></span>"
            "</div>"
        )
        payload_line = (
            "<div style='font-size:0.86rem;line-height:1.45;'>"
            "📦 " + " + ".join(payload_chips) +
            "</div>"
        )
        st.markdown(metadata_line, unsafe_allow_html=True)
        st.markdown(payload_line, unsafe_allow_html=True)


def build_phase1_transparency_preview(
    provider_label: str,
    endpoint: str,
    model: str,
    reasoning: str,
    system_prompt: str,
    initial_prompt: str,
    reference_media_kind: str,
    reference_media_tags: str = "",
) -> tuple[dict[str, str], list[str]]:
    initial_user_text = initial_prompt.strip()
    meta = {
        "provider": provider_label or "-",
        "endpoint": endpoint or "-",
        "model": model or "-",
        "reasoning": reasoning or "-",
    }
    payload = [
        transparency_chip("system", "#60a5fa", truncate_words(system_prompt)),
        transparency_chip("reference media", "#f59e0b", reference_media_kind),
    ]
    if reference_media_tags:
        payload.append(transparency_chip("media tags", "#f97316", truncate_words(reference_media_tags)))
    payload.append(transparency_chip("prompt/context", "#34d399", truncate_words(initial_user_text)))
    return meta, payload


def build_phase2_transparency_preview(
    provider_label: str,
    endpoint: str,
    model: str,
    reasoning: str,
    system_prompt: str,
    phase1_output: str,
    correction_prompt: str,
    correction_media_kind: str,
    correction_media_tags: str = "",
) -> tuple[dict[str, str], list[str]]:
    correction_text = correction_prompt.strip()
    meta = {
        "provider": provider_label or "-",
        "endpoint": endpoint or "-",
        "model": model or "-",
        "reasoning": reasoning or "-",
    }
    payload = [
        transparency_chip("system", "#60a5fa", truncate_words(system_prompt)),
        transparency_chip("reference context", "#f59e0b", "image/video/text"),
        transparency_chip("previous output", "#a78bfa", truncate_words(phase1_output)),
        transparency_chip("correction media", "#f59e0b", correction_media_kind),
    ]
    if correction_media_tags:
        payload.append(transparency_chip("media tags", "#f97316", truncate_words(correction_media_tags)))
    payload.append(transparency_chip("correction notes", "#34d399", truncate_words(correction_text)))
    return meta, payload


def load_env_file(path: str = ".env") -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass


def load_system_prompt(path: str = "system_prompt.txt") -> Tuple[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip(), ""
    except FileNotFoundError:
        return "", f"System prompt file not found: {path}"
    except OSError as exc:
        return "", f"Failed to read system prompt file ({path}): {exc}"


def load_prompt_presets(directory: str) -> tuple[list[dict], str]:
    directory_path = Path(directory)
    if not directory_path.exists():
        return [], f"Prompt preset directory not found: {directory}"
    if not directory_path.is_dir():
        return [], f"Prompt preset path is not a directory: {directory}"

    presets: list[dict] = []
    warnings: list[str] = []

    for txt_path in sorted(directory_path.glob("*.txt")):
        try:
            content = txt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            warnings.append(f"Failed reading preset '{txt_path.name}': {exc}")
            continue

        meta = {}
        meta_path = txt_path.with_suffix(".meta.toml")
        if meta_path.exists():
            try:
                with meta_path.open("rb") as f:
                    parsed = tomllib.load(f)
                if isinstance(parsed, dict):
                    meta = parsed
            except Exception as exc:
                warnings.append(f"Invalid metadata '{meta_path.name}': {exc}")

        title = str(meta.get("title", "")).strip() or txt_path.stem.replace("_", " ").replace("-", " ").title()
        description = str(meta.get("description", "")).strip()
        order = meta.get("order", 1000)
        try:
            order = int(order)
        except Exception:
            order = 1000

        presets.append(
            {
                "filename": txt_path.name,
                "title": title,
                "description": description,
                "content": content,
                "order": order,
            }
        )

    presets.sort(key=lambda p: (p["order"], p["title"].lower(), p["filename"].lower()))

    warning_message = "\n".join(warnings)
    return presets, warning_message


def pick_default_preset(options: list[dict], default_filename: str) -> dict | None:
    if not options:
        return None
    for preset in options:
        if preset["filename"] == default_filename:
            return preset
    return options[0]


def init_textarea_state(key: str, initial_value: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = initial_value


def load_hero(path: str = "hero.md") -> Tuple[str, str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip(), ""
    except FileNotFoundError:
        return "", f"Hero file not found: {path}"
    except OSError as exc:
        return "", f"Failed to read hero file ({path}): {exc}"


def normalize_notice_color(raw_color: Any) -> str:
    color = str(raw_color or "").strip().lower()
    return color if color in ALLOWED_BADGE_COLORS else "gray"


def build_notices_markdown_lines(notices: Any) -> list[str]:
    if not isinstance(notices, list):
        return []

    badges: list[str] = []
    for notice in notices:
        if not isinstance(notice, dict):
            continue

        enabled = notice.get("enabled", True)
        if enabled is False:
            continue

        text = str(notice.get("text", notice.get("label", ""))).strip()
        if not text:
            continue

        icon = str(notice.get("icon", "")).strip()
        color = normalize_notice_color(notice.get("color", "gray"))

        content = f"{icon} {text}".strip() if icon else text
        safe_content = _escape_streamlit_color_text(content)
        badges.append(f":{color}-badge[{safe_content}]")

    return badges


def load_app_config(path: str = "config.toml") -> tuple[dict, str]:
    try:
        with open(path, "rb") as f:
            loaded = tomllib.load(f)
        return loaded, ""
    except FileNotFoundError:
        return DEFAULT_APP_CONFIG, f"Config file not found: {path}. Using built-in defaults."
    except tomllib.TOMLDecodeError as exc:
        return DEFAULT_APP_CONFIG, f"Invalid TOML in {path}: {exc}. Using built-in defaults."
    except OSError as exc:
        return DEFAULT_APP_CONFIG, f"Failed to read config file ({path}): {exc}. Using built-in defaults."


def resolve_api_key(sidebar_key: str, provider_env_key: str) -> tuple[str, str]:
    typed_key = sidebar_key.strip()
    if typed_key:
        return typed_key, "sidebar input"

    provider_key = os.environ.get(provider_env_key, "").strip() if provider_env_key else ""
    if provider_key:
        return provider_key, f".env (`{provider_env_key}`)"

    generic_key = os.environ.get("LLM_API_KEY", "").strip()
    if generic_key:
        return generic_key, ".env (`LLM_API_KEY`)"

    legacy_key = os.environ.get("API_KEY", "").strip()
    if legacy_key:
        return legacy_key, ".env (`API_KEY`)"

    openai_legacy_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_legacy_key:
        return openai_legacy_key, ".env (`OPENAI_API_KEY`, legacy)"

    return "", "not found"


def markdown_to_plain_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n")
    cleaned = re.sub(r"```[\w+-]*\n?", "", cleaned)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s{0,3}>\s?", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*([-*_]\s*){3,}$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
    cleaned = re.sub(r"_(.*?)_", r"\1", cleaned)
    cleaned = re.sub(r"~~(.*?)~~", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def render_copy_buttons(
    plain_label: str,
    raw_label: str,
    text: str,
    key: str,
) -> None:
    copy_text_plain = markdown_to_plain_text(text)
    copy_text_raw = text or ""

    plain_button_id = f"copy-btn-plain-{key}"
    raw_button_id = f"copy-btn-raw-{key}"
    status_id = f"copy-status-{key}"

    st_html(
        f"""
        <div style=\"display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;margin-top:6px;width:100%;\">
          <div style=\"display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;\">
            <button id=\"{plain_button_id}\" style=\"padding:0.35rem 0.7rem;border:1px solid #555;border-radius:0.4rem;background:#1f1f1f;color:#f3f3f3;cursor:pointer;\">{html_lib.escape(plain_label)}</button>
            <button id=\"{raw_button_id}\" style=\"padding:0.35rem 0.7rem;border:1px solid #555;border-radius:0.4rem;background:#1f1f1f;color:#f3f3f3;cursor:pointer;\">{html_lib.escape(raw_label)}</button>
          </div>
          <span id=\"{status_id}\" style=\"font-size:0.85rem;color:#6c757d;\"></span>
        </div>
        <script>
          const textToCopyPlain = {json.dumps(copy_text_plain)};
          const textToCopyRaw = {json.dumps(copy_text_raw)};
          const plainBtn = document.getElementById({json.dumps(plain_button_id)});
          const rawBtn = document.getElementById({json.dumps(raw_button_id)});
          const status = document.getElementById({json.dumps(status_id)});

          async function copyWithStatus(textToCopy, successLabel) {{
            if (!status) return;
            try {{
              await navigator.clipboard.writeText(textToCopy);
              status.textContent = successLabel;
            }} catch (e) {{
              status.textContent = 'Copy failed';
            }}
            setTimeout(() => {{ status.textContent = ''; }}, 1200);
          }}

          if (plainBtn) {{
            plainBtn.onclick = async () => copyWithStatus(textToCopyPlain, 'Copied plain text');
          }}
          if (rawBtn) {{
            rawBtn.onclick = async () => copyWithStatus(textToCopyRaw, 'Copied as-is');
          }}
        </script>
        """,
        height=74,
    )


@st.dialog("Edit Phase 1 Output")
def edit_phase1_output_dialog(ui_locked: bool) -> None:
    st.text_area(
        "Edit Phase 1 markdown output",
        key="phase1_edit_text",
        height=320,
        disabled=ui_locked,
    )
    submit_col, cancel_col = st.columns(2)
    if submit_col.button("Submit changes", type="primary", disabled=ui_locked, width="stretch"):
        edited = st.session_state.get("phase1_edit_text", "")
        st.session_state[PHASE1_OUTPUT] = edited
        st.session_state[PHASE1_EDITED_BY_USER] = True

        messages = st.session_state.get(CONVERSATION_MESSAGES, [])
        for message in messages:
            if message.get("role") == "assistant":
                message["content"] = edited
                break

        st.rerun()
    if cancel_col.button("Cancel", disabled=ui_locked, width="stretch"):
        st.rerun()


@st.dialog("Edit Phase 2 Output")
def edit_phase2_output_dialog(ui_locked: bool) -> None:
    st.text_area(
        "Edit Phase 2 markdown output",
        key="phase2_edit_text",
        height=320,
        disabled=ui_locked,
    )
    submit_col, cancel_col = st.columns(2)
    if submit_col.button("Submit changes", type="primary", disabled=ui_locked, width="stretch"):
        edited = st.session_state.get("phase2_edit_text", "")
        st.session_state[PHASE2_OUTPUT] = edited
        st.session_state[PHASE2_EDITED_BY_USER] = True

        messages = st.session_state.get(CONVERSATION_MESSAGES, [])
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx].get("role") == "assistant":
                messages[idx]["content"] = edited
                break

        st.rerun()
    if cancel_col.button("Cancel", disabled=ui_locked, width="stretch"):
        st.rerun()


def render() -> None:
    st.set_page_config(page_title="FrameLab - Multimodal Analysis", layout="wide")
    init_state()
    load_env_file()
    app_config, config_error = load_app_config()

    file_prompt, prompt_error = load_system_prompt()
    hero_content, hero_error = load_hero()

    # Hero Section
    if hero_content:
        st.markdown(hero_content, unsafe_allow_html=True)
    elif hero_error:
        st.warning(hero_error)

    notices_markdown_lines = build_notices_markdown_lines(app_config.get("notices", []))
    if notices_markdown_lines:
        _, notices_center_col, _ = st.columns([1, 2.2, 1])
        with notices_center_col:
            for notice_line in notices_markdown_lines:
                st.markdown(notice_line, width="stretch", text_alignment="center")

    st.divider()

    providers = app_config.get("providers", {})
    defaults = app_config.get("defaults", {})
    prompts_cfg = app_config.get("prompts", {})

    system_dir = str(prompts_cfg.get("system_dir", "prompts/system")).strip() or "prompts/system"
    initial_dir = str(prompts_cfg.get("initial_dir", "prompts/initial")).strip() or "prompts/initial"
    correction_dir = str(prompts_cfg.get("correction_dir", "prompts/correction")).strip() or "prompts/correction"

    default_system_file = str(prompts_cfg.get("default_system", "")).strip()
    default_initial_file = str(prompts_cfg.get("default_initial", "")).strip()
    default_correction_file = str(prompts_cfg.get("default_correction", "")).strip()

    system_presets, system_presets_warning = load_prompt_presets(system_dir)
    initial_presets, initial_presets_warning = load_prompt_presets(initial_dir)
    correction_presets, correction_presets_warning = load_prompt_presets(correction_dir)

    default_system_preset = pick_default_preset(system_presets, default_system_file)
    default_initial_preset = pick_default_preset(initial_presets, default_initial_file)
    default_correction_preset = pick_default_preset(correction_presets, default_correction_file)
    provider_ids = list(providers.keys())
    default_provider_id = defaults.get("provider", provider_ids[0] if provider_ids else "")
    if default_provider_id not in providers and provider_ids:
        default_provider_id = provider_ids[0]

    with st.sidebar:
        st.header("Settings")

        ui_locked = st.session_state[IS_PROCESSING]

        if config_error:
            st.warning(config_error)

        with st.expander("API Setup", expanded=True):
            if not provider_ids:
                st.error("No providers found in config.toml. Please add at least one provider.")
                return

            default_provider_index = provider_ids.index(default_provider_id)
            selected_provider_id = st.selectbox(
                "Provider",
                options=provider_ids,
                index=default_provider_index,
                format_func=lambda pid: providers.get(pid, {}).get("label", pid),
                disabled=ui_locked,
            )
            selected_provider = providers.get(selected_provider_id, {})
            selected_provider_label = selected_provider.get("label", selected_provider_id)

            provider_default_base_url = str(selected_provider.get("base_url", "")).strip()
            provider_default_model = str(selected_provider.get("default_model", "")).strip()
            provider_env_key = str(selected_provider.get("env_key", "")).strip()
            provider_models = selected_provider.get("models", []) or []
            provider_models = [str(m).strip() for m in provider_models if str(m).strip()]
            if provider_default_model and provider_default_model not in provider_models:
                provider_models.insert(0, provider_default_model)
            model_default_index = (
                provider_models.index(provider_default_model)
                if provider_default_model and provider_default_model in provider_models
                else 0
            )

            api_key_input = st.text_input("API Key", type="password", disabled=ui_locked)
            effective_api_key, api_key_source = resolve_api_key(api_key_input, provider_env_key)
            if effective_api_key:
                st.caption(f"API key source: {api_key_source}")
            else:
                st.caption(
                    "No API key found. Use sidebar input or set one of: "
                    f"`{provider_env_key}` / `LLM_API_KEY` / `API_KEY` / `OPENAI_API_KEY`."
                )

            base_url_input = st.text_input(
                "Base URL / Endpoint",
                value=provider_default_base_url,
                disabled=ui_locked,
            )
            model_from_list = st.selectbox(
                "Model",
                options=provider_models or [provider_default_model],
                index=model_default_index,
                disabled=ui_locked,
            )
            model_input = st.text_input("Model Override (optional)", value="", disabled=ui_locked)
            reasoning_effort_input = st.selectbox(
                "Reasoning Effort",
                options=["none", "minimal", "low", "medium", "high"],
                index=["none", "minimal", "low", "medium", "high"].index(
                    defaults.get("reasoning_effort", "low")
                    if defaults.get("reasoning_effort", "low") in ["none", "minimal", "low", "medium", "high"]
                    else "low"
                ),
                help="For reasoning-capable models/providers. The selected value is sent as-is.",
                disabled=ui_locked,
            )

            effective_base_url = base_url_input.strip() or provider_default_base_url
            effective_model = model_input.strip() or model_from_list or provider_default_model
            effective_reasoning_effort = reasoning_effort_input

        st.divider()
        st.markdown("#### System Prompt")

        system_options = [p["filename"] for p in system_presets]
        default_system_index = (
            system_options.index(default_system_preset["filename"])
            if (default_system_preset and default_system_preset["filename"] in system_options)
            else 0
        )
        selected_system_file = st.selectbox(
            "System Prompt Preset",
            options=system_options,
            index=default_system_index,
            format_func=lambda fn: next((p["title"] for p in system_presets if p["filename"] == fn), fn),
            disabled=ui_locked or not system_options,
        ) if system_options else ""

        selected_system_preset = next((p for p in system_presets if p["filename"] == selected_system_file), None)
        selected_system_content = selected_system_preset["content"] if selected_system_preset else ""
        selected_system_description = selected_system_preset["description"] if selected_system_preset else ""

        if selected_system_description:
            st.caption(selected_system_description)

        system_prompt_override = st.text_area(
            "System Prompt Override (optional)",
            value="",
            placeholder="Leave empty to use selected system preset",
            height=180,
            disabled=ui_locked,
        )
        effective_system_prompt = system_prompt_override.strip() or selected_system_content or file_prompt

        if system_presets_warning:
            st.warning(system_presets_warning)
        if prompt_error and not selected_system_content:
            st.warning(prompt_error)

        if selected_system_content:
            st.caption(f"Loaded system prompt preset from `{system_dir}/{selected_system_file}`")
        elif not prompt_error:
            st.caption("Loaded fallback default system prompt from `system_prompt.txt`.")

        st.caption(
            "System prompt in use: "
            f"{'Sidebar override' if system_prompt_override.strip() else ('Selected preset' if selected_system_content else 'system_prompt.txt fallback')}"
        )

    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader(":material/photo_camera: Phase 1 · Primary Analysis")
        original_image = st.file_uploader(
            "Original Reference Media (image/video, optional, one or more)",
            type=SUPPORTED_MEDIA_TYPES,
            key="original_image",
            accept_multiple_files=True,
            disabled=ui_locked,
        )
        st.caption(
            "Optional upload: you can use text-only chat mode, or include one or more media items for multimodal analysis. "
            "Allowed formats: image (PNG/JPG/JPEG/WEBP) or video (MP4 only). "
            f"App-enforced video limit: {MAX_VIDEO_UPLOAD_MB} MB. "
            "Image size follows provider/endpoint limits."
        )
        phase1_media_errors = validate_media_sizes(original_image)
        for media_error in phase1_media_errors:
            st.error(media_error)

        phase1_media_items = collect_tagged_media_inputs(
            original_image,
            phase_key_prefix="phase1",
        )
        if len(phase1_media_items) == 1:
            single_item = phase1_media_items[0]
            if single_item["kind"] == "video":
                st.video(single_item["file"])
            else:
                st.image(single_item["file"], caption="Original image preview", width="stretch")
        elif len(phase1_media_items) > 1:
            st.caption("Multiple media detected. Showing compact thumbnails; open dialog for full-size preview + tags.")
            render_multi_media_thumbnail_strip(phase1_media_items)
            if st.button(
                "Manage media tags",
                key="phase1_manage_media_tags",
                disabled=ui_locked,
                width="stretch",
            ):
                manage_phase1_media_dialog(phase1_media_items, ui_locked)

        phase1_duplicate_tags = find_duplicate_media_tags(phase1_media_items)
        if phase1_duplicate_tags:
            st.warning(
                "Duplicate media tags detected: "
                + ", ".join(phase1_duplicate_tags)
                + ". Duplicate tags may reduce clarity in model references."
            )

        phase1_media_kind_summary = summarize_media_kind(original_image)
        phase1_media_tag_summary = summarize_media_tag_map(phase1_media_items)
        initial_options = [p["filename"] for p in initial_presets]
        default_initial_index = (
            initial_options.index(default_initial_preset["filename"])
            if (default_initial_preset and default_initial_preset["filename"] in initial_options)
            else 0
        )
        initial_preset_col, initial_load_col = st.columns([5, 1.25], gap="small")
        with initial_preset_col:
            selected_initial_file = st.selectbox(
                "Initial Prompt Preset",
                options=initial_options,
                index=default_initial_index,
                format_func=lambda fn: next((p["title"] for p in initial_presets if p["filename"] == fn), fn),
                disabled=ui_locked or not initial_options,
            ) if initial_options else ""
        selected_initial_preset = next((p for p in initial_presets if p["filename"] == selected_initial_file), None)
        selected_initial_content = selected_initial_preset["content"] if selected_initial_preset else ""
        selected_initial_description = selected_initial_preset["description"] if selected_initial_preset else ""
        if selected_initial_description:
            st.caption(selected_initial_description)
        if initial_presets_warning:
            st.warning(initial_presets_warning)

        init_textarea_state("initial_prompt_text", "")

        with initial_load_col:
            st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)
            load_initial_clicked = st.button(
                "Load",
                key="load_initial_preset",
                disabled=ui_locked or not initial_options,
                help="Load selected preset into the Initial Prompt text box.",
                width="stretch",
            )
        if load_initial_clicked:
            st.session_state["initial_prompt_text"] = selected_initial_content or DEFAULT_INITIAL_PROMPT

        initial_prompt = st.text_area(
            "Initial Prompt",
            key="initial_prompt_text",
            height=140,
            disabled=ui_locked,
        )

        effective_initial_prompt = initial_prompt

        phase1_meta_preview, phase1_payload_preview = build_phase1_transparency_preview(
            provider_label=str(selected_provider_label),
            endpoint=effective_base_url,
            model=effective_model,
            reasoning=effective_reasoning_effort,
            system_prompt=effective_system_prompt,
            initial_prompt=effective_initial_prompt,
            reference_media_kind=phase1_media_kind_summary,
            reference_media_tags=phase1_media_tag_summary,
        )
        render_transparency_block(
            phase1_meta_preview,
            phase1_payload_preview,
            key="phase1_transparency_preview",
        )

        analyze_clicked = st.button("Analyze", type="primary", width="stretch", disabled=ui_locked)

    with right_col:
        st.subheader(":material/description: Phase 1 Output")
        phase1_highlight_enabled = st.checkbox(
            "Highlight POS (EN only): verbs / adjectives / nouns",
            key="phase1_pos_highlight",
            value=False,
        )
        phase1_pos_options = {
            "Verb": "VERB",
            "Adjective": "ADJ",
            "Noun": "NOUN",
        }
        phase1_selected_labels = st.multiselect(
            "POS types to highlight",
            options=list(phase1_pos_options.keys()),
            default=list(phase1_pos_options.keys()),
            key="phase1_pos_types",
            disabled=not phase1_highlight_enabled,
        )
        phase1_selected_tags = {phase1_pos_options[label] for label in phase1_selected_labels}
        phase1_thought_expander = st.expander(":material/psychology: Thought Process", expanded=True)
        phase1_thought_placeholder = phase1_thought_expander.empty()
        phase1_answer_placeholder = st.empty()
        phase1_pos_note_placeholder = st.empty()

        if st.session_state[PHASE1_REASONING]:
            phase1_thought_placeholder.markdown(st.session_state[PHASE1_REASONING])
        if st.session_state[PHASE1_OUTPUT]:
            render_answer_with_optional_pos_highlight(
                phase1_answer_placeholder,
                phase1_pos_note_placeholder,
                st.session_state[PHASE1_OUTPUT],
                phase1_highlight_enabled,
                phase1_selected_tags,
            )
            phase1_usage_col, phase1_edit_col = st.columns([8, 1.6], gap="small", vertical_alignment="center")
            with phase1_usage_col:
                usage_caption = build_usage_caption(st.session_state[PHASE1_USAGE])
                if st.session_state[PHASE1_EDITED_BY_USER]:
                    usage_caption += " · Edited by user"
                st.caption(usage_caption)
            with phase1_edit_col:
                if st.button("✏️ Edit", key="phase1_edit_button", help="Edit output", disabled=ui_locked):
                    st.session_state["phase1_edit_text"] = st.session_state[PHASE1_OUTPUT]
                    edit_phase1_output_dialog(ui_locked)

            render_copy_buttons(
                "Copy Plain Text",
                "Copy Markdown",
                st.session_state[PHASE1_OUTPUT],
                key="phase1_copy_button",
            )

    if analyze_clicked and not ui_locked:
        if not effective_api_key:
            st.error("Please provide an API key in sidebar or set provider key / LLM_API_KEY / API_KEY in .env.")
            return
        if not effective_model:
            st.error("Please provide a model name.")
            return
        if phase1_media_errors:
            return

        st.session_state[LAST_ERROR] = ""
        st.session_state[IS_PROCESSING] = True
        st.session_state[PENDING_ACTION] = "phase1"
        st.rerun()

    if st.session_state[PENDING_ACTION] == "phase1":
        client = OpenAI(api_key=effective_api_key, base_url=effective_base_url)
        messages = []
        if effective_system_prompt.strip():
            messages.append({"role": "system", "content": effective_system_prompt.strip()})

        initial_user_text = effective_initial_prompt.strip()
        initial_request_media = make_request_media_input(phase1_media_items)
        initial_user_message = make_user_message(initial_request_media, initial_user_text)
        messages.append(initial_user_message)

        try:
            with st.spinner("Generating response..."):
                answer, thought, usage, prefer_responses_api = stream_response(
                    client,
                    effective_model,
                    messages,
                    phase1_thought_placeholder,
                    phase1_answer_placeholder,
                    reasoning_effort=effective_reasoning_effort,
                    prefer_responses_api=st.session_state[PREFER_RESPONSES_API],
                )
            st.session_state[PREFER_RESPONSES_API] = prefer_responses_api
            render_answer_with_optional_pos_highlight(
                phase1_answer_placeholder,
                phase1_pos_note_placeholder,
                answer,
                phase1_highlight_enabled,
                phase1_selected_tags,
            )
            phase1_usage_col, phase1_edit_col = st.columns([8, 1.6], gap="small", vertical_alignment="center")
            with phase1_usage_col:
                st.caption(build_usage_caption(usage))
            with phase1_edit_col:
                if st.button("✏️ Edit", key="phase1_edit_button_stream", help="Edit output", disabled=ui_locked):
                    st.session_state["phase1_edit_text"] = answer
                    edit_phase1_output_dialog(ui_locked)
            render_copy_buttons(
                "Copy Plain Text",
                "Copy Markdown",
                answer,
                key="phase1_copy_button",
            )

            st.session_state[PHASE1_DONE] = True
            st.session_state[PHASE1_OUTPUT] = answer
            st.session_state[PHASE1_EDITED_BY_USER] = False
            st.session_state[PHASE1_REASONING] = thought
            st.session_state[PHASE1_USAGE] = usage
            st.session_state[PHASE2_OUTPUT] = ""
            st.session_state[PHASE2_EDITED_BY_USER] = False
            st.session_state[PHASE2_REASONING] = ""
            st.session_state[PHASE2_USAGE] = None

            st.session_state[CONVERSATION_MESSAGES] = messages + [
                {"role": "assistant", "content": answer}
            ]
        except Exception as exc:
            st.session_state[LAST_ERROR] = f"Analyze failed: {exc}"
        finally:
            st.session_state[PENDING_ACTION] = None
            st.session_state[IS_PROCESSING] = False
            st.rerun()

    if st.session_state[PHASE1_DONE]:
        st.divider()
        corr_left, corr_right = st.columns([1, 1.2], gap="large")

        with corr_left:
            st.subheader(":material/sync_alt: Phase 2 · Refinement Loop")
            correction_image = st.file_uploader(
                "Upload the generated/incorrect media (image/video, optional, one or more)",
                type=SUPPORTED_MEDIA_TYPES,
                key="correction_image",
                accept_multiple_files=True,
                disabled=ui_locked,
            )
            st.caption(
                "Optional upload: you can submit text-only correction notes, or include one or more media items for multimodal refinement. "
                "Allowed formats: image (PNG/JPG/JPEG/WEBP) or video (MP4 only). "
                f"App-enforced video limit: {MAX_VIDEO_UPLOAD_MB} MB. "
                "Image size follows provider/endpoint limits."
            )
            phase2_media_errors = validate_media_sizes(correction_image)
            for media_error in phase2_media_errors:
                st.error(media_error)

            phase2_media_items = collect_tagged_media_inputs(
                correction_image,
                phase_key_prefix="phase2",
            )
            if len(phase2_media_items) == 1:
                single_item = phase2_media_items[0]
                if single_item["kind"] == "video":
                    st.video(single_item["file"])
                else:
                    st.image(single_item["file"], caption="Correction image preview", width="stretch")
            elif len(phase2_media_items) > 1:
                st.caption("Multiple media detected. Showing compact thumbnails; open dialog for full-size preview + tags.")
                render_multi_media_thumbnail_strip(phase2_media_items)
                if st.button(
                    "Manage media tags",
                    key="phase2_manage_media_tags",
                    disabled=ui_locked,
                    width="stretch",
                ):
                    manage_phase2_media_dialog(phase2_media_items, ui_locked)

            phase2_duplicate_tags = find_duplicate_media_tags(phase2_media_items)
            if phase2_duplicate_tags:
                st.warning(
                    "Duplicate media tags detected: "
                    + ", ".join(phase2_duplicate_tags)
                    + ". Duplicate tags may reduce clarity in model references."
                )

            phase2_media_kind_summary = summarize_media_kind(correction_image)
            phase2_media_tag_summary = summarize_media_tag_map(phase2_media_items)

            correction_options = [p["filename"] for p in correction_presets]
            default_correction_index = (
                correction_options.index(default_correction_preset["filename"])
                if (default_correction_preset and default_correction_preset["filename"] in correction_options)
                else 0
            )
            correction_preset_col, correction_load_col = st.columns([5, 1.25], gap="small")
            with correction_preset_col:
                selected_correction_file = st.selectbox(
                    "Refinement Notes Preset",
                    options=correction_options,
                    index=default_correction_index,
                    format_func=lambda fn: next((p["title"] for p in correction_presets if p["filename"] == fn), fn),
                    disabled=ui_locked or not correction_options,
                ) if correction_options else ""
            selected_correction_preset = next(
                (p for p in correction_presets if p["filename"] == selected_correction_file),
                None,
            )
            selected_correction_content = selected_correction_preset["content"] if selected_correction_preset else ""
            selected_correction_description = selected_correction_preset["description"] if selected_correction_preset else ""
            if selected_correction_description:
                st.caption(selected_correction_description)
            if correction_presets_warning:
                st.warning(correction_presets_warning)

            init_textarea_state("correction_notes_text", "")

            with correction_load_col:
                st.markdown("<div style='height: 1.9rem;'></div>", unsafe_allow_html=True)
                load_correction_clicked = st.button(
                    "Load",
                    key="load_correction_preset",
                    disabled=ui_locked or not correction_options,
                    help="Load selected preset into the Refinement Notes text box.",
                    width="stretch",
                )
            if load_correction_clicked:
                st.session_state["correction_notes_text"] = selected_correction_content or DEFAULT_CORRECTION_PROMPT

            correction_notes = st.text_area(
                "Refinement Notes",
                key="correction_notes_text",
                placeholder="Describe how the model should refine or revise the prior analysis.",
                height=120,
                disabled=ui_locked,
            )

            effective_correction_notes = correction_notes

            phase2_meta_preview, phase2_payload_preview = build_phase2_transparency_preview(
                provider_label=str(selected_provider_label),
                endpoint=effective_base_url,
                model=effective_model,
                reasoning=effective_reasoning_effort,
                system_prompt=effective_system_prompt,
                phase1_output=st.session_state[PHASE1_OUTPUT],
                correction_prompt=effective_correction_notes,
                correction_media_kind=phase2_media_kind_summary,
                correction_media_tags=phase2_media_tag_summary,
            )
            render_transparency_block(
                phase2_meta_preview,
                phase2_payload_preview,
                key="phase2_transparency_preview",
            )

            correction_clicked = st.button("Run Refinement", width="stretch", disabled=ui_locked)

        with corr_right:
            st.subheader(":material/auto_awesome: Refined Analysis")
            phase2_highlight_enabled = st.checkbox(
                "Highlight POS (EN only): verbs / adjectives / nouns",
                key="phase2_pos_highlight",
                value=False,
            )
            phase2_pos_options = {
                "Verb": "VERB",
                "Adjective": "ADJ",
                "Noun": "NOUN",
            }
            phase2_selected_labels = st.multiselect(
                "POS types to highlight",
                options=list(phase2_pos_options.keys()),
                default=list(phase2_pos_options.keys()),
                key="phase2_pos_types",
                disabled=not phase2_highlight_enabled,
            )
            phase2_selected_tags = {phase2_pos_options[label] for label in phase2_selected_labels}
            phase2_thought_expander = st.expander(":material/psychology: Thought Process", expanded=True)
            phase2_thought_placeholder = phase2_thought_expander.empty()
            phase2_answer_placeholder = st.empty()
            phase2_pos_note_placeholder = st.empty()

            if st.session_state[PHASE2_REASONING]:
                phase2_thought_placeholder.markdown(st.session_state[PHASE2_REASONING])
            if st.session_state[PHASE2_OUTPUT]:
                render_answer_with_optional_pos_highlight(
                    phase2_answer_placeholder,
                    phase2_pos_note_placeholder,
                    st.session_state[PHASE2_OUTPUT],
                    phase2_highlight_enabled,
                    phase2_selected_tags,
                )
                phase2_usage_col, phase2_edit_col = st.columns([8, 1.6], gap="small", vertical_alignment="center")
                with phase2_usage_col:
                    usage_caption = build_usage_caption(st.session_state[PHASE2_USAGE])
                    if st.session_state[PHASE2_EDITED_BY_USER]:
                        usage_caption += " · Edited by user"
                    st.caption(usage_caption)
                with phase2_edit_col:
                    if st.button("✏️ Edit", key="phase2_edit_button", help="Edit output", disabled=ui_locked):
                        st.session_state["phase2_edit_text"] = st.session_state[PHASE2_OUTPUT]
                        edit_phase2_output_dialog(ui_locked)

                render_copy_buttons(
                    "Copy Plain Text",
                    "Copy Markdown",
                    st.session_state[PHASE2_OUTPUT],
                    key="phase2_copy_button",
                )

        if correction_clicked and not ui_locked:
            if not effective_api_key:
                st.error("Please provide an API key in sidebar or set provider key / LLM_API_KEY / API_KEY in .env.")
                return
            if not effective_model:
                st.error("Please provide a model name.")
                return
            if phase2_media_errors:
                return

            st.session_state[LAST_ERROR] = ""
            st.session_state[IS_PROCESSING] = True
            st.session_state[PENDING_ACTION] = "phase2"
            st.rerun()

        if st.session_state[PENDING_ACTION] == "phase2":
            client = OpenAI(api_key=effective_api_key, base_url=effective_base_url)

            correction_text = effective_correction_notes.strip()
            correction_request_media = make_request_media_input(phase2_media_items)
            correction_user_message = make_user_message(correction_request_media, correction_text)

            messages = list(st.session_state[CONVERSATION_MESSAGES])
            messages.append(correction_user_message)

            try:
                with st.spinner("Running refinement..."):
                    answer, thought, usage, prefer_responses_api = stream_response(
                        client,
                        effective_model,
                        messages,
                        phase2_thought_placeholder,
                        phase2_answer_placeholder,
                        reasoning_effort=effective_reasoning_effort,
                        prefer_responses_api=st.session_state[PREFER_RESPONSES_API],
                    )
                st.session_state[PREFER_RESPONSES_API] = prefer_responses_api
                render_answer_with_optional_pos_highlight(
                    phase2_answer_placeholder,
                    phase2_pos_note_placeholder,
                    answer,
                    phase2_highlight_enabled,
                    phase2_selected_tags,
                )
                phase2_usage_col, phase2_edit_col = st.columns([8, 1.6], gap="small", vertical_alignment="center")
                with phase2_usage_col:
                    st.caption(build_usage_caption(usage))
                with phase2_edit_col:
                    if st.button("✏️ Edit", key="phase2_edit_button_stream", help="Edit output", disabled=ui_locked):
                        st.session_state["phase2_edit_text"] = answer
                        edit_phase2_output_dialog(ui_locked)
                render_copy_buttons(
                    "Copy Plain Text",
                    "Copy Markdown",
                    answer,
                    key="phase2_copy_button",
                )

                messages.append({"role": "assistant", "content": answer})
                st.session_state[CONVERSATION_MESSAGES] = messages
                st.session_state[PHASE2_OUTPUT] = answer
                st.session_state[PHASE2_EDITED_BY_USER] = False
                st.session_state[PHASE2_REASONING] = thought
                st.session_state[PHASE2_USAGE] = usage
            except Exception as exc:
                st.session_state[LAST_ERROR] = f"Correction failed: {exc}"
            finally:
                st.session_state[PENDING_ACTION] = None
                st.session_state[IS_PROCESSING] = False
                st.rerun()

    if st.session_state[LAST_ERROR]:
        st.error(st.session_state[LAST_ERROR])


if __name__ == "__main__":
    # Allows launching with: uv run run.py
    # while avoiding recursive Streamlit bootstrapping when the script
    # is already being executed by Streamlit itself.
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        running_inside_streamlit = get_script_run_ctx() is not None
    except Exception:
        running_inside_streamlit = False

    if running_inside_streamlit:
        render()
    else:
        from streamlit.web import cli as stcli

        sys.argv = ["streamlit", "run", __file__]
        raise SystemExit(stcli.main())
