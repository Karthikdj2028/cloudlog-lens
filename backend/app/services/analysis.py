"""Incremental analysis orchestration over the standalone engine."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cloudlog_engine.detection import DetectionAccumulator, DetectionConfig, Finding
from cloudlog_engine.schema.events import CanonicalEvent
from sqlalchemy.orm import Session

from .repository import persist_events, persist_findings


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    persisted_events: int
    findings: tuple[Finding, ...]


def persist_and_detect_events(
    session: Session,
    job_id: str,
    events: Iterable[CanonicalEvent],
    *,
    detection_config: DetectionConfig | None = None,
    batch_size: int = 500,
) -> AnalysisSummary:
    """Persist and detect a one-pass stream using bounded event batches.

    The caller owns the surrounding transaction. Detection aggregation retains
    bounded group state and bounded evidence; this function never materializes
    the complete event stream.
    """
    if isinstance(batch_size, bool) or not 1 <= batch_size <= 5000:
        raise ValueError("batch_size must be between 1 and 5000")

    detector = DetectionAccumulator(detection_config)
    batch: list[CanonicalEvent] = []
    persisted = 0
    for event in events:
        detector.add(event)
        batch.append(event)
        if len(batch) >= batch_size:
            persisted += persist_events(session, job_id, batch, batch_size=batch_size)
            batch.clear()

    if batch:
        persisted += persist_events(session, job_id, batch, batch_size=batch_size)

    findings = detector.finish()
    persist_findings(session, job_id, findings)
    return AnalysisSummary(persisted_events=persisted, findings=findings)
