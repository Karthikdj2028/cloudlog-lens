from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cloudlog_engine.detection import DetectionAccumulator, DetectionConfig
from cloudlog_engine.schema.events import (
    AuthenticationInfo,
    AuthOutcome,
    CanonicalEvent,
    HTTPInfo,
    SourceInfo,
)


def make_event(index: int, target: str = "/ok") -> CanonicalEvent:
    return CanonicalEvent(
        timestamp=datetime(2026, 11, 25, 10, 0, tzinfo=UTC),
        source=SourceInfo(name="stream", format="test"),
        event_id=f"30000000-0000-4000-8000-{index:012d}",
        event_type="auth.failure",
        client_ip="203.0.113.10",
        auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="svc"),
        http=HTTPInfo(method="GET", target=target, status_code=400),
    )


def test_accumulator_can_process_one_event_at_a_time():
    detector = DetectionAccumulator(DetectionConfig(failed_login_threshold=3))
    for index in range(1, 4):
        detector.add(make_event(index))
    findings = detector.finish()
    assert any(item.rule_id == "auth.repeated_failures" for item in findings)
    assert detector.finish() == findings


def test_accumulator_rejects_events_after_finalization():
    detector = DetectionAccumulator()
    detector.finish()
    with pytest.raises(RuntimeError, match="finalized"):
        detector.add(make_event(1))


def test_malformed_absolute_url_is_ignored_without_crashing():
    detector = DetectionAccumulator()
    detector.add(make_event(1, "http://[invalid-ipv6"))
    assert detector.finish() == ()
