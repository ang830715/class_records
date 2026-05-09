from __future__ import annotations

import base64
import json
from os import getenv
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from pydantic import ValidationError

from .schemas import ScheduleImportResult

DEFAULT_AI_BASE_URL = "https://api.openai.com/v1"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
SCHEDULE_IMPORT_PROMPT = (
    "Extract weekly teaching lessons from this timetable image. "
    "The left side contains period labels and times; columns are weekdays. "
    "Return only non-empty lesson cells. Map weekdays as Monday=0, Tuesday=1, "
    "Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6. "
    "Use 24-hour HH:MM times. Put the period label, such as P1, in period. "
    "Use notes for extra useful text only; otherwise null."
)
SCHEDULE_IMPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["lessons"],
    "properties": {
        "lessons": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "weekday",
                    "period",
                    "start_time",
                    "end_time",
                    "duration_minutes",
                    "class_name",
                    "notes",
                    "confidence",
                ],
                "properties": {
                    "weekday": {"type": "integer"},
                    "period": {"type": ["string", "null"]},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "class_name": {"type": "string"},
                    "notes": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                },
            },
        }
    },
}


def extract_schedule_from_image(image_bytes: bytes, content_type: str) -> ScheduleImportResult:
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is too large")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload must be an image")

    token = getenv("AI_PROVIDER_TOKEN") or getenv("OPENAI_API_KEY")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Schedule image import is not configured",
        )

    model = getenv("AI_SCHEDULE_MODEL") or getenv("OPENAI_SCHEDULE_MODEL", "gpt-5.5")
    api_style = getenv("AI_SCHEDULE_API_STYLE", "responses").strip().lower()
    base_url = getenv("AI_PROVIDER_BASE_URL") or getenv("OPENAI_BASE_URL") or getenv("OPENAI_API_BASE_URL") or DEFAULT_AI_BASE_URL
    image_data = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{image_data}"

    if api_style == "responses":
        endpoint = _provider_url(base_url, "responses")
        payload = _responses_payload(model, data_url)
    elif api_style in {"chat", "chat_completions", "chat-completions"}:
        endpoint = _provider_url(base_url, "chat/completions")
        payload = _chat_completions_payload(model, data_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_SCHEDULE_API_STYLE must be responses or chat_completions",
        )

    response_json = _post_ai_provider(endpoint, payload, token)
    response_text = _extract_response_text(response_json, api_style)
    try:
        return ScheduleImportResult.model_validate(json.loads(response_text))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider returned a schedule format the app could not understand",
        ) from exc


def _provider_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _responses_payload(model: str, image_url: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": SCHEDULE_IMPORT_PROMPT,
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                    },
                ],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "schedule_import",
                "strict": True,
                "schema": SCHEDULE_IMPORT_SCHEMA,
            }
        },
    }
    return payload


def _chat_completions_payload(model: str, image_url: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SCHEDULE_IMPORT_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "schedule_import",
                "strict": True,
                "schema": SCHEDULE_IMPORT_SCHEMA,
            },
        },
    }


def _post_ai_provider(endpoint: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI schedule import failed: {message[:500]}",
        ) from exc
    except (TimeoutError, URLError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI schedule import failed",
        ) from exc


def _extract_response_text(response_json: dict[str, Any], api_style: str) -> str:
    if api_style in {"chat", "chat_completions", "chat-completions"}:
        choices = response_json.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str) and content.strip():
                return content

    output_text = response_json.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response_json.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI provider did not return schedule text",
    )
