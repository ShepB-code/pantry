from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pantry_engine.db.models import Base
from pantry_engine.root import repo_root


def resolve_database_url(sqlite_path: Path | None = None) -> str:
    """PostgreSQL when ``DATABASE_URL`` is set; otherwise file-backed SQLite."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    path = sqlite_path or (repo_root() / "data" / "ingest" / "ingestion_runs.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve()}"


@lru_cache
def get_engine(database_url: str | None = None) -> Engine:
    url = database_url or resolve_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


@lru_cache
def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(database_url), autoflush=False, expire_on_commit=False)


def init_db(database_url: str | None = None) -> None:
    """Create tables if they do not exist (dev convenience; prefer Alembic in prod)."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    from pantry_engine.db.seed import ensure_default_location

    with get_session_factory(database_url)() as session:
        ensure_default_location(session)


def check_connection(database_url: str | None = None) -> dict:
    engine = get_engine(database_url)
    url = str(engine.url)
    display_url = url.split("@")[-1] if "@" in url else url
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "database": display_url}
    except Exception as exc:
        return {"ok": False, "database": display_url, "error": str(exc)}


def clear_engine_cache() -> None:
    """Test helper: reset cached engine after env/url changes."""
    get_engine.cache_clear()
    get_session_factory.cache_clear()
