from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from cloudlog_engine.detection import DetectionConfig
from cloudlog_engine.schema.events import (
    AuthenticationInfo,
    AuthOutcome,
    CanonicalEvent,
    SourceInfo,
)

from app.core.database import build_engine, build_session_factory, session_scope
from app.models import Base
from app.services.analysis import persist_and_detect_events
from app.services.repository import create_job, list_job_events, list_job_findings, transition_job


@pytest.fixture
def session_factory():
    engine = build_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield build_session_factory(engine)
    engine.dispose()


def event(index: int) -> CanonicalEvent:
    return CanonicalEvent(
        timestamp=datetime(2026, 11, 25, 10, 0, tzinfo=UTC) + timedelta(seconds=index),
        source=SourceInfo(name="stream", format="test"),
        event_id=f"20000000-0000-4000-8000-{index:012d}",
        event_type="auth.failure",
        client_ip="198.51.100.7",
        auth=AuthenticationInfo(outcome=AuthOutcome.FAILURE, account="service"),
    )


def test_stream_is_persisted_in_batches_and_detected_across_batch_boundaries(session_factory):
    source = (event(index) for index in range(1, 8))
    with session_scope(session_factory) as session:
        job = create_job(session, "stream.log")
        transition_job(session, job.job_id, "running")
        result = persist_and_detect_events(
            session,
            job.job_id,
            source,
            detection_config=DetectionConfig(failed_login_threshold=7),
            batch_size=2,
        )
        assert result.persisted_events == 7
        assert len(result.findings) == 1
        assert result.findings[0].observed_value == 7
        job_id = job.job_id

    with session_factory() as session:
        assert len(list_job_events(session, job_id)) == 7
        findings = list_job_findings(session, job_id)
        assert len(findings) == 1
        assert findings[0].rule_id == "auth.repeated_failures"


def test_streaming_service_rejects_invalid_batch_size(session_factory):
    with session_scope(session_factory) as session:
        job = create_job(session, "stream.log")
        transition_job(session, job.job_id, "running")
        with pytest.raises(ValueError):
            persist_and_detect_events(session, job.job_id, [], batch_size=0)
