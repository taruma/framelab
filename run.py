import base64
import mimetypes
import os
import sys
from typing import Any, Tuple

import streamlit as st
from openai import OpenAI

from config import DEFAULT_BASE_URL, DEFAULT_MODEL


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


def init_state() -> None:
    defaults = {
        "phase1_done": False,
        "conversation_messages": [],
        "phase1_output": "",
        "phase1_reasoning": "",
        "phase2_output": "",
        "phase2_reasoning": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def to_data_url(uploaded_file: Any) -> str:
    raw = uploaded_file.getvalue()
    mime = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "image/png"
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def make_user_message(image_file: Any, text: str) -> dict[str, Any]:
    content = []
    if text.strip():
        content.append({"type": "text", "text": text.strip()})
    if image_file is not None:
        content.append({"type": "image_url", "image_url": {"url": to_data_url(image_file)}})
    if not content:
        content.append({"type": "text", "text": "No extra text provided."})
    return {"role": "user", "content": content}


def messages_to_responses_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content")
        converted_content: list[dict[str, Any]] = []

        if isinstance(content, str):
            item_type = "output_text" if role == "assistant" else "input_text"
            if content.strip():
                converted_content.append({"type": item_type, "text": content})

        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, dict):
                    continue

                item_type = item.get("type")
                if item_type == "text":
                    text = item.get("text") or item.get("content") or ""
                    if text:
                        text_type = "output_text" if role == "assistant" else "input_text"
                        converted_content.append({"type": text_type, "text": text})

                elif item_type == "image_url":
                    image_obj = item.get("image_url")
                    if isinstance(image_obj, dict):
                        image_url = image_obj.get("url")
                        if image_url:
                            converted_content.append({"type": "input_image", "image_url": image_url})

        if not converted_content and role != "assistant":
            converted_content = [{"type": "input_text", "text": "No content provided."}]

        converted.append({"role": role, "content": converted_content})

    return converted


def extract_deltas(chunk: Any) -> Tuple[str, str]:
    text_delta = ""
    reasoning_delta = ""

    try:
        data = chunk.model_dump()
    except Exception:
        return "", ""

    choices = data.get("choices") or []
    if not choices:
        return "", ""

    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    reasoning = delta.get("reasoning_content") or delta.get("reasoning")

    if isinstance(content, str):
        text_delta += content
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text_delta += item.get("text") or item.get("content") or ""

    if isinstance(reasoning, str):
        reasoning_delta += reasoning
    elif isinstance(reasoning, list):
        for item in reasoning:
            if not isinstance(item, dict):
                continue
            reasoning_delta += item.get("text") or item.get("content") or ""

    return text_delta, reasoning_delta


def extract_response_deltas(event: Any) -> Tuple[str, str]:
    text_delta = ""
    reasoning_delta = ""

    try:
        data = event.model_dump()
    except Exception:
        return "", ""

    event_type = str(data.get("type") or "")
    delta = data.get("delta")

    if isinstance(delta, str):
        event_type_lower = event_type.lower()
        if "output_text" in event_type_lower:
            text_delta += delta
        elif any(token in event_type_lower for token in ["reason", "think", "summary"]):
            reasoning_delta += delta

    return text_delta, reasoning_delta


def stream_response(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    thought_placeholder: Any,
    answer_placeholder: Any,
    reasoning_effort: str | None = None,
) -> Tuple[str, str]:
    answer = ""
    thought = ""

    responses_request_kwargs: dict[str, Any] = {
        "model": model,
        "input": messages_to_responses_input(messages),
        "stream": True,
    }
    if reasoning_effort:
        responses_request_kwargs["reasoning"] = {"effort": reasoning_effort}

    try:
        stream = client.responses.create(**responses_request_kwargs)

        for event in stream:
            text_delta, reasoning_delta = extract_response_deltas(event)

            if reasoning_delta:
                thought += reasoning_delta
                thought_placeholder.markdown(thought)

            if text_delta:
                answer += text_delta
                answer_placeholder.markdown(answer)

        if not thought:
            thought_placeholder.caption("No reasoning/thought stream was returned by this model.")

        return answer, thought
    except Exception:
        # Fallback path for providers/endpoints without Responses API support.
        answer = ""
        thought = ""
        thought_placeholder.empty()
        answer_placeholder.empty()
        st.caption("Responses API failed on this endpoint/model. Falling back to Chat Completions.")

    request_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if reasoning_effort:
        request_kwargs["reasoning_effort"] = reasoning_effort

    stream = client.chat.completions.create(**request_kwargs)

    for chunk in stream:
        text_delta, reasoning_delta = extract_deltas(chunk)

        if reasoning_delta:
            thought += reasoning_delta
            thought_placeholder.markdown(thought)

        if text_delta:
            answer += text_delta
            answer_placeholder.markdown(answer)

    if not thought:
        thought_placeholder.caption("No reasoning/thought stream was returned by this model.")

    return answer, thought


