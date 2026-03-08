from typing import Any, Tuple

import streamlit as st
from openai import OpenAI

from conversation import messages_to_responses_input


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


def stream_via_responses_api(
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


def stream_via_chat_completions(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    thought_placeholder: Any,
    answer_placeholder: Any,
    reasoning_effort: str | None = None,
) -> Tuple[str, str]:
    answer = ""
    thought = ""

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


def stream_response(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    thought_placeholder: Any,
    answer_placeholder: Any,
    reasoning_effort: str | None = None,
) -> Tuple[str, str]:
    try:
        return stream_via_responses_api(
            client,
            model,
            messages,
            thought_placeholder,
            answer_placeholder,
            reasoning_effort=reasoning_effort,
        )
    except Exception:
        thought_placeholder.empty()
        answer_placeholder.empty()
        st.caption("Responses API failed on this endpoint/model. Falling back to Chat Completions.")

    return stream_via_chat_completions(
        client,
        model,
        messages,
        thought_placeholder,
        answer_placeholder,
        reasoning_effort=reasoning_effort,
    )
