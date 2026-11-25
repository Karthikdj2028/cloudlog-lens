"""Bounded, deterministic detection rules over canonical events."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote, urlsplit

from cloudlog_engine.schema.events import AuthOutcome, CanonicalEvent

from .models import DetectionConfig, DetectionEvidence, Finding, FindingSeverity


@dataclass(slots=True)
class _Bucket:
    count: int = 0
    evidence: list[DetectionEvidence] = field(default_factory=list)


def _window_start(timestamp: datetime, seconds: int) -> datetime:
    value = timestamp.astimezone(UTC)
    epoch = int(value.timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=UTC)


def _suspicious_target(target: str) -> str | None:
    decoded = unquote(target).casefold()
    path = urlsplit(decoded).path
    indicators = (
        ("path-traversal", "../" in path or path.startswith("/..")),
        ("environment-file-probe", path.endswith("/.env") or path == "/.env"),
        ("passwd-file-probe", "/etc/passwd" in path),
        ("proc-environment-probe", "/proc/self/environ" in path),
        ("script-injection-probe", "<script" in decoded),
        ("sql-injection-probe", "union select" in decoded or "or 1=1" in decoded),
    )
    return next((name for name, matched in indicators if matched), None)


class DetectionAccumulator:
    """Incremental detector for streams; retained state is explicitly bounded."""

    def __init__(self, config: DetectionConfig | None = None) -> None:
        self.config = config or DetectionConfig()
        self._groups: dict[tuple[str, str, datetime], _Bucket] = {}
        self._findings: list[Finding] = []
        self._result: tuple[Finding, ...] | None = None

    def _add(self, rule_id: str, subject: str, start: datetime, event: CanonicalEvent) -> None:
        key = (rule_id, subject, start)
        bucket = self._groups.get(key)
        if bucket is None:
            if len(self._groups) >= self.config.max_groups:
                raise ValueError("detection group limit exceeded")
            bucket = self._groups[key] = _Bucket()
        bucket.count += 1
        if len(bucket.evidence) < self.config.max_evidence_per_finding:
            bucket.evidence.append(DetectionEvidence(event.event_id, event.timestamp))

    def add(self, event: CanonicalEvent) -> None:
        """Consume one canonical event without retaining its raw source text."""
        if self._result is not None:
            raise RuntimeError("cannot add events after detection has been finalized")
        if not isinstance(event, CanonicalEvent):
            raise TypeError("DetectionAccumulator accepts CanonicalEvent instances only")

        auth_failed = (
            event.auth is not None and event.auth.outcome == AuthOutcome.FAILURE
        ) or event.event_type.casefold() in {"auth.failure", "login.failure"}
        if auth_failed:
            account = (
                event.auth.account if event.auth and event.auth.account
                else event.user or "unknown"
            )
            self._add(
                "auth.repeated_failures",
                f"ip={event.client_ip or 'unknown'};account={account}",
                _window_start(event.timestamp, self.config.failed_login_window_seconds),
                event,
            )

        if event.http is None:
            return

        if event.http.status_code is not None and event.http.status_code >= 500:
            self._add(
                "http.server_error_burst",
                f"ip={event.client_ip or 'unknown'}",
                _window_start(event.timestamp, self.config.server_error_window_seconds),
                event,
            )
        if event.client_ip is not None:
            self._add(
                "traffic.high_request_rate",
                f"ip={event.client_ip}",
                _window_start(event.timestamp, self.config.request_rate_window_seconds),
                event,
            )
        if event.http.target:
            indicator = _suspicious_target(event.http.target)
            if indicator is not None:
                if len(self._findings) >= self.config.max_findings:
                    raise ValueError("detection finding limit exceeded")
                self._findings.append(
                    Finding.build(
                        rule_id=f"web.{indicator}",
                        rule_version="1.0.0",
                        title="Suspicious URL pattern observed",
                        description=(
                            f"The request target matched the {indicator} indicator. "
                            "This may be benign testing or scanning; investigate the "
                            "request context and surrounding events."
                        ),
                        severity=FindingSeverity.MEDIUM,
                        subject=f"ip={event.client_ip or 'unknown'}",
                        window_start=event.timestamp,
                        window_end=event.timestamp,
                        threshold=1,
                        observed_value=1,
                        evidence=(DetectionEvidence(event.event_id, event.timestamp),),
                    )
                )

    def finish(self) -> tuple[Finding, ...]:
        """Finalize and return findings in stable order."""
        if self._result is not None:
            return self._result

        rules = (
            (
                "auth.repeated_failures",
                self.config.failed_login_threshold,
                self.config.failed_login_window_seconds,
                FindingSeverity.HIGH,
                "Repeated authentication failures",
                "Multiple authentication failures occurred for the same source/account "
                "within one UTC tumbling window.",
            ),
            (
                "http.server_error_burst",
                self.config.server_error_threshold,
                self.config.server_error_window_seconds,
                FindingSeverity.MEDIUM,
                "HTTP server error burst",
                "The source generated repeated HTTP 5xx responses within one UTC tumbling window.",
            ),
            (
                "traffic.high_request_rate",
                self.config.request_rate_threshold,
                self.config.request_rate_window_seconds,
                FindingSeverity.MEDIUM,
                "Unusually high request rate",
                "The source generated a high number of HTTP requests within one UTC tumbling window.",
            ),
        )
        metadata = {
            rule_id: (threshold, seconds, severity, title, description)
            for rule_id, threshold, seconds, severity, title, description in rules
        }
        for (rule_id, subject, start), bucket in self._groups.items():
            threshold, seconds, severity, title, description = metadata[rule_id]
            if bucket.count < threshold:
                continue
            if len(self._findings) >= self.config.max_findings:
                raise ValueError("detection finding limit exceeded")
            evidence = tuple(
                sorted(bucket.evidence, key=lambda item: (item.timestamp, item.event_id))
            )
            self._findings.append(
                Finding.build(
                    rule_id=rule_id,
                    rule_version="1.0.0",
                    title=title,
                    description=description,
                    severity=severity,
                    subject=subject,
                    window_start=start,
                    window_end=start + timedelta(seconds=seconds),
                    threshold=threshold,
                    observed_value=bucket.count,
                    evidence=evidence,
                )
            )

        self._result = tuple(
            sorted(
                self._findings,
                key=lambda item: (
                    item.rule_id,
                    item.window_start,
                    item.subject,
                    item.finding_id,
                ),
            )
        )
        return self._result


def run_detections(
    events: Iterable[CanonicalEvent],
    config: DetectionConfig | None = None,
) -> tuple[Finding, ...]:
    """Run built-in rules over an iterable using bounded incremental state.

    Windows are deterministic UTC tumbling windows. Group state, evidence
    retained per finding, and total findings are explicitly bounded. Findings
    are investigative leads, not proof of compromise.
    """
    accumulator = DetectionAccumulator(config)
    for event in events:
        accumulator.add(event)
    return accumulator.finish()
