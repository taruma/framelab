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
    PHASE1_OUTPUT,
    PHASE1_REASONING,
    PHASE1_USAGE,
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
    "providers": {},
}

TRANSPARENCY_PREVIEW_WORDS = 30
MAX_VIDEO_UPLOAD_MB = 30
SUPPORTED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
SUPPORTED_VIDEO_TYPES = ["mp4"]
SUPPORTED_MEDIA_TYPES = SUPPORTED_IMAGE_TYPES + SUPPORTED_VIDEO_TYPES
DEFAULT_INITIAL_PROMPT = "Analyze this reference image in highly detailed technical and creative terms."
DEFAULT_CORRECTION_PROMPT = "Use this new image and correction notes to refine your previous analysis."


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
            "spaCy is not installed. Run `uv add spacy`, then install model with "
            "`uv run python -m spacy download en_core_web_sm`."
        )
    except Exception as exc:
        if "Can't find model 'en_core_web_sm'" in str(exc):
            return "", (
                "spaCy model `en_core_web_sm` is missing. Install it with "
                "`uv run python -m spacy download en_core_web_sm`."
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
    if not usage:
        placeholder.caption("Usage: not returned by this model/provider.")
        return

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

    placeholder.caption(" · ".join(parts))


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
        transparency_chip("prompt/context", "#34d399", truncate_words(initial_user_text)),
    ]
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
        transparency_chip("reference media", "#f59e0b", "image/video"),
        transparency_chip("previous output", "#a78bfa", truncate_words(phase1_output)),
        transparency_chip("correction media", "#f59e0b", correction_media_kind),
        transparency_chip("correction notes", "#34d399", truncate_words(correction_text)),
    ]
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


