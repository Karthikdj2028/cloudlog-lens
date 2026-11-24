# Ingestion and Parser Contracts

## Scope

M2 provides a bounded-memory binary line reader, a streaming parser pipeline,
and built-in parsers for Apache Combined access logs, Nginx Combined access
logs, and JSON Lines objects. It does not implement syslog/auth parsing,
MapReduce, persistence, or job orchestration.

## Streaming reader

`iter_source_lines(stream)` accepts a binary file-like object and reads fixed
size chunks (64 KiB by default). It yields `SourceLine` records with a
1-based line number, zero-based byte offset, and decoded text. UTF-8 is strict
by default; a UTF-8 BOM is removed only at the beginning of the first record.
CRLF is normalized. A final line without a newline is processed.

The default maximum record size is 1 MiB, excluding the newline delimiter.
Oversized records are discarded through the next newline and reported as
`line_too_large`; invalid encoded records are reported as
`invalid_encoding`. Reading resumes after either issue. The reader retains
at most one bounded record plus the current chunk, not the complete input file.

## Parser result model

`parse_stream(stream, parser)` yields one `ParseResult` per physical line.
A result contains either a canonical event, a classified `IngestionIssue`, or
neither for a blank/whitespace-only line that was intentionally skipped.
Issues contain a stable code, a bounded safe message, line number, and byte
offset. Raw source text is never copied into an issue or canonical event.

Issue codes: `line_too_large`, `invalid_encoding`, `malformed_record`,
`invalid_json`, `invalid_timestamp`, `invalid_ip`, and `invalid_field`.

## Access log formats

Apache and Nginx adapters support the standard Combined layout:

`remote_addr ident remote_user [time_local] "request" status bytes "referer" "user-agent"`

The request field accepts an HTTP method, target, and optional HTTP version.
The timestamp uses an English month abbreviation and numeric UTC offset.
Client addresses are validated as IPv4 or IPv6. A dash in optional identity,
status, or byte fields maps to `None`. Arbitrary custom LogFormat definitions
are not inferred.

## JSON Lines mapping

Each nonblank line must be a JSON object with a timezone-aware ISO-8601
`timestamp`, `@timestamp`, `time`, or `ts`. Common aliases are supported for
event type, severity, host, client IP, user, HTTP, authentication, and message
fields. Nested `http`, `auth`/`authentication`, and `attributes` values must
be objects. Unknown top-level keys are preserved as attributes. Duplicate
object keys and non-standard JSON numeric constants are rejected. The input's
`source` property is ignored; source identity is assigned by the caller.

## Privacy and persistence

Parsers apply the configured `RedactionPolicy` (default sensitive-field
redaction) before returning a canonical event. IP masking remains opt-in.
Field-name redaction does not scrub secrets embedded inside arbitrary strings
or URLs. Persistence adapters must still call
`prepare_event_for_persistence` at their durable-write boundary.

## Fixtures and tests

`tests/fixtures/` contains synthetic records only. Tests verify line limits,
offsets, UTF-8 failures, parser mappings, and malformed-record classification.
