"""Shared parser behavior and privacy-safe result construction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cloudlog_engine.ingestion.models import (
    IngestionIssue,
    IngestionIssueCode,
    ParseResult,
    SourceLine,
)
from cloudlog_engine.schema.events import CanonicalEvent
from cloudlog_engine.schema.redaction import RedactionPolicy, apply_redaction


class BaseParser(ABC):
    """Base for deterministic one-line parsers."""

    format_name = "unknown"
    parser_version = "1"

    def __init__(
        self,
        *,
        source_name: str | None = None,
        redaction_policy: RedactionPolicy | None = None,
    ) -> None:
        self.source_name = source_name or self.format_name
        self.redaction_policy = redaction_policy or RedactionPolicy()

    @abstractmethod
    def parse_line(self, line: SourceLine) -> ParseResult:
        """Parse one line, returning an event, a classified issue, or a skip."""

    def success(self, line: SourceLine, event: CanonicalEvent) -> ParseResult:
        # The default field-redaction policy is applied during normalization,
        # before the event is returned to any caller that may persist it.
        safe_event = apply_redaction(event, self.redaction_policy)
        return ParseResult(
            line_number=line.line_number,
            byte_offset=line.byte_offset,
            event=safe_event,
        )

    @staticmethod
    def failure(
        line: SourceLine,
        code: IngestionIssueCode,
        message: str,
    ) -> ParseResult:
        return ParseResult(
            line_number=line.line_number,
            byte_offset=line.byte_offset,
            issue=IngestionIssue(
                code=code,
                message=message,
                line_number=line.line_number,
                byte_offset=line.byte_offset,
            ),
        )

    @staticmethod
    def skipped(line: SourceLine) -> ParseResult:
        return ParseResult(line_number=line.line_number, byte_offset=line.byte_offset)
