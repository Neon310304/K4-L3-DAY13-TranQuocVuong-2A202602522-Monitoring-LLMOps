from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app import logging_config
from app.dashboard import build_dashboard


def test_dashboard_uses_all_tool_events_for_retrieval_success(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "logs.jsonl"
    events = [
        {"ts": "2026-09-30T11:59:01Z", "event": "request_received", "correlation_id": "req-00000001"},
        {"ts": "2026-09-30T11:59:02Z", "event": "response_sent", "correlation_id": "req-00000001", "latency_ms": 100, "ttft_ms": 20, "tokens_in": 30, "tokens_out": 50, "cost_usd": 0.001, "quality_score": 0.8, "tool_success": True},
        {"ts": "2026-09-30T11:59:03Z", "event": "request_received", "correlation_id": "req-00000002"},
        {"ts": "2026-09-30T11:59:04Z", "event": "request_failed", "correlation_id": "req-00000002", "error_type": "RuntimeError", "tool_success": False},
    ]
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
    monkeypatch.setattr(logging_config, "LOG_PATH", path)

    data = build_dashboard(datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc))

    assert set(data["panels"]) == {"latency", "traffic", "errors", "cost", "tokens", "quality"}
    assert data["window_minutes"] == 60
    assert data["refresh_seconds"] == 30
    assert data["panels"]["traffic"]["metrics"]["Requests"] == 2
    assert data["panels"]["errors"]["metrics"]["Error rate"] == 50.0
    assert data["panels"]["errors"]["metrics"]["Retrieval success"] == 50.0
    assert data["panels"]["errors"]["error_types"] == {"RuntimeError": 1}
    assert data["panels"]["latency"]["metrics"]["P95"] == 100
    assert data["panels"]["tokens"]["metrics"]["Total"] == 80
    assert all("threshold" in panel for panel in data["panels"].values())
