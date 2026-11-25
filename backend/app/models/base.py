"""SQLAlchemy declarative base for local and hosted persistence."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared metadata root for Alembic and test database creation."""
