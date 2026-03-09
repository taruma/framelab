import os
import re
import json
import sys
import tomllib
import html as html_lib
from typing import Tuple

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
    "providers": {},
}

TRANSPARENCY_PREVIEW_WORDS = 30


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
    safe_label = html_lib.escape(label)
    return (
        f"<span style='color:{color};font-weight:600'>[{safe_label}: {safe_content}]</span>"
        if content
        else f"<span style='color:{color};font-weight:600'>[{safe_label}]</span>"
    )


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
    additional_context: str,
    has_reference_image: bool,
) -> tuple[dict[str, str], list[str]]:
    initial_user_text = (
        "Analyze this reference image in highly detailed technical and creative terms.\n\n"
        f"Additional Context:\n{additional_context.strip() or 'None provided.'}"
    )
    meta = {
        "provider": provider_label or "-",
        "endpoint": endpoint or "-",
        "model": model or "-",
        "reasoning": reasoning or "-",
    }
    payload = [
        transparency_chip("system", "#60a5fa", truncate_words(system_prompt)),
        transparency_chip("reference image", "#f59e0b", "image" if has_reference_image else "not selected"),
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
    correction_notes: str,
    has_correction_image: bool,
) -> tuple[dict[str, str], list[str]]:
    correction_text = (
        "Use this new image and correction notes to refine your previous analysis.\n\n"
        f"Correction Notes:\n{correction_notes.strip() or 'None provided.'}"
    )
    meta = {
        "provider": provider_label or "-",
        "endpoint": endpoint or "-",
        "model": model or "-",
        "reasoning": reasoning or "-",
    }
    payload = [
        transparency_chip("system", "#60a5fa", truncate_words(system_prompt)),
        transparency_chip("reference image", "#f59e0b", "image"),
        transparency_chip("previous output", "#a78bfa", truncate_words(phase1_output)),
        transparency_chip("correction image", "#f59e0b", "image" if has_correction_image else "not selected"),
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

            st.caption(f"Reasoning effort: {reasoning_effort_input}")

        st.divider()
        st.markdown("#### System Prompt")

        system_prompt_override = st.text_area(
            "System Prompt Override (optional)",
            value="",
            placeholder="Leave empty to use system_prompt.txt",
            height=180,
            disabled=ui_locked,
        )
        effective_system_prompt = system_prompt_override.strip() or file_prompt

        if prompt_error:
            st.warning(prompt_error)
        else:
            st.caption("Loaded default system prompt from `system_prompt.txt`.")

        st.caption(
            f"System prompt in use: {'Sidebar override' if system_prompt_override.strip() else 'system_prompt.txt'}"
        )

    phase1_transparency_placeholder = st.empty()

    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader("Phase 1 · Initial Analysis")
        original_image = st.file_uploader(
            "Original Reference Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="original_image",
            disabled=ui_locked,
        )
        if original_image is not None:
            st.image(original_image, caption="Original image preview", width="stretch")
        additional_context = st.text_area(
            "Additional Context",
            key="additional_context",
            height=140,
            disabled=ui_locked,
        )
        analyze_clicked = st.button("Analyze", type="primary", width="stretch", disabled=ui_locked)

    phase1_meta_preview, phase1_payload_preview = build_phase1_transparency_preview(
        provider_label=str(selected_provider_label),
        endpoint=effective_base_url,
        model=effective_model,
        reasoning=effective_reasoning_effort,
        system_prompt=effective_system_prompt,
        additional_context=additional_context,
        has_reference_image=original_image is not None,
    )
    with phase1_transparency_placeholder.container():
        render_transparency_block(
            phase1_meta_preview,
            phase1_payload_preview,
            key="phase1_transparency_preview",
        )

    with right_col:
        st.subheader("Phase 1 Output")
        phase1_thought_expander = st.expander("Thought Process", expanded=True)
        phase1_thought_placeholder = phase1_thought_expander.empty()
        phase1_answer_placeholder = st.empty()
        phase1_usage_placeholder = st.empty()
        phase1_copy_placeholder = st.empty()

        if st.session_state[PHASE1_REASONING]:
            phase1_thought_placeholder.markdown(st.session_state[PHASE1_REASONING])
        if st.session_state[PHASE1_OUTPUT]:
            phase1_answer_placeholder.markdown(st.session_state[PHASE1_OUTPUT])
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
            st.error("Please upload an original reference image.")
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

        initial_user_text = (
            "Analyze this reference image in highly detailed technical and creative terms.\n\n"
            f"Additional Context:\n{additional_context.strip() or 'None provided.'}"
        )

        initial_user_message = make_user_message(original_image, initial_user_text)
        messages.append(initial_user_message)

        try:
            with st.spinner("Analyzing image..."):
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
        phase2_transparency_placeholder = st.empty()
        corr_left, corr_right = st.columns([1, 1.2], gap="large")

        with corr_left:
            st.subheader("Phase 2 · Correction Flow")
            correction_image = st.file_uploader(
                "Upload the generated/incorrect image",
                type=["png", "jpg", "jpeg", "webp"],
                key="correction_image",
                disabled=ui_locked,
            )
            if correction_image is not None:
                st.image(correction_image, caption="Correction image preview", width="stretch")
            correction_notes = st.text_area(
                "Correction Notes",
                key="correction_notes",
                placeholder="Example: The lighting is too flat and shadows are missing.",
                height=120,
                disabled=ui_locked,
            )
            correction_clicked = st.button("Submit Correction", width="stretch", disabled=ui_locked)

        phase2_meta_preview, phase2_payload_preview = build_phase2_transparency_preview(
            provider_label=str(selected_provider_label),
            endpoint=effective_base_url,
            model=effective_model,
            reasoning=effective_reasoning_effort,
            system_prompt=effective_system_prompt,
            phase1_output=st.session_state[PHASE1_OUTPUT],
            correction_notes=correction_notes,
            has_correction_image=correction_image is not None,
        )
        with phase2_transparency_placeholder.container():
            render_transparency_block(
                phase2_meta_preview,
                phase2_payload_preview,
                key="phase2_transparency_preview",
            )

        with corr_right:
            st.subheader("Updated Analysis")
            phase2_thought_expander = st.expander("Thought Process", expanded=True)
            phase2_thought_placeholder = phase2_thought_expander.empty()
            phase2_answer_placeholder = st.empty()
            phase2_usage_placeholder = st.empty()
            phase2_copy_placeholder = st.empty()

            if st.session_state[PHASE2_REASONING]:
                phase2_thought_placeholder.markdown(st.session_state[PHASE2_REASONING])
            if st.session_state[PHASE2_OUTPUT]:
                phase2_answer_placeholder.markdown(st.session_state[PHASE2_OUTPUT])
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
                st.error("Please upload a correction image.")
                return

            st.session_state[LAST_ERROR] = ""
            st.session_state[IS_PROCESSING] = True
            st.session_state[PENDING_ACTION] = "phase2"
            st.rerun()

        if st.session_state[PENDING_ACTION] == "phase2":
            client = OpenAI(api_key=effective_api_key, base_url=effective_base_url)

            correction_text = (
                "Use this new image and correction notes to refine your previous analysis.\n\n"
                f"Correction Notes:\n{correction_notes.strip() or 'None provided.'}"
            )

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
