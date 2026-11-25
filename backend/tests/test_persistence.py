from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.database import build_engine, build_session_factory, session_scope
from app.models import Base, FindingEvidenceRecord
from app.services.repository import (
    InvalidJobTransition,
    MissingEvidenceEvent,
    create_job,
    list_job_events,
    list_job_findings,
    persist_events,
    persist_findings,
    record_stage_metric,
    transition_job,
)
from cloudlog_engine.detection import DetectionConfig, run_detections
from cloudlog_engine.schema.events import (
    AuthOutcome,
    AuthenticationInfo,
    CanonicalEvent,
    SourceInfo,
)


@pytest.fixture
def session_factory():
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


def make_event(index: int, *, seconds: int = 0) -> CanonicalEvent:
    timestamp = datetime(2026, 11, 25, 10, 0, tzinfo=UTC) + timedelta(seconds=seconds)
    return CanonicalEvent(
        timestamp=timestamp,
        source=SourceInfo(name="synthetic", format="test"),
        event_id=f"10000000-0000-4000-8000-{index:012d}",
        event_type="auth.failure",
        client_ip="192.0.2.20",
        auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="analyst"),
        attributes={"password": "should-not-persist", "request": {"token": "secret"}},
    )


def test_job_event_finding_lifecycle_and_redaction(session_factory):
    events = [make_event(i, seconds=i * 10) for i in range(1, 4)]
    with session_scope(session_factory) as session:
        job = create_job(session, "synthetic-auth.log")
        transition_job(session, job.job_id, "running")
        count = persist_events(session, job.job_id, iter(events), batch_size=2)
        findings = run_detections(events, DetectionConfig(failed_login_threshold=3))
        assert count == 3
        assert persist_findings(session, job.job_id, findings) == 1
        record_stage_metric(session, job.job_id, "map", 3, 0.025, 0)
        transition_job(session, job.job_id, "succeeded")
        job_id = job.job_id

    with session_factory() as session:
        stored_events = list_job_events(session, job_id)
        stored_findings = list_job_findings(session, job_id)
        assert len(stored_events) == 3
        assert stored_events[0].payload["attributes"]["password"] == "[REDACTED]"
        assert stored_events[0].payload["attributes"]["request"]["token"] == "[REDACTED]"
        assert len(stored_findings) == 1
        assert stored_findings[0].rule_id == "auth.repeated_failures"
        assert len(stored_findings[0].evidence) == 3


def test_finding_cannot_reference_another_jobs_event(session_factory):
    event = make_event(1)
    (finding,) = run_detections([event], DetectionConfig(failed_login_threshold=1))
    with session_scope(session_factory) as session:
        first = create_job(session, "first.log")
        transition_job(session, first.job_id, "running")
        persist_events(session, first.job_id, [event])
        second = create_job(session, "second.log")
        transition_job(session, second.job_id, "running")
        with pytest.raises(MissingEvidenceEvent):
            persist_findings(session, second.job_id, (finding,))


def test_job_state_machine_rejects_terminal_transition(session_factory):
    with session_scope(session_factory) as session:
        job = create_job(session, "sample.log")
        transition_job(session, job.job_id, "cancelled")
        with pytest.raises(InvalidJobTransition):
            transition_job(session, job.job_id, "running")


def test_event_persistence_requires_running_job(session_factory):
    with session_scope(session_factory) as session:
        job = create_job(session, "sample.log")
        with pytest.raises(InvalidJobTransition):
            persist_events(session, job.job_id, [make_event(1)])


def test_pagination_is_bounded(session_factory):
    with session_scope(session_factory) as session:
        job = create_job(session, "sample.log")
        transition_job(session, job.job_id, "running")
        persist_events(session, job.job_id, [make_event(i) for i in range(1, 4)])
        with pytest.raises(ValueError):
            list_job_events(session, job.job_id, limit=501)


def test_evidence_foreign_key_is_persisted(session_factory):
    event = make_event(1)
    (finding,) = run_detections([event], DetectionConfig(failed_login_threshold=1))
    with session_scope(session_factory) as session:
        job = create_job(session, "sample.log")
        transition_job(session, job.job_id, "running")
        persist_events(session, job.job_id, [event])
        persist_findings(session, job.job_id, (finding,))
        evidence = session.scalars(select(FindingEvidenceRecord)).all()
        assert evidence[0].event_id == event.event_id
