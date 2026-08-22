"""
RADAR Backend — Database Connection & Session Management.

Supports SQLite for development and PostgreSQL for production.
Switch by setting the DATABASE_URL environment variable.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Database URL: default to SQLite file in project root for local dev.
# Override with env var DATABASE_URL for PostgreSQL in production.
#   e.g. DATABASE_URL=postgresql://user:pass@host:5432/radar
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./radar.db")

# SQLite requires check_same_thread=False for FastAPI's async context.
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
