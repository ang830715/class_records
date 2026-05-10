from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from os import getenv
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from pydantic import ValidationError

from .schemas import ScheduleImportResult

logger = logging.getLogger(__name__)

DEFAULT_AI_BASE_URL = "https://api.openai.com/v1"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
SCHEDULE_IMPORT_PROMPT = (
    "Extract weekly teaching lessons from this timetable image. "
    "The left side contains period labels and times; columns are weekdays. "
    "Return only non-empty lesson cells. Map weekdays as Monday=0, Tuesday=1, "
    "Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6. "
    "Use 24-hour HH:MM times. Put the period label, such as P1, in period. "
    "Use notes for extra useful text only; otherwise null. "
    "Return exactly one JSON object with a lessons array. Do not wrap it in markdown. "
    "Example row: {\"weekday\":0,\"period\":\"P1\",\"start_time\":\"08:20\","
    "\"end_time\":\"09:05\",\"duration_minutes\":45,\"class_name\":\"PA4\","
    "\"notes\":null,\"confidence\":0.9}. If the image is a grid, extract every non-empty weekday cell."
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
        normalized = _normalize_schedule_payload(_load_json_from_text(response_text))
        if not normalized["lessons"]:
            logger.warning("AI schedule import returned zero lessons. Raw response preview: %s", response_text[:1200])
        return ScheduleImportResult.model_validate(normalized)
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
            "Accept": "application/json",
            "User-Agent": getenv("AI_PROVIDER_USER_AGENT", "class-records/0.1"),
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
            if isinstance(content, list):
                text_parts = [item.get("text") for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)]
                if text_parts:
                    return "\n".join(text_parts)

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


def _load_json_from_text(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Expected a JSON object", text, 0)
    return parsed


def _normalize_schedule_payload(value: dict[str, Any]) -> dict[str, Any]:
    raw_lessons = value.get("lessons") or value.get("schedule") or value.get("classes") or []
    if not isinstance(raw_lessons, list):
        raw_lessons = []

    lessons: list[dict[str, Any]] = []
    for raw_item in raw_lessons:
        if not isinstance(raw_item, dict):
            continue
        lesson = _normalize_lesson_item(raw_item)
        if lesson is not None:
            lessons.append(lesson)

    if not lessons:
        lessons.extend(_normalize_period_table(value))
    if not lessons:
        lessons.extend(_normalize_day_grouped_table(value))
    return {"lessons": lessons}


def _normalize_lesson_item(raw_item: dict[str, Any], default_weekday: int | None = None) -> dict[str, Any] | None:
    class_name = _first_text(raw_item, "class_name", "class", "course", "name", "subject")
    start_time, end_time = _time_pair(raw_item)
    weekday = _normalize_weekday(raw_item.get("weekday", raw_item.get("day", default_weekday)))
    if class_name is None or start_time is None or end_time is None or weekday is None:
        return None

    duration = _normalize_duration(raw_item.get("duration_minutes", raw_item.get("duration")), start_time, end_time)
    if duration is None:
        return None

    return {
        "weekday": weekday,
        "period": _first_text(raw_item, "period", "period_label", "lesson_period"),
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration,
        "class_name": class_name,
        "notes": _first_text(raw_item, "notes", "note"),
        "confidence": _normalize_confidence(raw_item.get("confidence")),
    }


def _normalize_period_table(value: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _first_list(value, "rows", "table", "timetable", "periods")
    lessons: list[dict[str, Any]] = []
    if rows is None:
        return lessons

    for row in rows:
        if not isinstance(row, dict):
            continue
        start_time, end_time = _time_pair(row)
        if start_time is None or end_time is None:
            continue
        period = _first_text(row, "period", "period_label", "lesson_period")
        for key, item in row.items():
            weekday = _normalize_weekday(key)
            if weekday is None:
                continue
            class_name = _class_name_from_cell(item)
            if class_name is None:
                continue
            duration = _normalize_duration(row.get("duration_minutes", row.get("duration")), start_time, end_time)
            if duration is None:
                continue
            lessons.append(
                {
                    "weekday": weekday,
                    "period": period,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_minutes": duration,
                    "class_name": class_name,
                    "notes": None,
                    "confidence": _normalize_confidence(row.get("confidence")),
                }
            )
    return lessons


def _normalize_day_grouped_table(value: dict[str, Any]) -> list[dict[str, Any]]:
    lessons: list[dict[str, Any]] = []
    for key, items in value.items():
        weekday = _normalize_weekday(key)
        if weekday is None or not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            lesson = _normalize_lesson_item(item, default_weekday=weekday)
            if lesson is not None:
                lessons.append(lesson)
    return lessons


def _first_text(value: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        item = value.get(key)
        if item is None:
            continue
        text = str(item).strip()
        if text:
            return text
    return None


def _first_list(value: dict[str, Any], *keys: str) -> list[Any] | None:
    for key in keys:
        item = value.get(key)
        if isinstance(item, list):
            return item
    return None


def _class_name_from_cell(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return _first_text(value, "class_name", "class", "course", "name", "subject")
    text = str(value).strip()
    return text if text and text.lower() not in {"-", "none", "null"} else None


def _time_pair(value: dict[str, Any]) -> tuple[str | None, str | None]:
    start_time = _normalize_time(_first_text(value, "start_time", "start", "time_start"))
    end_time = _normalize_time(_first_text(value, "end_time", "end", "time_end"))
    if start_time and end_time:
        return start_time, end_time

    combined = _first_text(value, "time", "time_range", "times", "hours")
    if combined:
        matches = re.findall(r"(\d{1,2}):(\d{2})", combined.replace(chr(0xFF1A), ":"))
        if len(matches) >= 2:
            start_time = _normalize_time(":".join(matches[0]))
            end_time = _normalize_time(":".join(matches[1]))
    return start_time, end_time


def _normalize_time(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.search(r"(\d{1,2}):(\d{2})", value.replace(chr(0xFF1A), ":"))
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return f"{hour:02d}:{minute:02d}"


def _normalize_weekday(value: Any) -> int | None:
    if isinstance(value, int) and 0 <= value <= 6:
        return value
    text = str(value).strip().lower()
    if text.isdigit():
        index = int(text)
        return index if 0 <= index <= 6 else None
    day_names = {
        "monday": 0,
        "mon": 0,
        "tuesday": 1,
        "tue": 1,
        "wednesday": 2,
        "wed": 2,
        "thursday": 3,
        "thu": 3,
        "thur": 3,
        "friday": 4,
        "fri": 4,
        "saturday": 5,
        "sat": 5,
        "sunday": 6,
        "sun": 6,
    }
    return day_names.get(text)


def _normalize_duration(value: Any, start_time: str, end_time: str) -> int | None:
    try:
        duration = int(value)
        if 0 < duration <= 480:
            return duration
    except (TypeError, ValueError):
        pass

    start = datetime.strptime(start_time, "%H:%M")
    end = datetime.strptime(end_time, "%H:%M")
    minutes = int((end - start).total_seconds() // 60)
    return minutes if 0 < minutes <= 480 else None


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.8
    if confidence > 1:
        confidence = confidence / 100
    return min(1, max(0, confidence))

