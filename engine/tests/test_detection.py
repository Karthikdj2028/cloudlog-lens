from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cloudlog_engine.detection import DetectionConfig, FindingSeverity, run_detections
from cloudlog_engine.schema.events import (
    AuthenticationInfo,
    AuthOutcome,
    CanonicalEvent,
    HTTPInfo,
    SourceInfo,
)

BASE = datetime(2026, 11, 25, 10, 0, tzinfo=UTC)


def make_event(
    index: int,
    *,
    seconds: int = 0,
    event_type: str = "http.access",
    ip: str = "192.0.2.10",
    status: int | None = 200,
    target: str = "/index.html",
    auth: AuthenticationInfo | None = None,
) -> CanonicalEvent:
    timestamp = BASE + timedelta(seconds=seconds)
    return CanonicalEvent(
        timestamp=timestamp,
        source=SourceInfo(name="synthetic", format="test"),
        event_id=f"00000000-0000-4000-8000-{index:012d}",
        event_type=event_type,
        client_ip=ip,
        auth=auth,
        http=(
            HTTPInfo(method="GET", target=target, status_code=status)
            if event_type.startswith("http")
            else None
        ),
    )


def test_repeated_login_failures_include_threshold_and_bounded_evidence():
    events = [
        make_event(
            index,
            seconds=index * 30,
            event_type="auth.failure",
            status=None,
            auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="alice"),
        )
        for index in range(1, 4)
    ]
    findings = run_detections(
        events,
        DetectionConfig(failed_login_threshold=3, max_evidence_per_finding=2),
    )
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "auth.repeated_failures"
    assert finding.severity == FindingSeverity.HIGH
    assert finding.threshold == 3
    assert finding.observed_value == 3
    assert len(finding.evidence) == 2


def test_login_failures_in_separate_tumbling_windows_do_not_combine():
    events = [
        make_event(
            1,
            seconds=1,
            event_type="auth.failure",
            status=None,
            auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="alice"),
        ),
        make_event(
            2,
            seconds=301,
            event_type="auth.failure",
            status=None,
            auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="alice"),
        ),
    ]
    assert not run_detections(events, DetectionConfig(failed_login_threshold=2))


def test_server_error_burst_and_high_request_rate_are_distinct_rules():
    events = [make_event(i, seconds=i, status=500) for i in range(1, 4)]
    findings = run_detections(
        events,
        DetectionConfig(server_error_threshold=3, request_rate_threshold=3),
    )
    assert {item.rule_id for item in findings} == {
        "http.server_error_burst",
        "traffic.high_request_rate",
    }


def test_request_rate_counts_http_requests_even_without_status_code():
    events = [make_event(i, status=None) for i in range(1, 3)]
    findings = run_detections(events, DetectionConfig(request_rate_threshold=2))
    assert [item.rule_id for item in findings] == ["traffic.high_request_rate"]


@pytest.mark.parametrize(
    ("target", "rule_id"),
    [
        ("/../../etc/passwd", "web.path-traversal"),
        ("/.env", "web.environment-file-probe"),
        ("/search?q=UNION%20SELECT%20password", "web.sql-injection-probe"),
        ("/<script>alert(1)</script>", "web.script-injection-probe"),
    ],
)
def test_suspicious_url_indicators(target: str, rule_id: str):
    (finding,) = run_detections([make_event(1, target=target)])
    assert finding.rule_id == rule_id
    assert finding.evidence[0].event_id == "00000000-0000-4000-8000-000000000001"


def test_detection_ids_and_order_are_deterministic():
    events = [make_event(i, seconds=i) for i in range(1, 4)]
    config = DetectionConfig(server_error_threshold=2, request_rate_threshold=2)
    first = run_detections(events, config)
    second = run_detections(events, config)
    assert first == second


def test_detection_group_limit_is_enforced():
    events = [make_event(i, ip=f"192.0.2.{i}") for i in range(1, 4)]
    with pytest.raises(ValueError, match="group limit"):
        run_detections(events, DetectionConfig(max_groups=2))
