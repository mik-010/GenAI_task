"""Parse CloudWatch-style JSONL telemetry batches into flat event dicts."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

REQUIRED_BODY_TYPES = {
    "claude_code.api_request",
    "claude_code.tool_decision",
    "claude_code.tool_result",
    "claude_code.user_prompt",
    "claude_code.api_error",
}

REQUIRED_ATTRS = {"event.timestamp", "session.id", "user.email"}


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _parse_ts(ts_str: str) -> datetime:
    """Parse event timestamp string to a timezone-aware datetime."""
    ts_str = ts_str.rstrip("Z")
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)


def parse_event(message_str: str) -> Optional[dict]:
    """Parse a single log-event message JSON into a normalised dict.

    Returns None when the event is malformed or has an unknown body type.
    """
    try:
        msg = json.loads(message_str) if isinstance(message_str, str) else message_str
    except json.JSONDecodeError as exc:
        logger.warning("Malformed JSON in event message: %s", exc)
        return None

    body = msg.get("body", "")
    if body not in REQUIRED_BODY_TYPES:
        logger.debug("Skipping unknown body type: %s", body)
        return None

    attrs = msg.get("attributes", {})
    missing = REQUIRED_ATTRS - set(attrs.keys())
    if missing:
        logger.warning("Event missing required attrs %s – skipping", missing)
        return None

    resource = msg.get("resource", {})

    base = {
        "event_type": body,
        "event_name": attrs.get("event.name", body.split(".")[-1]),
        "event_ts": _parse_ts(attrs["event.timestamp"]),
        "session_id": attrs["session.id"],
        "user_email": attrs["user.email"],
        "user_id": attrs.get("user.id"),
        "account_uuid": attrs.get("user.account_uuid"),
        "organization_id": attrs.get("organization.id"),
        "terminal_type": attrs.get("terminal.type"),
        "host_arch": resource.get("host.arch"),
        "host_name": resource.get("host.name"),
        "os_type": resource.get("os.type"),
        "os_version": resource.get("os.version"),
        "service_version": resource.get("service.version"),
        "raw_attributes": attrs,
    }

    if body == "claude_code.api_request":
        base["api_request"] = {
            "model": attrs.get("model", "unknown"),
            "input_tokens": _safe_int(attrs.get("input_tokens")),
            "output_tokens": _safe_int(attrs.get("output_tokens")),
            "cache_read_tokens": _safe_int(attrs.get("cache_read_tokens")),
            "cache_creation_tokens": _safe_int(attrs.get("cache_creation_tokens")),
            "cost_usd": _safe_float(attrs.get("cost_usd")),
            "duration_ms": _safe_int(attrs.get("duration_ms")),
        }
    elif body in ("claude_code.tool_decision", "claude_code.tool_result"):
        base["tool_usage"] = {
            "tool_name": attrs.get("tool_name", "unknown"),
            "decision": attrs.get("decision"),
            "decision_source": attrs.get("decision_source") or attrs.get("source"),
            "success": attrs.get("success", "").lower() == "true" if "success" in attrs else None,
            "duration_ms": _safe_int(attrs.get("duration_ms")),
            "result_size_bytes": _safe_int(attrs.get("tool_result_size_bytes")) or None,
        }
    elif body == "claude_code.user_prompt":
        base["user_prompt"] = {
            "prompt_length": _safe_int(attrs.get("prompt_length")),
        }
    elif body == "claude_code.api_error":
        base["api_error"] = {
            "model": attrs.get("model"),
            "error_message": attrs.get("error"),
            "status_code": attrs.get("status_code"),
            "attempt": _safe_int(attrs.get("attempt"), 1),
            "duration_ms": _safe_int(attrs.get("duration_ms")),
        }

    return base


def iter_events_from_jsonl(path: str) -> Generator[dict, None, None]:
    """Yield parsed events from a JSONL file of CloudWatch log batches."""
    with open(path, "r") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                batch = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Line %d: malformed batch JSON: %s", line_no, exc)
                continue

            for log_event in batch.get("logEvents", []):
                message = log_event.get("message", "")
                parsed = parse_event(message)
                if parsed is not None:
                    yield parsed
