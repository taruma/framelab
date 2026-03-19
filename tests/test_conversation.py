from __future__ import annotations

from dataclasses import dataclass

from conversation import make_user_message, messages_to_responses_input, to_data_url


@dataclass
class FakeUploadedFile:
    data: bytes
    name: str = "sample.png"
    type: str = "image/png"

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


def test_to_data_url_encodes_binary_with_mime() -> None:
    uploaded = FakeUploadedFile(data=b"abc123", name="frame.png", type="image/png")

    data_url = to_data_url(uploaded)

    assert data_url.startswith("data:image/png;base64,")
    assert data_url.endswith("YWJjMTIz")


def test_make_user_message_with_text_and_image() -> None:
    uploaded = FakeUploadedFile(data=b"img", name="shot.jpg", type="image/jpeg")

    message = make_user_message(uploaded, "Analyze this")

    assert message["role"] == "user"
    assert message["content"][0] == {"type": "text", "text": "Analyze this"}
    assert message["content"][1]["type"] == "image_url"
    assert message["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_make_user_message_uses_video_payload_for_video_mime() -> None:
    uploaded = FakeUploadedFile(data=b"vid", name="clip.mp4", type="video/mp4")

    message = make_user_message(uploaded, "")

    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "video_url"
    assert message["content"][0]["video_url"]["url"].startswith("data:video/mp4;base64,")


def test_make_user_message_falls_back_when_no_text_and_no_media() -> None:
    message = make_user_message(None, "   ")
    assert message == {
        "role": "user",
        "content": [{"type": "text", "text": "No extra text provided."}],
    }


def test_messages_to_responses_input_converts_roles_text_and_media() -> None:
    messages = [
        {"role": "system", "content": "You are helpful"},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Look"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                {"type": "video_url", "video_url": {"url": "data:video/mp4;base64,def"}},
            ],
        },
        {"role": "assistant", "content": "Final answer"},
    ]

    converted = messages_to_responses_input(messages)

    assert converted[0] == {
        "role": "system",
        "content": [{"type": "input_text", "text": "You are helpful"}],
    }
    assert converted[1]["role"] == "user"
    assert converted[1]["content"][0] == {"type": "input_text", "text": "Look"}
    assert converted[1]["content"][1] == {
        "type": "input_image",
        "image_url": "data:image/png;base64,abc",
    }
    assert converted[1]["content"][2] == {
        "type": "input_video",
        "video_url": "data:video/mp4;base64,def",
    }
    assert converted[2] == {
        "role": "assistant",
        "content": [{"type": "output_text", "text": "Final answer"}],
    }


def test_messages_to_responses_input_adds_user_fallback_content() -> None:
    converted = messages_to_responses_input([{"role": "user", "content": []}])
    assert converted == [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "No content provided."}],
        }
    ]
