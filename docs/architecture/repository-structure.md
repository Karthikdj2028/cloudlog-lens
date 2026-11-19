# Canonical Repository Structure

The repository uses a decoupled monorepo. The engine, API, frontend, and desktop host have separate ownership and package configuration; only the backend may depend on the engine.

```text
cloudlog-lens/
├── .github/workflows/                 # CI
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── api/                       # FastAPI REST routers
│   │   ├── core/                      # Config, security, DB session, logging
│   │   ├── models/                    # SQLAlchemy entities
│   │   ├── services/                  # Application orchestration
│   │   └── alembic/                   # Database migrations
│   └── tests/
├── desktop/                           # Tauri v2 host (later milestone)
├── engine/
│   ├── pyproject.toml
│   ├── src/cloudlog_engine/
│   │   ├── schema/                    # Canonical event schema and redaction
│   │   ├── parsers/                   # Apache, Nginx, JSONL, syslog/auth
│   │   ├── mapreduce/                 # Reader, chunking, map, shuffle, reduce
│   │   └── detection/                 # Rules and evidence models
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── components/
│       ├── features/
│       ├── hooks/
│       └── services/
├── docs/                              # Architecture and development specs
├── infrastructure/                    # Optional local/hosted operational assets
├── rules/                             # Declarative detection rule definitions
├── sample-data/                       # Synthetic or explicitly licensed samples
├── tests/fixtures/                     # Shared synthetic fixtures
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── SECURITY.md
```

## Package ownership and dependency direction

- `engine/` owns canonical events, parsers, normalization, MapReduce, and detection contracts. It has no runtime dependency on FastAPI, SQLAlchemy, Tauri, or frontend code.
- `backend/` owns HTTP endpoints, settings, authorization, persistence, and orchestration. It may call the engine through its public Python API; the reverse dependency is forbidden.
- `frontend/` owns the browser experience and communicates with the backend through versioned HTTP contracts. It never accesses the database directly.
- `desktop/` owns Tauri lifecycle and sidecar integration. It reuses the frontend rather than forking product UI.
- `rules/` contains declarative, versioned detection rules; it must not become an arbitrary code execution surface.
- `sample-data/` and `tests/fixtures/` contain synthetic or explicitly licensed records only.
- `infrastructure/` holds reproducible operational assets; it must not absorb application domain logic.

## Runtime and privacy conventions

- Local workflows use SQLite; hosted multi-user deployments target PostgreSQL.
- Normalize timestamps to UTC and validate canonical event fields before downstream processing.
- Apply configured field redaction and optional IP masking during normalization, before persistence.
- Never commit `.env` files, databases, raw logs, credentials, caches, or generated build output.
- Empty directories use `.gitkeep` until a milestone introduces their first real implementation file.

## Implementation status

- M1 provides the package metadata, canonical event schema, redaction helpers, tests, and minimal frontend toolchain entry point.
- Parser, MapReduce, detection, API, persistence, full UI, and desktop runtime directories are reserved for later milestones.
- A placeholder directory does not mean its planned capability is implemented.
