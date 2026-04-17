"""Database engine, session factory, and initialization for TEQ."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from teq.models import Base

# The database file lives at data/teq.db relative to the repository root.
# When running from a different working directory, set the TEQ_DB_PATH
# environment variable or pass engine directly.
_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "teq.db"
_DB_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all tables in the database (idempotent)."""
    Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