def render_copy_button(label: str, text: str, key: str) -> None:
    copy_text = markdown_to_plain_text(text)
    button_id = f"copy-btn-{key}"
    status_id = f"copy-status-{key}"
    st_html(
        f"""
        <div style=\"display:flex;align-items:center;gap:8px;margin-top:4px;\">
          <button id=\"{button_id}\" style=\"padding:0.35rem 0.7rem;border:1px solid #555;border-radius:0.4rem;background:#1f1f1f;color:#f3f3f3;cursor:pointer;\">{html_lib.escape(label)}</button>
          <span id=\"{status_id}\" style=\"font-size:0.85rem;color:#6c757d;\"></span>
        </div>
        <script>
          const textToCopy = {json.dumps(copy_text)};
          const btn = document.getElementById({json.dumps(button_id)});
          const status = document.getElementById({json.dumps(status_id)});
          if (btn && status) {{
            btn.onclick = async () => {{
              try {{
                await navigator.clipboard.writeText(textToCopy);
                status.textContent = 'Copied';
              }} catch (e) {{
                status.textContent = 'Copy failed';
              }}
              setTimeout(() => {{ status.textContent = ''; }}, 1200);
            }};
          }}
        </script>
        """,
        height=44,
    )


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
        st.subheader("Phase 1 · Initial Analysis")
        original_image = st.file_uploader(
            "Original Reference Media (image/video)",
            type=SUPPORTED_MEDIA_TYPES,
            key="original_image",
            disabled=ui_locked,
        )
        st.caption(
            "Allowed formats: image (PNG/JPG/JPEG/WEBP) or video (MP4 only). "
            f"App-enforced video limit: {MAX_VIDEO_UPLOAD_MB} MB. "
            "Image size follows provider/endpoint limits."
        )
        phase1_media_error = validate_media_size(original_image)
        if phase1_media_error:
            st.error(phase1_media_error)
        if original_image is not None:
            if get_media_kind(original_image) == "video":
                st.video(original_image)
            else:
                st.image(original_image, caption="Original image preview", width="stretch")
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
            reference_media_kind=get_media_kind(original_image),
        )
        render_transparency_block(
            phase1_meta_preview,
            phase1_payload_preview,
            key="phase1_transparency_preview",
        )

        analyze_clicked = st.button("Analyze", type="primary", width="stretch", disabled=ui_locked)

    with right_col:
        st.subheader("Phase 1 Output")
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
        phase1_thought_expander = st.expander("Thought Process", expanded=True)
        phase1_thought_placeholder = phase1_thought_expander.empty()
        phase1_answer_placeholder = st.empty()
        phase1_pos_note_placeholder = st.empty()
        phase1_usage_placeholder = st.empty()
        phase1_copy_placeholder = st.empty()

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
            render_usage(st.session_state[PHASE1_USAGE], phase1_usage_placeholder)
            with phase1_copy_placeholder.container():
                render_copy_button(
                    "Copy Output (plain text)",
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
        if original_image is None:
            st.error("Please upload an original reference media file.")
            return
        if phase1_media_error:
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

        initial_user_message = make_user_message(original_image, initial_user_text)
        messages.append(initial_user_message)

        try:
            with st.spinner("Analyzing media..."):
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
            render_usage(usage, phase1_usage_placeholder)
            render_answer_with_optional_pos_highlight(
                phase1_answer_placeholder,
                phase1_pos_note_placeholder,
                answer,
                phase1_highlight_enabled,
                phase1_selected_tags,
            )
            with phase1_copy_placeholder.container():
                render_copy_button("Copy Output (plain text)", answer, key="phase1_copy_button")

            st.session_state[PHASE1_DONE] = True
            st.session_state[PHASE1_OUTPUT] = answer
            st.session_state[PHASE1_REASONING] = thought
            st.session_state[PHASE1_USAGE] = usage
            st.session_state[PHASE2_OUTPUT] = ""
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
            st.subheader("Phase 2 · Correction Flow")
            correction_image = st.file_uploader(
                "Upload the generated/incorrect media (image/video)",
                type=SUPPORTED_MEDIA_TYPES,
                key="correction_image",
                disabled=ui_locked,
            )
            st.caption(
                "Allowed formats: image (PNG/JPG/JPEG/WEBP) or video (MP4 only). "
                f"App-enforced video limit: {MAX_VIDEO_UPLOAD_MB} MB. "
                "Image size follows provider/endpoint limits."
            )
            phase2_media_error = validate_media_size(correction_image)
            if phase2_media_error:
                st.error(phase2_media_error)
            if correction_image is not None:
                if get_media_kind(correction_image) == "video":
                    st.video(correction_image)
                else:
                    st.image(correction_image, caption="Correction image preview", width="stretch")

            correction_options = [p["filename"] for p in correction_presets]
            default_correction_index = (
                correction_options.index(default_correction_preset["filename"])
                if (default_correction_preset and default_correction_preset["filename"] in correction_options)
                else 0
            )
            correction_preset_col, correction_load_col = st.columns([5, 1.25], gap="small")
            with correction_preset_col:
                selected_correction_file = st.selectbox(
                    "Correction Notes Preset",
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
                    help="Load selected preset into the Correction Notes text box.",
                    width="stretch",
                )
            if load_correction_clicked:
                st.session_state["correction_notes_text"] = selected_correction_content or DEFAULT_CORRECTION_PROMPT

            correction_notes = st.text_area(
                "Correction Notes",
                key="correction_notes_text",
                placeholder="Describe exactly how the model should correct the prior analysis.",
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
                correction_media_kind=get_media_kind(correction_image),
            )
            render_transparency_block(
                phase2_meta_preview,
                phase2_payload_preview,
                key="phase2_transparency_preview",
            )

            correction_clicked = st.button("Submit Correction", width="stretch", disabled=ui_locked)

        with corr_right:
            st.subheader("Updated Analysis")
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
            phase2_thought_expander = st.expander("Thought Process", expanded=True)
            phase2_thought_placeholder = phase2_thought_expander.empty()
            phase2_answer_placeholder = st.empty()
            phase2_pos_note_placeholder = st.empty()
            phase2_usage_placeholder = st.empty()
            phase2_copy_placeholder = st.empty()

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
                render_usage(st.session_state[PHASE2_USAGE], phase2_usage_placeholder)
                with phase2_copy_placeholder.container():
                    render_copy_button(
                        "Copy Updated Analysis (plain text)",
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
            if correction_image is None:
                st.error("Please upload a correction media file.")
                return
            if phase2_media_error:
                return

            st.session_state[LAST_ERROR] = ""
            st.session_state[IS_PROCESSING] = True
            st.session_state[PENDING_ACTION] = "phase2"
            st.rerun()

        if st.session_state[PENDING_ACTION] == "phase2":
            client = OpenAI(api_key=effective_api_key, base_url=effective_base_url)

            correction_text = effective_correction_notes.strip()

            correction_user_message = make_user_message(correction_image, correction_text)

            messages = list(st.session_state[CONVERSATION_MESSAGES])
            messages.append(correction_user_message)

            try:
                with st.spinner("Applying correction..."):
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
                render_usage(usage, phase2_usage_placeholder)
                render_answer_with_optional_pos_highlight(
                    phase2_answer_placeholder,
                    phase2_pos_note_placeholder,
                    answer,
                    phase2_highlight_enabled,
                    phase2_selected_tags,
                )
                with phase2_copy_placeholder.container():
                    render_copy_button(
                        "Copy Updated Analysis (plain text)",
                        answer,
                        key="phase2_copy_button",
                    )

                messages.append({"role": "assistant", "content": answer})
                st.session_state[CONVERSATION_MESSAGES] = messages
                st.session_state[PHASE2_OUTPUT] = answer
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
