"""Versioned canonical event contracts used by every ingestion adapter."""

from __future__ import annotations

import ipaddress
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4


class EventSeverity(StrEnum):
    UNKNOWN = "unknown"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuthOutcome(StrEnum):
    UNKNOWN = "unknown"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class SourceInfo:
    """Privacy-safe source identity. name is a logical label, not a file path."""

    name: str
    format: str
    parser_version: str = "1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "source.name", 255))
        object.__setattr__(self, "format", _required_text(self.format, "source.format", 64))
        object.__setattr__(
            self,
            "parser_version",
            _required_text(self.parser_version, "source.parser_version", 64),
        )


@dataclass(frozen=True, slots=True)
class HTTPInfo:
    """HTTP request/response fields common to access-log formats."""

    method: str | None = None
    target: str | None = None
    protocol: str | None = None
    status_code: int | None = None
    response_bytes: int | None = None
    duration_ms: float | None = None

    def __post_init__(self) -> None:
        if self.method is not None:
            method = _required_text(self.method, "http.method", 32).upper()
            object.__setattr__(self, "method", method)
        if self.target is not None:
            object.__setattr__(self, "target", _required_text(self.target, "http.target", 4096))
        if self.protocol is not None:
            object.__setattr__(self, "protocol", _required_text(self.protocol, "http.protocol", 32))
        if self.status_code is not None and (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ValueError("http.status_code must be an integer between 100 and 599")
        if self.response_bytes is not None and (
            isinstance(self.response_bytes, bool)
            or not isinstance(self.response_bytes, int)
            or self.response_bytes < 0
        ):
            raise ValueError("http.response_bytes must be a non-negative integer")
        if self.duration_ms is not None:
            try:
                duration = float(self.duration_ms)
            except (TypeError, ValueError) as exc:
                raise ValueError("http.duration_ms must be numeric") from exc
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("http.duration_ms must be a finite non-negative number")
            object.__setattr__(self, "duration_ms", duration)


@dataclass(frozen=True, slots=True)
class AuthenticationInfo:
    """Authentication activity normalized across authentication log formats."""

    outcome: AuthOutcome = AuthOutcome.UNKNOWN
    action: str | None = None
    account: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "outcome", AuthOutcome(self.outcome))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unsupported auth outcome: {self.outcome!r}") from exc
        if self.action is not None:
            object.__setattr__(self, "action", _required_text(self.action, "auth.action", 128))
        if self.account is not None:
            object.__setattr__(self, "account", _required_text(self.account, "auth.account", 256))


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    """Normalized event shared by parsers, analytics, and detections.

    Raw source lines are intentionally excluded. Retaining raw data must be an
    explicit, separately governed storage decision.
    """

    timestamp: datetime
    event_type: str
    source: SourceInfo
    event_id: str = field(default_factory=lambda: str(uuid4()))
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0"
    severity: EventSeverity = EventSeverity.UNKNOWN
    host: str | None = None
    client_ip: str | None = None  # address or masked CIDR
    user: str | None = None
    http: HTTPInfo | None = None
    auth: AuthenticationInfo | None = None
    message: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _utc_datetime(self.timestamp, "timestamp"))
        object.__setattr__(self, "observed_at", _utc_datetime(self.observed_at, "observed_at"))
        try:
            object.__setattr__(self, "event_id", str(UUID(self.event_id)))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("event_id must be a valid UUID string") from exc
        if self.schema_version != "1.0":
            raise ValueError("schema_version must be '1.0' for this contract")
        object.__setattr__(self, "event_type", _required_text(self.event_type, "event_type", 64))
        if not isinstance(self.source, SourceInfo):
            raise TypeError("source must be a SourceInfo instance")
        try:
            object.__setattr__(self, "severity", EventSeverity(self.severity))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unsupported severity: {self.severity!r}") from exc
        if self.host is not None:
            object.__setattr__(self, "host", _required_text(self.host, "host", 255))
        if self.client_ip is not None:
            raw_ip = _required_text(self.client_ip, "client_ip", 64)
            try:
                normalized_ip = (
                    str(ipaddress.ip_network(raw_ip, strict=False))
                    if "/" in raw_ip
                    else ipaddress.ip_address(raw_ip).compressed
                )
            except ValueError as exc:
                raise ValueError("client_ip must be a valid IP address or CIDR network") from exc
            object.__setattr__(self, "client_ip", normalized_ip)
        if self.user is not None:
            object.__setattr__(self, "user", _required_text(self.user, "user", 256))
        if self.http is not None and not isinstance(self.http, HTTPInfo):
            raise TypeError("http must be an HTTPInfo instance or None")
        if self.auth is not None and not isinstance(self.auth, AuthenticationInfo):
            raise TypeError("auth must be an AuthenticationInfo instance or None")
        if self.message is not None:
            object.__setattr__(self, "message", _required_text(self.message, "message", 8192))
        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        if len(self.attributes) > 128:
            raise ValueError("attributes cannot contain more than 128 top-level keys")
        object.__setattr__(self, "attributes", _freeze_json(dict(self.attributes), depth=0))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable copy without exposing mutable internals."""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "timestamp": _isoformat(self.timestamp),
            "observed_at": _isoformat(self.observed_at),
            "event_type": self.event_type,
            "severity": self.severity.value,
            "source": {
                "name": self.source.name,
                "format": self.source.format,
                "parser_version": self.source.parser_version,
            },
            "host": self.host,
            "client_ip": self.client_ip,
            "user": self.user,
            "http": None
            if self.http is None
            else {
                "method": self.http.method,
                "target": self.http.target,
                "protocol": self.http.protocol,
                "status_code": self.http.status_code,
                "response_bytes": self.http.response_bytes,
                "duration_ms": self.http.duration_ms,
            },
            "auth": None
            if self.auth is None
            else {
                "outcome": self.auth.outcome.value,
                "action": self.auth.action,
                "account": self.auth.account,
            },
            "message": self.message,
            "attributes": _thaw_json(self.attributes),
        }


def _required_text(value: str, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    if len(value) > max_length:
        raise ValueError(f"{field_name} cannot exceed {max_length} characters")
    if "\x00" in value:
        raise ValueError(f"{field_name} cannot contain NUL characters")
    return value


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _freeze_json(value: Any, depth: int) -> Any:
    if depth > 8:
        raise ValueError("attributes nesting cannot exceed 8 levels")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("attribute numbers must be finite")
        return value
    if isinstance(value, str):
        if len(value) > 8192 or "\x00" in value:
            raise ValueError("attribute strings cannot exceed 8192 characters or contain NUL")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, child in value.items():
            if not isinstance(key, str) or not key.strip() or len(key) > 128 or "\x00" in key:
                raise ValueError(
                    "attribute object keys must be non-empty strings of at most 128 characters"
                )
            frozen[key] = _freeze_json(child, depth + 1)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        if len(value) > 1024:
            raise ValueError("attribute arrays cannot contain more than 1024 items")
        return tuple(_freeze_json(child, depth + 1) for child in value)
    raise TypeError(f"attribute value {type(value).__name__} is not JSON-compatible")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(child) for child in value]
    return value


def _isoformat(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
