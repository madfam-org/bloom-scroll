"""Alembic environment configuration.

Rewritten 2026-07-16 after the production feed outage: this file carried
three stacked defects that made `alembic upgrade head` fail in every
production context — silently, because the db-init job also lacked set -e:

1. The URL went through ``config.set_main_option``, whose configparser
   interpolation raises ``invalid interpolation syntax`` on any ``%`` in
   the URL (URL-encoded passwords always contain one).
2. Migrations ran through ``async_engine_from_config`` while every entry
   point (db-init job CLI, API startup safety net) is synchronous.
3. The URL driver was passed through verbatim, so an async
   (``+asyncpg``) secret URL broke sync engines and vice versa.

The environment now builds a plain sync engine straight from settings —
no configparser, no async loop.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# Import settings
from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect them
from app.models.bloom_card import BloomCard  # noqa: F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def _sync_database_url() -> str:
    """Settings URL normalized to a sync psycopg2 form.

    Never feed this to ``config.set_main_option`` — configparser
    interpolation chokes on ``%`` in URL-encoded passwords.
    """
    return (
        settings.DATABASE_URL
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgres://", "postgresql://")
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DBAPI needed)."""
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode over a plain sync engine."""
    connectable = create_engine(_sync_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
