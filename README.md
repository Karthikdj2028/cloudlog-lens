# CloudLog Lens

**A privacy-first log analytics and security investigation workspace powered by MapReduce.**

CloudLog Lens is a local-first platform for importing, normalizing, analyzing, and investigating infrastructure logs. It combines a React web client, a planned Tauri desktop shell, a FastAPI application layer, and a framework-independent Python processing engine.

> **Current status:** M0 and M1 foundations are implemented. M2 is in progress: bounded-memory ingestion, Apache/Nginx Combined parsing, and JSON Lines parsing are being added. MapReduce execution, persistence, API behavior, and product screens remain future work.

## Product principles

- Local-first and privacy-first: no telemetry by default, no automatic log uploads, and no external AI or reputation calls.
- Explainable analysis: findings carry rule identifiers, thresholds, time windows, and supporting evidence. A finding is an investigative lead, not proof of compromise.
- Real, bounded MapReduce: streaming ingestion, explicit map/shuffle/reduce stages, disk spill for large jobs, and sequential/parallel correctness parity.
- Shared web and desktop experience, with the desktop shell reusing the frontend.
- Modular monolith with a standalone processing engine; no premature microservices.

## Repository architecture

- `engine/`: framework-independent Python event schema, parsers, MapReduce, and detection.
- `backend/`: FastAPI application, persistence boundary, and job orchestration.
- `frontend/`: React + TypeScript + Vite browser client.
- `desktop/`: planned Tauri v2 shell and Python sidecar lifecycle.
- `docs/`: architecture, development, and security specifications.
- `tests/fixtures/`: synthetic or explicitly licensed test data only.

See [System Architecture](docs/architecture/README.md), [Canonical Repository Structure](docs/architecture/repository-structure.md), and [Development Workflow](docs/development/README.md).

## Development

Engine tests (standard library only):

    PYTHONPATH=engine/src python3 -m unittest discover -s engine/tests -v

Install and run the engine package:

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e "./engine[dev]"
    python -m pytest engine/tests

Frontend validation:

    cd frontend
    npm install
    npm run typecheck
    npm run build

Backend and desktop implementations are scheduled for later milestones. See [ROADMAP.md](ROADMAP.md).

## License

License selection and publication will be finalized before the first distributable release.
