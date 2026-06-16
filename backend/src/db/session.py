from __future__ import annotations

from contextlib import contextmanager
import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from .models import Base


logger = logging.getLogger(__name__)
settings = get_settings()
database_path = Path(settings.database_path)
database_path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"duckdb:///{path}", future=True)


def _build_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _fallback_database_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.local{path.suffix}")


def _is_lock_error(error: OperationalError) -> bool:
    message = str(error).lower()
    return "being used by another process" in message or "cannot access the file" in message


engine = _build_engine(database_path)
SessionLocal = _build_session_factory(engine)
active_database_path = database_path


def _activate_database(path: Path) -> None:
    global engine, SessionLocal, active_database_path
    engine = _build_engine(path)
    SessionLocal = _build_session_factory(engine)
    active_database_path = path


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Using DuckDB database at %s", active_database_path)
    except OperationalError as exc:
        if not _is_lock_error(exc):
            raise

        fallback_path = _fallback_database_path(database_path)
        logger.warning(
            "Primary DuckDB file %s is locked by another process; falling back to %s",
            database_path,
            fallback_path,
        )
        _activate_database(fallback_path)
        Base.metadata.create_all(bind=engine)
        logger.info("Using fallback DuckDB database at %s", active_database_path)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
