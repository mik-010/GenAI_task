"""Unit tests for the telemetry event parser."""

import json
import os
import tempfile

import pytest

from app.ingestion.parser import parse_event, iter_events_from_jsonl


VALID_API_REQUEST = {
    "body": "claude_code.api_request",
    "attributes": {
        "event.timestamp": "2026-01-15T10:30:00.123Z",
        "event.name": "api_request",
        "session.id": "sess-001",
        "user.email": "alice@example.com",
        "user.id": "uid-001",
        "user.account_uuid": "acc-001",
        "organization.id": "org-001",
        "terminal.type": "vscode",
        "model": "claude-sonnet-4-5-20250929",
        "input_tokens": "100",
        "output_tokens": "50",
        "cache_read_tokens": "200",
        "cache_creation_tokens": "10",
        "cost_usd": "0.05",
        "duration_ms": "5000",
    },
    "resource": {
        "host.arch": "arm64",
        "host.name": "dev-machine",
        "os.type": "darwin",
        "os.version": "24.6.0",
        "service.version": "2.1.50",
    },
    "scope": {"name": "com.anthropic.claude_code.events", "version": "2.1.50"},
}

VALID_TOOL_DECISION = {
    "body": "claude_code.tool_decision",
    "attributes": {
        "event.timestamp": "2026-01-15T10:30:01.000Z",
        "event.name": "tool_decision",
        "session.id": "sess-001",
        "user.email": "alice@example.com",
        "tool_name": "Read",
        "decision": "accept",
        "source": "config",
    },
    "resource": {},
    "scope": {},
}


class TestParseEvent:
    def test_valid_api_request(self):
        result = parse_event(json.dumps(VALID_API_REQUEST))
        assert result is not None
        assert result["event_type"] == "claude_code.api_request"
        assert result["user_email"] == "alice@example.com"
        assert "api_request" in result
        assert result["api_request"]["model"] == "claude-sonnet-4-5-20250929"
        assert result["api_request"]["input_tokens"] == 100
        assert result["api_request"]["cost_usd"] == pytest.approx(0.05)

    def test_valid_tool_decision(self):
        result = parse_event(json.dumps(VALID_TOOL_DECISION))
        assert result is not None
        assert result["event_type"] == "claude_code.tool_decision"
        assert "tool_usage" in result
        assert result["tool_usage"]["tool_name"] == "Read"
        assert result["tool_usage"]["decision"] == "accept"

    def test_malformed_json(self):
        result = parse_event("not json at all")
        assert result is None

    def test_unknown_body_type(self):
        event = {**VALID_API_REQUEST, "body": "unknown.event"}
        result = parse_event(json.dumps(event))
        assert result is None

    def test_missing_required_attrs(self):
        event = {
            "body": "claude_code.api_request",
            "attributes": {"event.timestamp": "2026-01-15T10:30:00.123Z"},
            "resource": {},
        }
        result = parse_event(json.dumps(event))
        assert result is None

    def test_dict_input(self):
        result = parse_event(VALID_API_REQUEST)
        assert result is not None

    def test_safe_int_fallback(self):
        event = dict(VALID_API_REQUEST)
        event["attributes"] = {**event["attributes"], "input_tokens": "not_a_number"}
        result = parse_event(event)
        assert result["api_request"]["input_tokens"] == 0


class TestIterEventsFromJsonl:
    def test_reads_batched_jsonl(self):
        batch = {
            "messageType": "DATA_MESSAGE",
            "logEvents": [
                {
                    "id": "1",
                    "timestamp": 1705312200123,
                    "message": json.dumps(VALID_API_REQUEST),
                },
                {
                    "id": "2",
                    "timestamp": 1705312201000,
                    "message": json.dumps(VALID_TOOL_DECISION),
                },
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(batch) + "\n")
            f.flush()
            path = f.name

        try:
            events = list(iter_events_from_jsonl(path))
            assert len(events) == 2
            assert events[0]["event_type"] == "claude_code.api_request"
            assert events[1]["event_type"] == "claude_code.tool_decision"
        finally:
            os.unlink(path)

    def test_skips_malformed_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("not json\n")
            f.write(json.dumps({"logEvents": [{"message": json.dumps(VALID_API_REQUEST)}]}) + "\n")
            f.flush()
            path = f.name

        try:
            events = list(iter_events_from_jsonl(path))
            assert len(events) == 1
        finally:
            os.unlink(path)
