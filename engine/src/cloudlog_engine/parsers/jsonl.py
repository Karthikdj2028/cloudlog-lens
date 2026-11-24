"""JSON Lines parser for structured application and infrastructure logs."""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from cloudlog_engine.ingestion.models import (
    IngestionIssueCode,
    ParseResult,
    SourceLine,
)
from cloudlog_engine.parsers.base import BaseParser
from cloudlog_engine.schema.events import (
    AuthenticationInfo,
    CanonicalEvent,
    HTTPInfo,
    SourceInfo,
)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _first(data: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in data:
            return data[name]
    return None


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty ISO-8601 string")
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone offset")
    return parsed


def _optional_int(value: Any) -> Any:
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return value


class JSONLinesParser(BaseParser):
    """Parse one JSON object per line into the canonical event schema.

    The input's source field is intentionally ignored: source identity is
    provided by the ingestion caller, not trusted from the log payload.
    Unknown top-level fields are preserved as bounded event attributes.
    """

    format_name = "jsonl"

    def parse_line(self, line: SourceLine) -> ParseResult:
        if not line.text.strip():
            return self.skipped(line)
        try:
            data = json.loads(
                line.text,
                object_pairs_hook=_unique_object,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_JSON,
                "Record is not a valid JSON object",
            )
        if not isinstance(data, dict):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_JSON,
                "JSON Lines records must be objects",
            )

        timestamp_value = _first(data, "timestamp", "@timestamp", "time", "ts")
        try:
            timestamp = _datetime(timestamp_value)
        except (TypeError, ValueError):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_TIMESTAMP,
                "Timestamp must be a timezone-aware ISO-8601 string",
            )

        observed_at_value = data.get("observed_at")
        observed_at = None
        if observed_at_value is not None:
            try:
                observed_at = _datetime(observed_at_value)
            except (TypeError, ValueError):
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_TIMESTAMP,
                    "observed_at must be a timezone-aware ISO-8601 string",
                )

        client_ip = _first(data, "client_ip", "remote_addr", "ip", "src_ip")
        if client_ip == "-":
            client_ip = None
        if client_ip is not None:
            if not isinstance(client_ip, str):
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_IP,
                    "Client address must be an IPv4/IPv6 address or CIDR string",
                )
            try:
                client_ip = (
                    str(ipaddress.ip_network(client_ip, strict=False))
                    if "/" in client_ip
                    else ipaddress.ip_address(client_ip).compressed
                )
            except ValueError:
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_IP,
                    "Client address must be a valid IPv4/IPv6 address or CIDR",
                )

        http_data = data.get("http")
        if http_data is not None and not isinstance(http_data, dict):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_FIELD,
                "http must be a JSON object",
            )
        http_data = http_data or {}
        http_method = _first(http_data, "method") or _first(data, "http_method", "method")
        http_target = _first(http_data, "target", "path", "url") or _first(
            data, "http_target", "target", "path", "url"
        )
        http_protocol = _first(http_data, "protocol", "http_version") or _first(
            data, "http_protocol", "protocol", "http_version"
        )
        status = _first(http_data, "status_code", "status") 
        if status is None:
            status = _first(data, "status_code", "status")
        response_bytes = _first(http_data, "response_bytes", "bytes_sent")
        if response_bytes is None:
            response_bytes = _first(data, "response_bytes", "bytes_sent")
        duration_ms = _first(http_data, "duration_ms")
        if duration_ms is None:
            duration_ms = data.get("duration_ms")
        try:
            has_http = any(
                value is not None
                for value in (
                    http_method, http_target, http_protocol, status,
                    response_bytes, duration_ms,
                )
            )
            http = (
                HTTPInfo(
                    method=http_method,
                    target=http_target,
                    protocol=http_protocol,
                    status_code=_optional_int(status),
                    response_bytes=_optional_int(response_bytes),
                    duration_ms=duration_ms,
                )
                if has_http else None
            )
        except (TypeError, ValueError):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_FIELD,
                "HTTP fields do not satisfy the canonical event contract",
            )

        auth_data = _first(data, "auth", "authentication")
        if auth_data is not None and not isinstance(auth_data, dict):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_FIELD,
                "auth must be a JSON object",
            )
        auth_data = auth_data or {}
        auth_outcome = _first(auth_data, "outcome") or data.get("auth_outcome")
        auth_action = _first(auth_data, "action") or data.get("auth_action")
        auth_account = _first(auth_data, "account") or data.get("auth_account")
        auth = None
        if any(value is not None for value in (auth_outcome, auth_action, auth_account)):
            try:
                auth = AuthenticationInfo(
                    outcome=auth_outcome or "unknown",
                    action=auth_action,
                    account=auth_account,
                )
            except (TypeError, ValueError):
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_FIELD,
                    "Authentication fields do not satisfy the canonical event contract",
                )

        attributes = data.get("attributes", {})
        if not isinstance(attributes, dict):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_FIELD,
                "attributes must be a JSON object",
            )
        consumed = {
            "timestamp", "@timestamp", "time", "ts", "observed_at", "event_id",
            "schema_version", "event_type", "eventType", "type", "severity", "level",
            "host", "hostname", "client_ip", "remote_addr", "ip", "src_ip",
            "user", "username", "account", "message", "msg", "http", "http_method",
            "method", "http_target", "target", "path", "url", "http_protocol",
            "protocol", "http_version", "status_code", "status", "response_bytes",
            "bytes_sent", "duration_ms", "auth", "authentication", "auth_outcome",
            "auth_action", "auth_account", "attributes", "source",
        }
        merged_attributes = dict(attributes)
        for key, value in data.items():
            if key not in consumed:
                merged_attributes.setdefault(key, value)

        event_type = _first(data, "event_type", "eventType", "type")
        if event_type is None:
            event_type = "auth.activity" if auth is not None else (
                "http.request" if http is not None else "log.record"
            )
        severity = _first(data, "severity", "level") or "unknown"
        host = _first(data, "host", "hostname")
        user = _first(data, "user", "username", "account")
        message = _first(data, "message", "msg")

        try:
            kwargs: dict[str, Any] = {}
            if "event_id" in data:
                kwargs["event_id"] = data["event_id"]
            if "schema_version" in data:
                kwargs["schema_version"] = data["schema_version"]
            if observed_at is not None:
                kwargs["observed_at"] = observed_at
            event = CanonicalEvent(
                timestamp=timestamp,
                event_type=event_type,
                source=SourceInfo(
                    name=self.source_name,
                    format=self.format_name,
                    parser_version=self.parser_version,
                ),
                severity=severity,
                host=host,
                client_ip=client_ip,
                user=user,
                http=http,
                auth=auth,
                message=message,
                attributes=merged_attributes,
                **kwargs,
            )
        except (TypeError, ValueError):
            return self.failure(
                line,
                IngestionIssueCode.INVALID_FIELD,
                "Record fields do not satisfy the canonical event contract",
            )
        return self.success(line, event)
