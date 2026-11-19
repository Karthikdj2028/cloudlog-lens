# CloudLog Lens Roadmap

This roadmap describes intended milestones, not completed features.

| Milestone | Scope | Exit criteria |
|---|---|---|
| M0 — Architecture foundation | Architecture, boundaries, repository policy, security principles | Docs reviewed; responsibilities and dependency direction clear |
| M1 — Repository and event schema | Monorepo scaffold, development configs, canonical event v1.0, redaction, schema tests | Python package installs; event/redaction tests and frontend type/build checks pass |
| M2 — Ingestion and parsing | Streaming readers; Apache/Nginx/JSONL parsers; parser fixtures | Fixtures parse correctly; malformed records are classified |
| M3 — MapReduce engine | Sequential and multiprocessing execution; shuffle; reducers; spill | Deterministic equivalence and bounded-resource tests pass |
| M4 — Persistence and detections | SQLite models/migrations; job state; explainable detection rules | Evidence-linked findings and migration tests pass |
| M5 — Web MVP | FastAPI endpoints; React dashboard; import/jobs/events/findings | End-to-end local analysis workflow works |
| M6 — Desktop MVP | Tauri shell; Python sidecar; secure local API | Desktop package starts, analyzes, and shuts down safely |
| M7 — Hardening and extensions | PostgreSQL hosted mode; workspace auth; Hadoop adapter; live monitoring | Security regression suite and hosted isolation checks pass |

## Release strategy

- **v0.1:** Local web workflow for supported files, real MapReduce, initial explainable detections.
- **v0.2:** Desktop packaging and improved investigation/reporting.
- **v0.x:** Hardening, performance, and carefully scoped hosted preview.
- **v1.0:** Stable local product with documented compatibility, security posture, and repeatable release process.

A milestone is not complete because its scaffold or UI exists. It is complete when its behavior, tests, resource limits, and documentation satisfy the exit criteria.
