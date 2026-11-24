"""Bounded-memory binary line reader for log files and file-like objects."""

from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO

from cloudlog_engine.ingestion.models import (
    IngestionIssue,
    IngestionIssueCode,
    SourceLine,
)


def iter_source_lines(
    stream: BinaryIO,
    *,
    chunk_size: int = 64 * 1024,
    max_line_bytes: int = 1024 * 1024,
    encoding: str = "utf-8",
) -> Iterator[SourceLine | IngestionIssue]:
    """Yield decoded lines while bounding memory used for any one record.

    The reader consumes a binary stream in fixed-size chunks. A record larger
    than max_line_bytes is discarded until its newline and represented by a
    LINE_TOO_LARGE issue; it is never accumulated in memory. Invalid encoded
    records are similarly classified and the next line is still processed.

    byte_offset is the zero-based offset of the first byte in the record.
    Newline bytes are excluded from the record-size limit. CRLF is normalized
    by removing the trailing carriage return.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if max_line_bytes < 1:
        raise ValueError("max_line_bytes must be at least 1")
    if not isinstance(encoding, str) or not encoding:
        raise ValueError("encoding must be a non-empty string")

    buffer = bytearray()
    oversized = False
    line_number = 1
    line_offset = 0
    byte_offset = 0

    def append_segment(segment: bytes) -> None:
        nonlocal oversized
        if oversized:
            return
        if len(buffer) + len(segment) > max_line_bytes:
            buffer.clear()
            oversized = True
        else:
            buffer.extend(segment)

    def finish_line() -> SourceLine | IngestionIssue:
        nonlocal buffer, oversized
        if oversized:
            result: SourceLine | IngestionIssue = IngestionIssue(
                code=IngestionIssueCode.LINE_TOO_LARGE,
                message=f"Record exceeds the {max_line_bytes}-byte limit",
                line_number=line_number,
                byte_offset=line_offset,
            )
        else:
            raw = bytes(buffer)
            if raw.endswith(b"\r"):
                raw = raw[:-1]
            try:
                text = raw.decode(encoding, errors="strict")
                if line_number == 1 and text.startswith("\ufeff"):
                    text = text[1:]
                result = SourceLine(
                    line_number=line_number,
                    byte_offset=line_offset,
                    text=text,
                )
            except UnicodeDecodeError:
                result = IngestionIssue(
                    code=IngestionIssueCode.INVALID_ENCODING,
                    message=f"Record is not valid {encoding}",
                    line_number=line_number,
                    byte_offset=line_offset,
                )
        buffer = bytearray()
        oversized = False
        return result

    while True:
        chunk = stream.read(chunk_size)
        if chunk == b"":
            break
        if not isinstance(chunk, bytes):
            raise TypeError("iter_source_lines requires a binary stream returning bytes")

        cursor = 0
        while cursor < len(chunk):
            newline_at = chunk.find(b"\n", cursor)
            if newline_at < 0:
                segment = chunk[cursor:]
                append_segment(segment)
                byte_offset += len(segment)
                break

            segment = chunk[cursor:newline_at]
            append_segment(segment)
            byte_offset += len(segment)
            yield finish_line()
            byte_offset += 1  # newline delimiter
            line_number += 1
            line_offset = byte_offset
            cursor = newline_at + 1

    # A final record without a newline is still a record. Do not invent an
    # extra empty record when the file ends immediately after a newline.
    if buffer or oversized:
        yield finish_line()
