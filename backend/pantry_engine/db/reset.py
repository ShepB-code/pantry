from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from pantry_engine.db.session import clear_engine_cache, get_engine, resolve_database_url


def reset_database(database_url: str | None = None) -> str:
    """Drop all Pantry tables (Postgres: public schema; SQLite: delete file)."""
    clear_engine_cache()
    url = database_url or resolve_database_url()

    if url.startswith("sqlite"):
        engine = get_engine(url)
        engine.dispose()
        clear_engine_cache()
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.unlink(missing_ok=True)
        return f"deleted SQLite file {db_path}"

    engine = get_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    clear_engine_cache()
    display = url.split("@")[-1] if "@" in url else url
    return f"dropped and recreated public schema on {display}"
