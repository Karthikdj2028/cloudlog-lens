# M4 — Persistence and Explainable Detection

## Scope

M4 implements the local persistence and deterministic detection foundation. It does not claim that the REST API, dashboard, desktop runtime, PostgreSQL hosted deployment, or Linux authentication parser is complete; those belong to later work or parser-specific follow-up.

## Engine detection

The framework-independent `cloudlog_engine.detection` package accepts canonical events and emits immutable findings. Built-in version 1.0.0 rules cover:

- Repeated authentication failures by source IP/account in configurable UTC tumbling windows.
- HTTP 5xx bursts by source IP.
- High HTTP request rates by source IP.
- Suspicious URL indicators including path traversal, environment-file probes, passwd/proc probes, script tags, and basic SQL-injection patterns.

The incremental `DetectionAccumulator` supports one-pass streams. It caps unique groups, evidence references per finding, and total findings. Rule thresholds are defaults and can be changed through `DetectionConfig`. These rules are heuristic signals and can produce false positives.

## Persistence

The backend owns SQLAlchemy entities and repositories for analysis jobs, canonical events, findings, finding evidence, and MapReduce stage metrics. SQLite is the tested local target. Alembic revision `0001_initial` creates the initial schema.

Repository operations require an explicit SQLAlchemy session; the application boundary owns transaction commit/rollback. Events are redacted through `prepare_event_for_persistence` before the JSON payload is stored. Event streams are consumed in bounded batches. Evidence writes verify that every referenced event belongs to the same analysis job.

Job transitions are explicit: queued → running → succeeded/failed/cancelled, or queued → failed/cancelled. Terminal states cannot be reopened.

## One-pass orchestration

`persist_and_detect_events` feeds each canonical event into the incremental detector and persists bounded batches. It does not materialize the full event stream. The caller owns the transaction; for a large job, choose transaction boundaries deliberately and persist job failure state if processing aborts.

## Validation

Engine tests cover thresholds, UTC window boundaries, suspicious URL patterns, deterministic IDs/order, group limits, and bounded evidence. Backend tests cover migration execution, SQLite job lifecycle, event redaction, evidence/job integrity, pagination limits, and one-pass streaming across batch boundaries.

## Known limitations

- The initial rules use UTC tumbling windows, not sliding windows or statistical baselines.
- URL checks are deliberately small pattern indicators, not a full web-attack classifier.
- Authentication detections work on canonical authentication events; raw Linux auth/syslog parsing is not yet implemented.
- SQLite is the current local persistence target. PostgreSQL and hosted workspace isolation remain later work.
- FastAPI endpoints, asynchronous job worker, SSE progress, dashboard, and exports are not part of M4.
