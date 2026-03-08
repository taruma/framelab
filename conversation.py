import base64
import mimetypes
from typing import Any


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
