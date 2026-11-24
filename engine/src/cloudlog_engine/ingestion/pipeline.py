"""Composition of the streaming reader and a line parser."""

from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO, Protocol

from cloudlog_engine.ingestion.models import (
    IngestionIssue,
    ParseResult,
    SourceLine,
)
from cloudlog_engine.ingestion.reader import iter_source_lines


class LineParser(Protocol):
    """Minimal contract required by the streaming ingestion pipeline."""

    def parse_line(self, line: SourceLine) -> ParseResult:
        """Normalize one source line without retaining its raw text."""


def parse_stream(
    stream: BinaryIO,
    parser: LineParser,
    *,
    chunk_size: int = 64 * 1024,
    max_line_bytes: int = 1024 * 1024,
    encoding: str = "utf-8",
) -> Iterator[ParseResult]:
    """Stream source bytes into parser outcomes without materializing the file."""
    for record in iter_source_lines(
        stream,
        chunk_size=chunk_size,
        max_line_bytes=max_line_bytes,
        encoding=encoding,
    ):
        if isinstance(record, IngestionIssue):
            yield ParseResult(
                line_number=record.line_number,
                byte_offset=record.byte_offset,
                issue=record,
            )
        else:
            yield parser.parse_line(record)
