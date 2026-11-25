"""Persistence operations; transaction commit/rollback remains with the caller."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from itertools import islice
from uuid import uuid4

from cloudlog_engine.detection import Finding
from cloudlog_engine.schema.events import CanonicalEvent
from cloudlog_engine.schema.redaction import RedactionPolicy, prepare_event_for_persistence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisJob, FindingEvidenceRecord, FindingRecord, JobStageMetric, LogEvent

_JOB_TRANSITIONS = {
    "queued": {"running", "cancelled", "failed"},
    "running": {"succeeded", "failed", "cancelled"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
}
_SAFE_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class RepositoryError(Exception):
    """Base error for invalid persistence operations."""


class InvalidJobTransition(RepositoryError):
    """Raised when a job state transition is not allowed."""


class MissingEvidenceEvent(RepositoryError):
    """Raised when a finding references an event outside this job."""


def create_job(session: Session, source_name: str, *, now: datetime | None = None) -> AnalysisJob:
    if not source_name or len(source_name) > 255 or "\x00" in source_name:
        raise ValueError("source_name must contain 1-255 safe characters")
    job = AnalysisJob(
        job_id=str(uuid4()),
        source_name=source_name,
        status="queued",
        created_at=(now or datetime.now(UTC)).astimezone(UTC),
    )
    session.add(job)
    session.flush()
    return job


def transition_job(
    session: Session,
    job_id: str,
    new_status: str,
    *,
    error_code: str | None = None,
    now: datetime | None = None,
) -> AnalysisJob:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise RepositoryError("analysis job not found")
    if new_status not in _JOB_TRANSITIONS:
        raise ValueError("unsupported job status")
    if new_status not in _JOB_TRANSITIONS[job.status]:
        raise InvalidJobTransition(f"cannot transition job from {job.status} to {new_status}")
    if error_code is not None and not _SAFE_ERROR_CODE.fullmatch(error_code):
        raise ValueError("error_code must be a safe machine-readable identifier")
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    job.status = new_status
    if new_status == "running":
        job.started_at = timestamp
    if new_status in {"succeeded", "failed", "cancelled"}:
        job.finished_at = timestamp
    job.error_code = error_code if new_status == "failed" else None
    session.flush()
    return job


def persist_events(
    session: Session,
    job_id: str,
    events: Iterable[CanonicalEvent],
    *,
    redaction_policy: RedactionPolicy | None = None,
    batch_size: int = 500,
) -> int:
    """Consume and persist an event stream in bounded batches in the caller transaction."""
    if isinstance(batch_size, bool) or not 1 <= batch_size <= 5000:
        raise ValueError("batch_size must be between 1 and 5000")
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise RepositoryError("analysis job not found")
    if job.status != "running":
        raise InvalidJobTransition("events can only be persisted while a job is running")

    iterator = iter(events)
    count = 0
    while batch := list(islice(iterator, batch_size)):
        rows = []
        for original in batch:
            if not isinstance(original, CanonicalEvent):
                raise TypeError("events must contain CanonicalEvent instances")
            event = prepare_event_for_persistence(original, redaction_policy)
            rows.append(
                LogEvent(
                    event_id=event.event_id,
                    job_id=job_id,
                    timestamp=event.timestamp,
                    observed_at=event.observed_at,
                    event_type=event.event_type,
                    severity=event.severity.value,
                    source_name=event.source.name,
                    source_format=event.source.format,
                    host=event.host,
                    client_ip=event.client_ip,
                    user=event.user,
                    http_method=event.http.method if event.http else None,
                    http_target=event.http.target if event.http else None,
                    http_status=event.http.status_code if event.http else None,
                    auth_outcome=event.auth.outcome.value if event.auth else None,
                    payload=event.to_dict(),
                )
            )
        session.add_all(rows)
        session.flush()
        count += len(rows)
    job.parsed_events += count
    session.flush()
    return count


def persist_findings(session: Session, job_id: str, findings: tuple[Finding, ...]) -> int:
    job = session.get(AnalysisJob, job_id)
    if job is None:
        raise RepositoryError("analysis job not found")
    if job.status != "running":
        raise InvalidJobTransition("findings can only be persisted while a job is running")

    event_ids = {item.event_id for finding in findings for item in finding.evidence}
    if event_ids:
        stored = set(
            session.scalars(
                select(LogEvent.event_id).where(
                    LogEvent.job_id == job_id, LogEvent.event_id.in_(event_ids)
                )
            ).all()
        )
        if stored != event_ids:
            raise MissingEvidenceEvent("finding evidence must reference events from this job")

    for finding in findings:
        session.add(
            FindingRecord(
                finding_id=finding.finding_id,
                job_id=job_id,
                rule_id=finding.rule_id,
                rule_version=finding.rule_version,
                title=finding.title,
                description=finding.description,
                severity=finding.severity.value,
                subject=finding.subject,
                window_start=finding.window_start,
                window_end=finding.window_end,
                threshold=finding.threshold,
                observed_value=finding.observed_value,
                created_at=datetime.now(UTC),
                evidence=[
                    FindingEvidenceRecord(
                        evidence_id=str(uuid4()),
                        event_id=item.event_id,
                        ordinal=ordinal,
                        timestamp=item.timestamp,
                    )
                    for ordinal, item in enumerate(finding.evidence)
                ],
            )
        )
    session.flush()
    job.finding_count += len(findings)
    session.flush()
    return len(findings)


def record_stage_metric(
    session: Session,
    job_id: str,
    stage: str,
    record_count: int,
    duration_seconds: float,
    spill_bytes: int = 0,
) -> JobStageMetric:
    if (
        not stage
        or len(stage) > 64
        or isinstance(record_count, bool)
        or not isinstance(record_count, int)
        or record_count < 0
        or isinstance(spill_bytes, bool)
        or not isinstance(spill_bytes, int)
        or spill_bytes < 0
        or not math.isfinite(duration_seconds)
        or duration_seconds < 0
    ):
        raise ValueError("invalid stage metric")
    if session.get(AnalysisJob, job_id) is None:
        raise RepositoryError("analysis job not found")
    metric = JobStageMetric(
        metric_id=str(uuid4()),
        job_id=job_id,
        stage=stage,
        record_count=record_count,
        duration_seconds=duration_seconds,
        spill_bytes=spill_bytes,
    )
    session.add(metric)
    session.flush()
    return metric


def list_job_events(session: Session, job_id: str, *, limit: int = 100, offset: int = 0):
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError("limit must be 1-500 and offset cannot be negative")
    return session.scalars(
        select(LogEvent)
        .where(LogEvent.job_id == job_id)
        .order_by(LogEvent.timestamp, LogEvent.event_id)
        .limit(limit)
        .offset(offset)
    ).all()


def list_job_findings(session: Session, job_id: str, *, limit: int = 100, offset: int = 0):
    if not 1 <= limit <= 500 or offset < 0:
        raise ValueError("limit must be 1-500 and offset cannot be negative")
    return session.scalars(
        select(FindingRecord)
        .where(FindingRecord.job_id == job_id)
        .order_by(FindingRecord.created_at, FindingRecord.finding_id)
        .limit(limit)
        .offset(offset)
    ).all()
