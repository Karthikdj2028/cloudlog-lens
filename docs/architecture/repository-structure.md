# Canonical Repository Structure

The active implementation layout follows the M1 monorepo plan. Existing M0 documentation paths are retained for continuity; the following is the canonical source layout for new code.

```text
cloudlog-lens/
├── .github/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── alembic/
│   └── tests/
├── desktop/                         # Tauri v2 host (later desktop milestone)
├── engine/
│   ├── pyproject.toml
│   ├── src/cloudlog_engine/
│   │   ├── schema/                  # Canonical event contract and redaction
│   │   ├── parsers/
│   │   ├── mapreduce/
│   │   └── detection/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── components/
│       ├── features/
│       ├── hooks/
│       └── services/
├── docs/
├── infrastructure/
├── rules/
├── sample-data/
├── tests/
│   └── fixtures/                    # Synthetic / licensed fixtures only
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── SECURITY.md
```

## Package ownership and dependency direction

- `engine/` owns canonical events, parsing, normalization, MapReduce, and detection contracts. It has no runtime dependency on FastAPI, SQLAlchemy, Tauri, or frontend code.
- `backend/` owns HTTP endpoints, settings, authorization, persistence, and orchestration. It may call the engine through its public Python API; the reverse dependency is forbidden.
- `frontend/` owns the browser experience and communicates with the backend through versioned HTTP contracts. It never accesses the database directly.
- `desktop/` owns Tauri lifecycle and sidecar integration. It reuses the frontend rather than forking product UI.
- `rules/` contains declarative, versioned detection rules; it must not become an arbitrary code execution surface.
- `tests/fixtures/` contains synthetic or explicitly licensed records only.

## Runtime and privacy conventions

- Local workflows use SQLite; hosted multi-user deployments target PostgreSQL.
- Normalize timestamps to UTC and validate canonical event fields before downstream processing.
- Apply configured field redaction and optional IP masking during normalization, before persistence.
- Never commit `.env` files, databases, raw logs, credentials, caches, or generated build output.
- Empty directories use `.gitkeep` until a milestone introduces their first real implementation file.

## Compatibility note

The original M0 scaffold used `apps/web/`, `apps/desktop/`, `backend/cloudlog_api/`, and `engine/cloudlog_engine/`. Those placeholders are retained on the M1 branch to avoid destructive moves during review. New implementation work uses `frontend/`, `desktop/`, `backend/app/`, and `engine/src/cloudlog_engine/`. A dedicated cleanup can remove obsolete placeholders after the migration is accepted.
