# CloudLog Lens Roadmap

This roadmap describes intended milestones, not completed features.

| Milestone | Scope | Exit criteria |
|---|---|---|
| M0 — Architecture foundation | Architecture, boundaries, repository scaffold, security principles | Docs reviewed; directory ownership clear |
| M1 — Ingestion and parsing | Streaming readers; Apache/Nginx/JSONL parsers; canonical events | Fixtures parse correctly; malformed records reported |
| M2 — MapReduce engine | Sequential and multiprocessing execution; shuffle; reducers; spill | Deterministic equivalence and bounded-resource tests pass |
| M3 — Persistence and detections | SQLite models/migrations; job state; explainable detection rules | Evidence-linked findings and migration tests pass |
| M4 — Web MVP | FastAPI endpoints; React dashboard; import/jobs/events/findings | End-to-end local analysis workflow works |
| M5 — Desktop MVP | Tauri shell; Python sidecar; secure local API | Desktop package starts, analyzes, and shuts down safely |
| M6 — Hardening and hosted mode | PostgreSQL; workspace auth; backups; security/CI | Security regression suite and hosted isolation checks pass |
| M7 — Extensions | Hadoop adapter; live monitoring; custom parsers/rules | Optional integrations remain isolated from local MVP |

## Release strategy

- **v0.1:** Local web workflow for supported files, real MapReduce, initial explainable detections.
- **v0.2:** Desktop packaging and improved investigation/reporting.
- **v0.x:** Hardening, performance, and carefully scoped hosted preview.
- **v1.0:** Stable local product with documented compatibility, security posture, and repeatable release process.

A milestone is not complete because its UI exists. It is complete when its behavior, tests, resource limits, and documentation satisfy the exit criteria.
