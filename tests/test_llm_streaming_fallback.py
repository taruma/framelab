from __future__ import annotations

from typing import Any

import llm_streaming


def test_stream_response_uses_chat_when_prefer_responses_disabled(monkeypatch: Any) -> None:
    notes: list[str] = []

    monkeypatch.setattr(llm_streaming.st, "caption", lambda msg: notes.append(msg))
    monkeypatch.setattr(
        llm_streaming,
        "stream_via_chat_completions",
        lambda *args, **kwargs: ("chat-answer", "", {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}),
    )

    answer, thought, usage, prefer = llm_streaming.stream_response(
        client=object(),
        model="m",
        messages=[],
        thought_placeholder=object(),
        answer_placeholder=object(),
        prefer_responses_api=False,
    )

    assert answer == "chat-answer"
    assert thought == ""
    assert usage == {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}
    assert prefer is False
    assert any("Chat Completions (Responses API disabled" in msg for msg in notes)


def test_stream_response_prefers_responses_when_success(monkeypatch: Any) -> None:
    notes: list[str] = []
    monkeypatch.setattr(llm_streaming.st, "caption", lambda msg: notes.append(msg))
    monkeypatch.setattr(
        llm_streaming,
        "stream_via_responses_api",
        lambda *args, **kwargs: ("responses-answer", "reason", {"total_tokens": 3}),
    )

    answer, thought, usage, prefer = llm_streaming.stream_response(
        client=object(),
        model="m",
        messages=[],
        thought_placeholder=object(),
        answer_placeholder=object(),
        prefer_responses_api=True,
    )

    assert answer == "responses-answer"
    assert thought == "reason"
    assert usage == {"total_tokens": 3}
    assert prefer is True
    assert any("Transport: Responses API" in msg for msg in notes)


def test_stream_response_falls_back_to_chat_and_keeps_responses_enabled(monkeypatch: Any) -> None:
    class Placeholder:
        def __init__(self) -> None:
            self.cleared = False

        def empty(self) -> None:
            self.cleared = True

    thought_placeholder = Placeholder()
    answer_placeholder = Placeholder()
    captions: list[str] = []
    warnings: list[str] = []

    def fail_responses(*args: Any, **kwargs: Any) -> tuple[str, str, dict[str, int] | None]:
        raise RuntimeError("temporary outage")

    monkeypatch.setattr(llm_streaming, "stream_via_responses_api", fail_responses)
    monkeypatch.setattr(
        llm_streaming,
        "stream_via_chat_completions",
        lambda *args, **kwargs: ("fallback-answer", "", {"total_tokens": 2}),
    )
    monkeypatch.setattr(llm_streaming.st, "caption", lambda msg: captions.append(msg))
    monkeypatch.setattr(llm_streaming.st, "warning", lambda msg: warnings.append(msg))

    answer, thought, usage, prefer = llm_streaming.stream_response(
        client=object(),
        model="m",
        messages=[],
        thought_placeholder=thought_placeholder,
        answer_placeholder=answer_placeholder,
        prefer_responses_api=True,
    )

    assert answer == "fallback-answer"
    assert thought == ""
    assert usage == {"total_tokens": 2}
    assert prefer is True
    assert thought_placeholder.cleared and answer_placeholder.cleared
    assert any("Falling back to Chat Completions" in msg for msg in captions)
    assert any("Responses API error" in msg for msg in warnings)


def test_stream_response_disables_responses_api_on_schema_mismatch(monkeypatch: Any) -> None:
    class Placeholder:
        def empty(self) -> None:
            return None

    def fail_responses(*args: Any, **kwargs: Any) -> tuple[str, str, dict[str, int] | None]:
        raise RuntimeError("input.status missing")

    monkeypatch.setattr(llm_streaming, "stream_via_responses_api", fail_responses)
    monkeypatch.setattr(
        llm_streaming,
        "stream_via_chat_completions",
        lambda *args, **kwargs: ("ok", "", None),
    )
    monkeypatch.setattr(llm_streaming.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(llm_streaming.st, "warning", lambda *_args, **_kwargs: None)

    _, _, _, prefer = llm_streaming.stream_response(
        client=object(),
        model="m",
        messages=[],
        thought_placeholder=Placeholder(),
        answer_placeholder=Placeholder(),
        prefer_responses_api=True,
    )

    assert prefer is False
