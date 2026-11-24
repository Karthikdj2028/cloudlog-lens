"""Apache and Nginx Common/Combined access-log parsers."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timedelta, timezone

from cloudlog_engine.ingestion.models import (
    IngestionIssueCode,
    ParseResult,
    SourceLine,
)
from cloudlog_engine.parsers.base import BaseParser
from cloudlog_engine.schema.events import (
    CanonicalEvent,
    EventSeverity,
    HTTPInfo,
    SourceInfo,
)

_COMBINED = re.compile(
    r"^(?P<client>\S+) \S+ (?P<user>\S+) "
    r"\[(?P<timestamp>[^\]]+)\] "
    r'"(?P<request>[^"]*)" '
    r"(?P<status>\d{3}|-) (?P<bytes>\d+|-) "
    r'"(?P<referer>[^"]*)" "(?P<agent>[^"]*)"$'
)
_REQUEST = re.compile(
    r"^(?P<method>[!#$%&'*+.^_`|~0-9A-Za-z-]{1,32}) "
    r"(?P<target>\S{1,4096})(?: (?P<protocol>HTTP/\d(?:\.\d)?))?$"
)
_TIMESTAMP = re.compile(
    r"^(?P<day>\d{2})/(?P<month>[A-Za-z]{3})/(?P<year>\d{4}):"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) "
    r"(?P<sign>[+-])(?P<offset_hour>\d{2})(?P<offset_minute>\d{2})$"
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def _parse_access_timestamp(value: str) -> datetime:
    match = _TIMESTAMP.fullmatch(value)
    if match is None:
        raise ValueError("timestamp does not match the access-log timestamp format")
    parts = match.groupdict()
    month = _MONTHS.get(parts["month"])
    if month is None:
        raise ValueError("timestamp contains an unknown month")
    offset_hour = int(parts["offset_hour"])
    offset_minute = int(parts["offset_minute"])
    if offset_hour > 23 or offset_minute > 59:
        raise ValueError("timestamp contains an invalid UTC offset")
    offset = timedelta(hours=offset_hour, minutes=offset_minute)
    if parts["sign"] == "-":
        offset = -offset
    return datetime(
        int(parts["year"]),
        month,
        int(parts["day"]),
        int(parts["hour"]),
        int(parts["minute"]),
        int(parts["second"]),
        tzinfo=timezone(offset),
    )


class _CombinedAccessParser(BaseParser):
    """Shared parser for the standard combined access-log layout."""

    format_name = "access.combined"

    def parse_line(self, line: SourceLine) -> ParseResult:
        if not line.text.strip():
            return self.skipped(line)

        match = _COMBINED.fullmatch(line.text)
        if match is None:
            return self.failure(
                line,
                IngestionIssueCode.MALFORMED_RECORD,
                "Record does not match the combined access-log layout",
            )

        values = match.groupdict()
        try:
            timestamp = _parse_access_timestamp(values["timestamp"])
        except ValueError:
            return self.failure(
                line,
                IngestionIssueCode.INVALID_TIMESTAMP,
                "Access-log timestamp is invalid",
            )

        client_ip = None
        if values["client"] != "-":
            try:
                client_ip = ipaddress.ip_address(values["client"]).compressed
            except ValueError:
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_IP,
                    "Client address is not a valid IPv4 or IPv6 address",
                )

        http = None
        request = values["request"]
        status_code = int(values["status"]) if values["status"] != "-" else None
        response_bytes = int(values["bytes"]) if values["bytes"] != "-" else None
        if request not in {"", "-"}:
            request_match = _REQUEST.fullmatch(request)
            if request_match is None:
                return self.failure(
                    line,
                    IngestionIssueCode.MALFORMED_RECORD,
                    "HTTP request field is malformed",
                )
            parts = request_match.groupdict()
            try:
                http = HTTPInfo(
                    method=parts["method"],
                    target=parts["target"],
                    protocol=parts["protocol"],
                    status_code=status_code,
                    response_bytes=response_bytes,
                )
            except (TypeError, ValueError):
                return self.failure(
                    line,
                    IngestionIssueCode.INVALID_FIELD,
                    "HTTP access-log fields are invalid",
                )
        elif status_code is not None or response_bytes is not None:
            http = HTTPInfo(status_code=status_code, response_bytes=response_bytes)

        severity = EventSeverity.UNKNOWN
        if status_code is not None:
            severity = (
                EventSeverity.ERROR
                if status_code >= 500
                else EventSeverity.WARNING
                if status_code >= 400
                else EventSeverity.INFO
            )

        attributes = {
            "referer": values["referer"],
            "user_agent": values["agent"],
        }
        event = CanonicalEvent(
            timestamp=timestamp,
            event_type="http.request",
            source=SourceInfo(
                name=self.source_name,
                format=self.format_name,
                parser_version=self.parser_version,
            ),
            severity=severity,
            client_ip=client_ip,
            user=None if values["user"] == "-" else values["user"],
            http=http,
            attributes=attributes,
        )
        return self.success(line, event)


class ApacheCombinedParser(_CombinedAccessParser):
    """Parse Apache httpd's standard LogFormat combined access records."""

    format_name = "apache.combined"


class NginxCombinedParser(_CombinedAccessParser):
    """Parse Nginx's standard access_log combined format."""

    format_name = "nginx.combined"
