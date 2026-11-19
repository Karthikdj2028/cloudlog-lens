# CloudLog Engine

Standalone Python package for log ingestion, parsing, canonical normalization, MapReduce, analytics, detection, and export.

## Independence contract

The engine has no runtime dependency on FastAPI, Pydantic, SQLAlchemy, Tauri, React, or a database. The initial canonical event and redaction implementation uses only the Python standard library.

## Development

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
```

A dependency-free test invocation is also supported from the repository root:

```bash
PYTHONPATH=engine/src python3 -m unittest discover -s engine/tests -v
```

## Canonical event contract

The first schema version is `1.0`. See `src/cloudlog_engine/schema/events.py`. Events are immutable, timestamps must be timezone-aware and are normalized to UTC, client IP fields accept an address or an explicitly masked CIDR, and extension attributes are bounded JSON-compatible data.

Call `prepare_event_for_persistence(event, policy)` during normalization and before any durable write. Sensitive attribute keys are redacted by default; client-network masking is configurable. Never persist raw source lines through this event contract.
