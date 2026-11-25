# CloudLog API and Persistence

The backend owns HTTP contracts, authorization, persistence, and orchestration. The processing engine remains independent of FastAPI and SQLAlchemy.

## Install for local development

Requires Python 3.12 or newer. From the `backend` directory:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ..\engine
python -m pip install -e ".[dev]"
```

Run the backend test suite:

```powershell
python -m pytest -v
python -m ruff check app tests
python -m ruff format --check app tests
```

## Database

SQLite is the local default. Run Alembic migrations from this directory:

```powershell
$env:CLOUDLOG_DATABASE_URL = "sqlite:///./cloudlog_lens.db"
python -m alembic -c alembic.ini upgrade head
```

The repository layer accepts an explicit SQLAlchemy session. The caller owns transaction commit/rollback. Event persistence consumes iterables in bounded batches and applies canonical-event redaction before storing the JSON payload. Multiprocessing workers must never write to this database.

PostgreSQL is a later hosted target; local SQLite is the current implementation target. No database is created merely by importing the package.
