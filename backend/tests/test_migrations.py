from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_creates_all_persistence_tables(tmp_path, monkeypatch):
    monkeypatch.delenv("CLOUDLOG_DATABASE_URL", raising=False)
    database_path = tmp_path / "migration-test.sqlite"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert {
        "alembic_version",
        "analysis_jobs",
        "log_events",
        "findings",
        "finding_evidence",
        "job_stage_metrics",
    } <= tables
