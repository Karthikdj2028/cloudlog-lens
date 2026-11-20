# Security and Privacy Baseline

This document defines design constraints. It is not a claim that security controls are already implemented.

## Data handling

- Local-first: user log data remains on the user's machine unless the user explicitly configures a hosted deployment and uploads data.
- No telemetry by default; no automatic uploads; no external AI processing; no default third-party IP reputation lookups.
- Never use real customer logs as committed fixtures. Prefer synthetic data.
- Redact credentials, tokens, session identifiers, and configured sensitive fields from diagnostics and exports.

## Untrusted input

- Treat all imported bytes, filenames, archive metadata, log fields, and rule parameters as untrusted.
- Enforce maximum file size, decompressed size, line length, event count, processing time, and concurrency.
- Reject or safely handle malformed encodings and oversized records.
- Prevent path traversal and symlink escapes. Resolve paths and verify containment within approved roots.
- Do not execute content from logs, imported archives, or rule files.
- Use strict parser selection and explicit format handling; avoid unsafe deserialization.

## Application security

- Parameterize SQL; scope every hosted query to an authorized workspace.
- Escape all log-derived content in HTML and UI. Never use raw HTML rendering for event fields.
- Protect CSV exports against spreadsheet formula injection.
- Avoid leaking filesystem paths, stack traces, secrets, or raw log payloads in API errors.
- Apply request size limits, rate/concurrency controls, and safe CORS configuration.
- Validate authorization at the service/repository boundary, not only in frontend navigation.

## Desktop security

- Bind the local API to loopback only.
- Generate an unpredictable, ephemeral API token per desktop launch and keep it out of URLs, logs, and persistent frontend assets.
- Restrict Tauri capabilities to the minimum required.
- Validate all file paths on the backend even when selected through a native file picker.
- Shut down the sidecar and clean temporary files on exit.

## Processing safety

- Multiprocessing workers do not write to SQLite.
- Use bounded queues and bounded batches; disk spill uses per-job temporary directories and cleanup.
- Cancellation and worker failure must not leave unbounded orphan processes or temporary files.
- Findings are explainable signals, not proof of compromise. No automatic IP blocking or destructive response.

## Release gate

Before a public release, add regression tests for traversal, archive/decompression limits, unsafe rendering, CSV formula injection, workspace isolation, secret redaction, desktop loopback/token behavior, and dependency vulnerabilities. Document any residual risks.
