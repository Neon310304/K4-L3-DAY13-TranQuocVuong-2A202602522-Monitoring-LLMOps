from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from . import logging_config

router = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "dashboard.yaml"
SLO_PATH = ROOT / "config" / "slo.yaml"
HTML_PATH = Path(__file__).with_name("dashboard.html")


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percentile / 100) - 1)], 3)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _read_events(start: datetime, now: datetime) -> list[dict[str, Any]]:
    path = logging_config.LOG_PATH
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
            timestamp = datetime.fromisoformat(event["ts"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                continue
            timestamp = timestamp.astimezone(timezone.utc)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        if start <= timestamp <= now:
            event["_minute"] = timestamp.replace(second=0, microsecond=0)
            events.append(event)
    return events


def _numbers(events: list[dict[str, Any]], field: str) -> list[float]:
    return [float(event[field]) for event in events if isinstance(event.get(field), (int, float)) and not isinstance(event[field], bool)]


def build_dashboard(now: datetime | None = None) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    slo = yaml.safe_load(SLO_PATH.read_text(encoding="utf-8"))
    dashboard = config["dashboard"]
    minutes = dashboard["time_range_minutes"]
    minute_keys = [now.replace(second=0, microsecond=0) - timedelta(minutes=minutes - 1 - i) for i in range(minutes)]
    start = minute_keys[0]
    events = _read_events(start, now)
    groups: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        groups[event["_minute"]].append(event)

    received = [event for event in events if event.get("event") == "request_received"]
    responses = [event for event in events if event.get("event") == "response_sent"]
    failures = [event for event in events if event.get("event") == "request_failed"]
    retrievals = [event for event in events if isinstance(event.get("tool_success"), bool)]
    latencies = _numbers(responses, "latency_ms")
    ttfts = _numbers(responses, "ttft_ms")
    costs = _numbers(responses, "cost_usd")
    qualities = _numbers(responses, "quality_score")
    token_in = _numbers(responses, "tokens_in")
    token_out = _numbers(responses, "tokens_out")

    def each(fn):
        return [fn(groups.get(minute, [])) for minute in minute_keys]

    def by_event(items, event_name):
        return [item for item in items if item.get("event") == event_name]

    def pct(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator * 100, 2) if denominator else None

    def rate(items):
        requests = by_event(items, "request_received")
        errors = by_event(items, "request_failed")
        return pct(len(errors), len(requests))

    def retrieval_rate(items):
        tool_events = [item for item in items if isinstance(item.get("tool_success"), bool)]
        return pct(sum(item["tool_success"] for item in tool_events), len(tool_events))

    def cumulative(field):
        total = 0.0
        result = []
        for minute in minute_keys:
            total += sum(_numbers(by_event(groups.get(minute, []), "response_sent"), field))
            result.append(round(total, 6))
        return result

    panel_specs = {panel["id"]: panel for panel in dashboard["panels"]}

    def panel(panel_id: str, metrics: dict, series: list[dict], *, extra: dict | None = None) -> dict:
        spec = panel_specs[panel_id]
        return {
            "title": spec["title"],
            "unit": spec["unit"],
            "threshold": spec["threshold"],
            "metrics": metrics,
            "series": series,
            **(extra or {}),
        }

    panels = {
        "latency": panel(
            "latency",
            {"P50": _percentile(latencies, 50), "P95": _percentile(latencies, 95), "P99": _percentile(latencies, 99), "TTFT P95": _percentile(ttfts, 95)},
            [
                {"name": label, "values": each(lambda items, p=p: _percentile(_numbers(by_event(items, "response_sent"), "latency_ms"), p))}
                for label, p in (("P50", 50), ("P95", 95), ("P99", 99))
            ] + [{"name": "TTFT P95", "values": each(lambda items: _percentile(_numbers(by_event(items, "response_sent"), "ttft_ms"), 95))}],
        ),
        "traffic": panel(
            "traffic",
            {"Requests": len(received), "Average/min": round(len(received) / minutes, 2)},
            [{"name": "Requests/min", "values": each(lambda items: len(by_event(items, "request_received")))}],
        ),
        "errors": panel(
            "errors",
            {"Error rate": pct(len(failures), len(received)), "Retrieval success": retrieval_rate(retrievals), "Failures": len(failures)},
            [
                {"name": "Error rate", "values": each(rate)},
                {"name": "Retrieval success", "values": each(retrieval_rate)},
            ],
            extra={"error_types": dict(Counter(str(item.get("error_type") or "unknown") for item in failures)), "retrieval_threshold": slo["guardrails"]["retrieval_success_rate_pct_min"]},
        ),
        "cost": panel(
            "cost",
            {"Total": round(sum(costs), 6), "Average/request": round(sum(costs) / len(responses), 6) if responses else None},
            [{"name": "Cumulative cost", "values": cumulative("cost_usd")}],
        ),
        "tokens": panel(
            "tokens",
            {"Input": int(sum(token_in)), "Output": int(sum(token_out)), "Total": int(sum(token_in) + sum(token_out))},
            [
                {"name": "Input", "values": cumulative("tokens_in")},
                {"name": "Output", "values": cumulative("tokens_out")},
                {"name": "Total", "values": [round(a + b) for a, b in zip(cumulative("tokens_in"), cumulative("tokens_out"))]},
            ],
        ),
        "quality": panel(
            "quality",
            {"Average": _mean(qualities), "Responses": len(qualities)},
            [{"name": "Average quality", "values": each(lambda items: _mean(_numbers(by_event(items, "response_sent"), "quality_score")))}],
        ),
    }

    return {
        "title": dashboard["title"],
        "generated_at": now.isoformat(),
        "window_start": start.isoformat(),
        "window_minutes": minutes,
        "refresh_seconds": dashboard["refresh_seconds"],
        "timestamps": [minute.isoformat() for minute in minute_keys],
        "panels": panels,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page() -> HTMLResponse:
    return HTMLResponse(HTML_PATH.read_text(encoding="utf-8"))


@router.get("/dashboard/data")
def dashboard_data() -> dict[str, Any]:
    return build_dashboard()
