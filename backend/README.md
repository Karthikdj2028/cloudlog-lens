# CloudLog API

FastAPI application boundary for HTTP contracts, authorization, persistence, and job orchestration.

The API layer may depend on the standalone engine. The engine must never import this package.

This milestone creates configuration and package boundaries only. Routers, database models,
workers, and service implementations will be added in later milestones.

## Development

Create a virtual environment, then install this package with its development extra:

    python -m pip install -e ".[dev]"

Run backend tests from this directory with:

    python -m pytest
