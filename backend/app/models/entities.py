"""Persistence entities for jobs, canonical events, findings, and evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (Index("ix_analysis_jobs_status_created", "status", "created_at"),)

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    input_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parsed_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False, default="0.1.0")

    events: Mapped[list[LogEvent]] = relationship(back_populates="job", cascade="all, delete-orphan")
    findings: Mapped[list[FindingRecord]] = relationship(back_populates="job", cascade="all, delete-orphan")
    stage_metrics: Mapped[list[JobStageMetric]] = relationship(back_populates="job", cascade="all, delete-orphan")


class LogEvent(Base):
    __tablename__ = "log_events"
    __table_args__ = (
        UniqueConstraint("job_id", "event_id", name="uq_log_events_job_event"),
        Index("ix_log_events_job_timestamp", "job_id", "timestamp"),
        Index("ix_log_events_job_client_ip_timestamp", "job_id", "client_ip", "timestamp"),
        Index("ix_log_events_job_event_type_timestamp", "job_id", "event_type", "timestamp"),
        Index("ix_log_events_job_http_status", "job_id", "http_status"),
    )

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[str] = mapped_column(String(32), nullable=False)
    host: Mapped[str | None] = mapped_column(String(255))
    client_ip: Mapped[str | None] = mapped_column(String(64))
    user: Mapped[str | None] = mapped_column(String(256))
    http_method: Mapped[str | None] = mapped_column(String(32))
    http_target: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    auth_outcome: Mapped[str | None] = mapped_column(String(16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    job: Mapped[AnalysisJob] = relationship(back_populates="events")


class FindingRecord(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_job_severity", "job_id", "severity"),
        Index("ix_findings_job_created", "job_id", "created_at"),
    )

    finding_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job: Mapped[AnalysisJob] = relationship(back_populates="findings")
    evidence: Mapped[list[FindingEvidenceRecord]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class FindingEvidenceRecord(Base):
    __tablename__ = "finding_evidence"
    __table_args__ = (
        UniqueConstraint("finding_id", "ordinal", name="uq_finding_evidence_ordinal"),
        Index("ix_finding_evidence_event", "event_id"),
    )

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.finding_id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey("log_events.event_id", ondelete="RESTRICT"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    finding: Mapped[FindingRecord] = relationship(back_populates="evidence")


class JobStageMetric(Base):
    __tablename__ = "job_stage_metrics"
    __table_args__ = (Index("ix_job_stage_metrics_job", "job_id"),)

    metric_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    spill_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    job: Mapped[AnalysisJob] = relationship(back_populates="stage_metrics")
