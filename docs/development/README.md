# Development Workflow

## Current milestone

The repository currently contains architecture documentation and an empty directory scaffold. No backend, engine, frontend, desktop shell, or CI test suite has been implemented yet. Do not interpret `.gitkeep` placeholders as working packages.

## Planned local prerequisites

Versions will be pinned in the relevant manifests when each package is introduced. Expected toolchain:

- Python 3.12+ for the API and processing engine.
- Node.js LTS and a package manager for the React frontend.
- Rust stable and Tauri v2 prerequisites for desktop packaging.
- Git and a supported SQLite runtime.

## Milestone sequence

1. **M0 — Architecture foundation:** architecture docs, package boundaries, repository scaffold, security principles. (This milestone.)
2. **M1 — Ingestion and parsing:** streaming readers, Apache/Nginx/JSONL parsers, canonical event contract, parser fixtures.
3. **M2 — MapReduce engine:** sequential runner, multiprocessing runner, partition/shuffle/reduce, bounded spill, metrics, equivalence tests.
4. **M3 — Persistence and detections:** SQLAlchemy models, Alembic migrations, job lifecycle, explainable rules/evidence.
5. **M4 — Web application:** FastAPI API, shared React experience, import workflow, job progress, dashboards and event/finding explorers.
6. **M5 — Desktop application:** Tauri v2 shell, sidecar lifecycle, local security boundary, packaging.
7. **M6 — Hardening and hosted deployment:** security regression tests, PostgreSQL, workspace authorization, backups, release automation.
8. **M7 — Extensions:** optional Hadoop Streaming/HDFS adapter, live tailing, custom parsers/rules, community integrations.

## Engineering workflow

- Start each milestone with repository inspection and a written scope.
- Create a focused branch and keep commits reviewable.
- Write or update tests alongside implementation; do not defer all tests to the end.
- Run formatters, linters, type checks, unit tests, and relevant integration tests before claiming completion.
- Record exact commands and outcomes. If a check cannot run, state why; never report it as passed.
- Keep dependencies pinned and review licenses, maintenance, and supply-chain posture.
- Do not commit real logs, credentials, personal data, databases, or generated build output.
- Use synthetic fixtures with documented provenance.
- Update docs when an architectural boundary changes.

## Definition of done

A milestone is complete only when its stated deliverables exist, the scope has not silently expanded, relevant tests/checks have been run, failures and limitations are documented, and the repository status/commit evidence is reported.