def render() -> None:
    st.set_page_config(page_title="Multimodal Analysis + Correction", layout="wide")
    init_state()
    load_env_file()

    file_prompt, prompt_error = load_system_prompt()

    st.title("🧠 Multimodal Image Analysis")
    st.caption("Analyze a reference image, then iterate with correction images and notes.")

    with st.sidebar:
        st.header("Model Settings")
        api_key_input = st.text_input("API Key", type="password")
        env_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        effective_api_key = api_key_input.strip() or env_api_key
        if api_key_input.strip():
            st.caption("Using API key from sidebar input.")
        elif env_api_key:
            st.caption("Using API key from .env (`OPENAI_API_KEY`).")
        else:
            st.caption("No API key found yet. Enter one in sidebar or set `OPENAI_API_KEY` in .env.")

        base_url_input = st.text_input(
            "Base URL / Endpoint",
            value="",
            placeholder=f"Leave empty to use default: {DEFAULT_BASE_URL}",
        )
        model_input = st.text_input(
            "Model Name",
            value="",
            placeholder=f"Leave empty to use default: {DEFAULT_MODEL}",
        )
        reasoning_effort_input = st.selectbox(
            "Reasoning Effort",
            options=["none", "minimal", "low", "medium", "high"],
            index=2,
            help="For reasoning-capable models/providers. The selected value is sent as-is.",
        )

        effective_base_url = base_url_input.strip() or DEFAULT_BASE_URL
        effective_model = model_input.strip() or DEFAULT_MODEL
        effective_reasoning_effort = reasoning_effort_input

        st.caption(
            f"Endpoint in use: {'Sidebar override' if base_url_input.strip() else 'config.py default'}"
        )
        st.caption(
            f"Model in use: {'Sidebar override' if model_input.strip() else 'config.py default'}"
        )
        st.caption(
            "Reasoning effort in use: "
            f"{reasoning_effort_input}"
        )

        system_prompt_override = st.text_area(
            "System Prompt Override (optional)",
            value="",
            placeholder="Leave empty to use system_prompt.txt",
            height=180,
        )
        effective_system_prompt = system_prompt_override.strip() or file_prompt

        if prompt_error:
            st.warning(prompt_error)
        else:
            st.caption("Loaded default system prompt from `system_prompt.txt`.")

        st.caption(
            f"System prompt in use: {'Sidebar override' if system_prompt_override.strip() else 'system_prompt.txt'}"
        )

    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader("Phase 1 · Initial Analysis")
        original_image = st.file_uploader(
            "Original Reference Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="original_image",
        )
        if original_image is not None:
            st.image(original_image, caption="Original image preview", width="stretch")
        additional_context = st.text_area("Additional Context", key="additional_context", height=140)
        analyze_clicked = st.button("Analyze", type="primary", width="stretch")

    with right_col:
        st.subheader("Phase 1 Output")
        phase1_thought_expander = st.expander("Thought Process", expanded=True)
        phase1_thought_placeholder = phase1_thought_expander.empty()
        phase1_answer_placeholder = st.empty()

        if st.session_state["phase1_reasoning"]:
            phase1_thought_placeholder.markdown(st.session_state["phase1_reasoning"])
        if st.session_state["phase1_output"]:
            phase1_answer_placeholder.markdown(st.session_state["phase1_output"])

    if analyze_clicked:
        if not effective_api_key:
            st.error("Please provide an API key in the sidebar or set OPENAI_API_KEY in .env.")
            return
        if not effective_model:
            st.error("Please provide a model name.")
            return
        if original_image is None:
            st.error("Please upload an original reference image.")
            return

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

        with st.spinner("Analyzing image..."):
            answer, thought = stream_response(
                client,
                effective_model,
                messages,
                phase1_thought_placeholder,
                phase1_answer_placeholder,
                reasoning_effort=effective_reasoning_effort,
            )

        st.session_state["phase1_done"] = True
        st.session_state["phase1_output"] = answer
        st.session_state["phase1_reasoning"] = thought
        st.session_state["phase2_output"] = ""
        st.session_state["phase2_reasoning"] = ""

        st.session_state["conversation_messages"] = messages + [
            {"role": "assistant", "content": answer}
        ]

    if st.session_state["phase1_done"]:
        st.divider()
        corr_left, corr_right = st.columns([1, 1.2], gap="large")

        with corr_left:
            st.subheader("Phase 2 · Correction Flow")
            correction_image = st.file_uploader(
                "Upload the generated/incorrect image",
                type=["png", "jpg", "jpeg", "webp"],
                key="correction_image",
            )
            if correction_image is not None:
                st.image(correction_image, caption="Correction image preview", width="stretch")
            correction_notes = st.text_area(
                "Correction Notes",
                key="correction_notes",
                placeholder="Example: The lighting is too flat and shadows are missing.",
                height=120,
            )
            correction_clicked = st.button("Submit Correction", width="stretch")

        with corr_right:
            st.subheader("Updated Analysis")
            phase2_thought_expander = st.expander("Thought Process", expanded=True)
            phase2_thought_placeholder = phase2_thought_expander.empty()
            phase2_answer_placeholder = st.empty()

            if st.session_state["phase2_reasoning"]:
                phase2_thought_placeholder.markdown(st.session_state["phase2_reasoning"])
            if st.session_state["phase2_output"]:
                phase2_answer_placeholder.markdown(st.session_state["phase2_output"])

        if correction_clicked:
            if not effective_api_key:
                st.error("Please provide an API key in the sidebar or set OPENAI_API_KEY in .env.")
                return
            if not effective_model:
                st.error("Please provide a model name.")
                return
            if correction_image is None:
                st.error("Please upload a correction image.")
                return

            client = OpenAI(api_key=effective_api_key, base_url=effective_base_url)

            correction_text = (
                "Use this new image and correction notes to refine your previous analysis.\n\n"
                f"Correction Notes:\n{correction_notes.strip() or 'None provided.'}"
            )
            correction_user_message = make_user_message(correction_image, correction_text)

            messages = list(st.session_state["conversation_messages"])
            messages.append(correction_user_message)

            with st.spinner("Applying correction..."):
                answer, thought = stream_response(
                    client,
                    effective_model,
                    messages,
                    phase2_thought_placeholder,
                    phase2_answer_placeholder,
                    reasoning_effort=effective_reasoning_effort,
                )

            messages.append({"role": "assistant", "content": answer})
            st.session_state["conversation_messages"] = messages
            st.session_state["phase2_output"] = answer
            st.session_state["phase2_reasoning"] = thought


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
