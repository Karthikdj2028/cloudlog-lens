"""Typed, deterministic contracts for explainable security detections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid5


_FINDING_NAMESPACE = UUID("2b7f93a8-1d3a-4d1e-a0c2-7a61b25b1d6f")


class FindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Resource limits and thresholds for the built-in deterministic rules."""

    failed_login_threshold: int = 5
    failed_login_window_seconds: int = 300
    server_error_threshold: int = 10
    server_error_window_seconds: int = 60
    request_rate_threshold: int = 120
    request_rate_window_seconds: int = 60
    max_groups: int = 100_000
    max_evidence_per_finding: int = 20
    max_findings: int = 10_000

    def __post_init__(self) -> None:
        for name in (
            "failed_login_threshold",
            "failed_login_window_seconds",
            "server_error_threshold",
            "server_error_window_seconds",
            "request_rate_threshold",
            "request_rate_window_seconds",
            "max_groups",
            "max_evidence_per_finding",
            "max_findings",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class DetectionEvidence:
    """A reference to a canonical event; raw log lines are never copied."""

    event_id: str
    timestamp: datetime

    def __post_init__(self) -> None:
        UUID(self.event_id)
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("evidence timestamp must be timezone-aware")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class Finding:
    """A finding with explicit rule provenance, threshold, window, and evidence."""

    finding_id: str
    rule_id: str
    rule_version: str
    title: str
    description: str
    severity: FindingSeverity
    subject: str
    window_start: datetime
    window_end: datetime
    threshold: int
    observed_value: int
    evidence: tuple[DetectionEvidence, ...]

    def __post_init__(self) -> None:
        UUID(self.finding_id)
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("finding windows must be timezone-aware")
        if self.window_end < self.window_start:
            raise ValueError("finding window_end cannot precede window_start")
        if self.threshold < 1 or self.observed_value < self.threshold:
            raise ValueError("finding values must satisfy the configured threshold")
        if not self.rule_id or not self.rule_version or not self.evidence:
            raise ValueError("finding requires rule metadata and at least one evidence item")

    @classmethod
    def build(
        cls,
        *,
        rule_id: str,
        rule_version: str,
        title: str,
        description: str,
        severity: FindingSeverity,
        subject: str,
        window_start: datetime,
        window_end: datetime,
        threshold: int,
        observed_value: int,
        evidence: tuple[DetectionEvidence, ...],
    ) -> Finding:
        """Build a stable ID from the rule, subject, and window."""
        identity = "|".join(
            (
                rule_id,
                subject,
                window_start.astimezone(UTC).isoformat(),
                window_end.astimezone(UTC).isoformat(),
            )
        )
        return cls(
            finding_id=str(uuid5(_FINDING_NAMESPACE, identity)),
            rule_id=rule_id,
            rule_version=rule_version,
            title=title,
            description=description,
            severity=severity,
            subject=subject,
            window_start=window_start.astimezone(UTC),
            window_end=window_end.astimezone(UTC),
            threshold=threshold,
            observed_value=observed_value,
            evidence=evidence,
        )
