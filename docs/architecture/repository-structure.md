# Canonical Repository Structure

This tree is the agreed target layout. Empty package directories are represented by `.gitkeep` until their milestone adds real source files. Do not create placeholder implementation modules merely to make the tree look populated.

```text
cloudlog-lens/
├── apps/
│   ├── web/                         # Shared React + TypeScript frontend
│   │   ├── public/
│   │   └── src/
│   │       ├── app/                  # App shell, router, providers
│   │       ├── components/           # Shared UI components
│   │       ├── features/             # Feature-oriented screens and state
│   │       ├── hooks/
│   │       ├── lib/                  # API client, utilities
│   │       ├── styles/
│   │       └── types/
│   └── desktop/                     # Tauri v2 host and desktop packaging
│       ├── src/
│       └── src-tauri/
│           ├── capabilities/
│           ├── icons/
│           └── src/
├── backend/
│   └── cloudlog_api/
│       ├── api/v1/                   # Versioned HTTP routers
│       ├── core/                     # Settings, security, errors, logging
│       ├── dependencies/             # Request-scoped dependency wiring
│       ├── models/                   # SQLAlchemy persistence models
│       ├── repositories/             # Database access
│       ├── schemas/                  # Pydantic contracts
│       ├── services/                 # Application orchestration
│       └── workers/                  # Background job execution
├── engine/
│   └── cloudlog_engine/
│       ├── ingestion/
│       ├── parsers/
│       ├── normalization/
│       ├── mapreduce/
│       ├── analytics/
│       ├── detection/
│       └── export/
├── contracts/                        # Canonical event and API contract docs
├── docs/
│   ├── architecture/
│   │   └── decisions/
│   ├── development/
│   └── security/
├── infrastructure/
│   ├── docker/
│   └── scripts/
├── migrations/
│   └── versions/
├── rules/
│   └── detections/
├── sample-data/
│   ├── apache/
│   ├── nginx/
│   ├── jsonl/
│   └── linux-auth/
├── tests/
│   ├── unit/
│   │   ├── engine/
│   │   ├── backend/
│   │   └── frontend/
│   ├── integration/
│   ├── e2e/
│   ├── fixtures/
│   └── performance/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
├── .editorconfig
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE (choose before first release)
├── README.md
├── ROADMAP.md
└── SECURITY.md
```

## Dependency direction

```text
apps/web ───────────────► backend HTTP API
apps/desktop ───────────► apps/web + local API sidecar
backend/cloudlog_api ───► engine/cloudlog_engine
backend/cloudlog_api ───► persistence / migrations
engine/cloudlog_engine ─► Python standard library + focused engine dependencies
rules ──────────────────► consumed by engine detection layer
contracts ──────────────► referenced by API, engine, and frontend tests
```

The engine must not import the API, ORM, UI, or desktop host. The frontend must not access the database directly. Desktop-specific OS integration must not leak into web feature modules.

## Directory ownership

| Directory | Responsibility | Not responsible for |
|---|---|---|
| `apps/web` | Browser UI and shared client logic | Parsing files, database access |
| `apps/desktop` | Tauri host, packaging, sidecar lifecycle | Detection logic, MapReduce |
| `backend/cloudlog_api` | HTTP, authorization, orchestration, persistence boundary | Core map/shuffle/reduce algorithms |
| `engine/cloudlog_engine` | Parsing, normalization, processing, analytics, detection | HTTP, ORM sessions, UI |
| `rules` | Versioned detection definitions and metadata | Executable arbitrary user code |
| `migrations` | Schema evolution | Runtime business logic |
| `contracts` | Shared schemas and compatibility expectations | UI components |
| `sample-data` | Synthetic or explicitly licensed fixtures | Real customer logs |
| `tests` | Unit, integration, end-to-end, performance verification | Production runtime code |
| `infrastructure` | Reproducible local/hosted operational assets | Application domain logic |

## Naming and packaging conventions

- Python import package: `cloudlog_engine` and `cloudlog_api`.
- Python modules: lowercase `snake_case.py`; public types use CapWords.
- TypeScript components: `PascalCase.tsx`; hooks use `useThing.ts`.
- Feature modules should be grouped by product capability, not by file extension alone.
- API routes remain under `/api/v1`; breaking external contract changes require a versioning decision.
- Detection rules carry stable IDs and explicit versions.
- Keep generated output, local databases, uploaded logs, secrets, caches, and build artifacts out of Git.

## Scaffold policy

A `.gitkeep` means only that the directory is reserved for a planned responsibility. It does not indicate that the package is implemented or ready to import. Remove a placeholder when the first real file is added.
