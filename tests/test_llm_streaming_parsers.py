from __future__ import annotations

from llm_streaming import (
    extract_deltas,
    extract_response_deltas,
    extract_usage_from_chat_chunk,
    extract_usage_from_response_event,
    normalize_usage,
    should_disable_responses_api,
)


class DummyDump:
    def __init__(self, data: dict):
        self._data = data

    def model_dump(self) -> dict:
        return self._data


def test_normalize_usage_supports_prompt_completion_shape() -> None:
    usage = normalize_usage({"prompt_tokens": 10, "completion_tokens": 5})
    assert usage == {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}


def test_normalize_usage_supports_input_output_shape() -> None:
    usage = normalize_usage({"input_tokens": 4, "output_tokens": 6, "total_tokens": 10})
    assert usage == {"input_tokens": 4, "output_tokens": 6, "total_tokens": 10}


def test_should_disable_responses_api_for_known_schema_mismatch() -> None:
    exc = RuntimeError("input.status is missing in payload")
    assert should_disable_responses_api(exc) is True


def test_extract_usage_from_response_event_top_level_and_nested() -> None:
    top_level = DummyDump({"usage": {"input_tokens": 1, "output_tokens": 2}})
    nested = DummyDump({"response": {"usage": {"prompt_tokens": 3, "completion_tokens": 4}}})

    assert extract_usage_from_response_event(top_level) == {
        "input_tokens": 1,
        "output_tokens": 2,
        "total_tokens": 3,
    }
    assert extract_usage_from_response_event(nested) == {
        "input_tokens": 3,
        "output_tokens": 4,
        "total_tokens": 7,
    }


def test_extract_usage_from_chat_chunk() -> None:
    chunk = DummyDump({"usage": {"prompt_tokens": 7, "completion_tokens": 8}})
    assert extract_usage_from_chat_chunk(chunk) == {
        "input_tokens": 7,
        "output_tokens": 8,
        "total_tokens": 15,
    }


def test_extract_deltas_handles_string_and_list_shapes() -> None:
    chunk_string = DummyDump(
        {
            "choices": [
                {
                    "delta": {
                        "content": "hello",
                        "reasoning_content": "think",
                    }
                }
            ]
        }
    )
    chunk_list = DummyDump(
        {
            "choices": [
                {
                    "delta": {
                        "content": [{"text": " world"}],
                        "reasoning": [{"content": " more"}],
                    }
                }
            ]
        }
    )

    assert extract_deltas(chunk_string) == ("hello", "think")
    assert extract_deltas(chunk_list) == (" world", " more")


def test_extract_response_deltas_routes_by_event_type() -> None:
    text_event = DummyDump({"type": "response.output_text.delta", "delta": "A"})
    reasoning_event = DummyDump({"type": "response.reasoning.delta", "delta": "B"})
    irrelevant_event = DummyDump({"type": "response.completed", "delta": "C"})

    assert extract_response_deltas(text_event) == ("A", "")
    assert extract_response_deltas(reasoning_event) == ("", "B")
    assert extract_response_deltas(irrelevant_event) == ("", "")
