# CloudLog Lens

**A privacy-first log analytics and security investigation workspace powered by MapReduce.**

CloudLog Lens is planned as a local-first platform for importing, normalizing, analyzing, and investigating infrastructure logs. It combines a React web interface, a Tauri desktop shell, a FastAPI application layer, and a framework-independent Python MapReduce engine.

> **Project status:** Architecture and repository foundation. This repository currently contains the agreed system design and scaffold; application functionality is not yet implemented.

## Product principles

- **Local-first and privacy-first:** no telemetry by default, no automatic log uploads, and no external AI or reputation calls.
- **Explainable analysis:** findings carry rule identifiers, thresholds, time windows, and supporting evidence. A finding is an investigative lead, not proof of compromise.
- **Real, bounded MapReduce:** streaming ingestion, explicit map/shuffle/reduce stages, disk spill for large jobs, and sequential/parallel correctness parity.
- **One coherent product:** web and desktop share the same TypeScript frontend and API contracts.
- **Modular monolith:** clear package boundaries without premature microservices.

## Architecture

See [System Architecture](docs/architecture/README.md) for the component model, runtime modes, data flow, persistence strategy, security boundaries, and key decisions.

See [Repository Structure](docs/architecture/repository-structure.md) for the canonical folder map and ownership of each package.

## Planned stack

| Area | Technology |
|---|---|
| Web UI | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Desktop shell | Tauri v2 |
| API | Python, FastAPI, Pydantic |
| Persistence | SQLAlchemy, Alembic; SQLite local, PostgreSQL hosted |
| Processing | Standalone Python package with streaming MapReduce |
| Quality | pytest, Ruff, Vitest, Playwright, GitHub Actions |

## Planned capabilities

1. Import Apache/Nginx access logs, JSONL, and staged Linux authentication logs.
2. Normalize records into a canonical event model.
3. Execute streaming MapReduce jobs with measurable stages and bounded memory.
4. Surface explainable signals such as repeated authentication failures, path probing, 404 enumeration, and 5xx spikes.
5. Explore events, job stages, findings, and evidence; export reports.
6. Run locally in a browser or desktop shell, with a later hosted PostgreSQL deployment mode.

## Development status

The current milestone establishes the architecture, package boundaries, repository scaffold, and contributor-facing development guidance. It deliberately does not implement parsers, API endpoints, UI screens, persistence models, or detection rules.

## Documentation

- [Architecture overview](docs/architecture/README.md)
- [Canonical folder structure](docs/architecture/repository-structure.md)
- [Architecture decisions](docs/architecture/decisions/README.md)
- [Development workflow](docs/development/README.md)
- [Security model](docs/security/README.md)
- [Roadmap](ROADMAP.md)

## License

License selection and publication will be finalized before the first distributable release.
