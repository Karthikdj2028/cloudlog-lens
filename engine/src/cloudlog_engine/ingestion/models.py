"""Small immutable records shared by readers and parsers.

These records deliberately contain source coordinates and classified errors,
not the raw log line. Raw input remains transient inside the reader/parser.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cloudlog_engine.schema.events import CanonicalEvent


class IngestionIssueCode(StrEnum):
    LINE_TOO_LARGE = "line_too_large"
    INVALID_ENCODING = "invalid_encoding"
    MALFORMED_RECORD = "malformed_record"
    INVALID_JSON = "invalid_json"
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_IP = "invalid_ip"
    INVALID_FIELD = "invalid_field"


@dataclass(frozen=True, slots=True)
class SourceLine:
    """One decoded source record and its zero-based byte location."""

    line_number: int
    byte_offset: int
    text: str

    def __post_init__(self) -> None:
        if self.line_number < 1:
            raise ValueError("line_number must be positive")
        if self.byte_offset < 0:
            raise ValueError("byte_offset cannot be negative")
        if not isinstance(self.text, str):
            raise TypeError("text must be a string")


@dataclass(frozen=True, slots=True)
class IngestionIssue:
    """A safe, bounded description of a reader or parser failure."""

    code: IngestionIssueCode
    message: str
    line_number: int
    byte_offset: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", IngestionIssueCode(self.code))
        if not self.message or len(self.message) > 256 or "\x00" in self.message:
            raise ValueError("issue message must contain 1-256 safe characters")
        if self.line_number < 1:
            raise ValueError("line_number must be positive")
        if self.byte_offset < 0:
            raise ValueError("byte_offset cannot be negative")


@dataclass(frozen=True, slots=True)
class ParseResult:
    """The outcome for one physical input line.

    event and issue are mutually exclusive. Neither means the line was
    intentionally skipped (currently blank/whitespace-only input).
    """

    line_number: int
    byte_offset: int
    event: CanonicalEvent | None = None
    issue: IngestionIssue | None = None

    def __post_init__(self) -> None:
        if self.line_number < 1:
            raise ValueError("line_number must be positive")
        if self.byte_offset < 0:
            raise ValueError("byte_offset cannot be negative")
        if self.event is not None and self.issue is not None:
            raise ValueError("a parse result cannot contain both an event and an issue")
        if self.event is not None and not isinstance(self.event, CanonicalEvent):
            raise TypeError("event must be a CanonicalEvent instance")

    @property
    def is_skipped(self) -> bool:
        return self.event is None and self.issue is None
