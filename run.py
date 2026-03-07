import base64
import mimetypes
import sys
from typing import Any, Tuple

import streamlit as st
from openai import OpenAI


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


def stream_response(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    thought_placeholder: Any,
    answer_placeholder: Any,
) -> Tuple[str, str]:
    answer = ""
    thought = ""

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
    )

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

    st.title("🧠 Multimodal Image Analysis")
    st.caption("Analyze a reference image, then iterate with correction images and notes.")

    with st.sidebar:
        st.header("Model Settings")
        api_key = st.text_input("API Key", type="password")
        base_url = st.text_input("Base URL / Endpoint", value="https://api.openai.com/v1")
        model = st.text_input("Model Name", value="gpt-4o")
        system_prompt = st.text_area(
            "System Prompt",
            value="",
            placeholder="Optional: define role, output format, constraints, and style.",
            height=180,
        )

    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader("Phase 1 · Initial Analysis")
        original_image = st.file_uploader(
            "Original Reference Image",
            type=["png", "jpg", "jpeg", "webp"],
            key="original_image",
        )
        additional_context = st.text_area("Additional Context", key="additional_context", height=140)
        analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)

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
        if not api_key.strip():
            st.error("Please provide an API key.")
            return
        if not model.strip():
            st.error("Please provide a model name.")
            return
        if original_image is None:
            st.error("Please upload an original reference image.")
            return

        client = OpenAI(api_key=api_key.strip(), base_url=base_url.strip())
        messages = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})

        initial_user_text = (
            "Analyze this reference image in highly detailed technical and creative terms.\n\n"
            f"Additional Context:\n{additional_context.strip() or 'None provided.'}"
        )
        initial_user_message = make_user_message(original_image, initial_user_text)
        messages.append(initial_user_message)

        with st.spinner("Analyzing image..."):
            answer, thought = stream_response(
                client,
                model.strip(),
                messages,
                phase1_thought_placeholder,
                phase1_answer_placeholder,
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
            correction_notes = st.text_area(
                "Correction Notes",
                key="correction_notes",
                placeholder="Example: The lighting is too flat and shadows are missing.",
                height=120,
            )
            correction_clicked = st.button("Submit Correction", use_container_width=True)

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
            if not api_key.strip():
                st.error("Please provide an API key.")
                return
            if not model.strip():
                st.error("Please provide a model name.")
                return
            if correction_image is None:
                st.error("Please upload a correction image.")
                return

            client = OpenAI(api_key=api_key.strip(), base_url=base_url.strip())

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
                    model.strip(),
                    messages,
                    phase2_thought_placeholder,
                    phase2_answer_placeholder,
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
