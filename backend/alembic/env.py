from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from pantry_engine.db.models import Base

_backend_dir = Path(__file__).resolve().parents[1]
load_dotenv(_backend_dir / ".env")
load_dotenv()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("DATABASE_URL="):
        url = url.removeprefix("DATABASE_URL=").strip()
    if not url:
        raise RuntimeError(
            "Set DATABASE_URL in backend/.env before running Alembic, e.g.\n"
            "DATABASE_URL=postgresql+psycopg://pantry:pantry@127.0.0.1:5432/pantry"
        )
    if "://" not in url:
        raise RuntimeError(f"DATABASE_URL does not look like a URL: {url!r}")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
