"""Alembic migration environment configuration."""

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool, create_engine

# Ensure backend/ is on sys.path so `app.*` imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.infra.db import Base  # noqa: E402
from app.infra import models  # noqa: E402, F401 — triggers ORM model registration

settings = get_settings()
target_metadata = Base.metadata
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Offline mode: only generate SQL scripts."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online mode: connect to the database and run migrations."""
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
