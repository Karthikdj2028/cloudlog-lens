# Development Workflow

## Current state

M0 architecture documentation is established. M1 adds the monorepo workspace scaffold, Python package metadata, a minimal React toolchain entry point, the canonical event schema v1.0, redaction helpers, unit tests, and the initial CI checks. Log parsers, MapReduce algorithms, API endpoints, persistence models, product screens, and the Tauri runtime are still future work.

## Local prerequisites

- Python 3.12+ for the engine and API.
- Node.js 24 and npm for the frontend scaffold.
- Rust stable and Tauri v2 prerequisites when the desktop milestone begins.
- Git and SQLite for later local persistence work.

## M0–M7 sequence

1. **M0 — Architecture foundation:** architecture docs, package boundaries, initial repository policy, and security principles.
2. **M1 — Repository and event schema:** monorepo scaffold, development manifests, canonical event contract v1.0, redaction utilities, and schema tests.
3. **M2 — Ingestion and parsing:** streaming readers, Apache/Nginx/JSONL parsers, parser fixtures, and malformed-record reporting.
4. **M3 — MapReduce engine:** sequential reference runner, multiprocessing runner, partition/shuffle/reduce, bounded spill, metrics, and equivalence tests.
5. **M4 — Persistence and detections:** SQLAlchemy models, Alembic migrations, job lifecycle, explainable rules, and evidence.
6. **M5 — Web application:** FastAPI API, shared React experience, import workflow, job progress, dashboards, and event/finding explorers.
7. **M6 — Desktop application:** Tauri v2 shell, sidecar lifecycle, loopback/token security, and packaging.
8. **M7 — Hardening and extensions:** PostgreSQL hosted mode, workspace authorization, security regression tests, optional Hadoop/HDFS, live tailing, and custom rules.

## Engine development

From the repository root, run the dependency-free unit suite:

    PYTHONPATH=engine/src python3 -m unittest discover -s engine/tests -v

Install the engine package and development tools:

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e "./engine[dev]"
    python -m pytest engine/tests
    ruff check engine/src engine/tests

## Frontend development

    cd frontend
    npm install
    npm run typecheck
    npm run build

## Engineering workflow

- Inspect the repository and define scope before each milestone.
- Keep milestones on focused branches and submit reviewable pull requests.
- Add tests alongside behavior; run formatter, lint, type checks, and relevant suites before claiming completion.
- Record exact commands and outcomes. If a check cannot run, state why.
- Pin direct dependencies and review maintenance, license, and supply-chain posture.
- Do not commit real logs, credentials, personal data, local databases, or generated build output.
- Use synthetic fixtures with documented provenance.
- Update architecture and roadmap documents when package ownership changes.

## Definition of done

A milestone is complete only when deliverables exist, scope is respected, CI checks pass, documentation reflects actual behavior, and remaining limitations are stated.
