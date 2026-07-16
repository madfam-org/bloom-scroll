"""Alembic schema convergence shared by the db-init Job and API startup.

The production database predates alembic tracking: it was bootstrapped by
hand in 2026-04, so it has real tables but no ``alembic_version`` row.
``alembic upgrade head`` on such a database dies on the first
``CREATE TABLE`` (DuplicateTable — the 2026-07-16 db-init Job failure that
blocked every ArgoCD sync once #107 made migrations actually run).

:func:`ensure_schema` adopts that state: when tables exist but tracking
doesn't, stamp the baseline revision the bootstrap corresponds to, then
upgrade to head. Migrations 002/003 carry existence guards so any partially
bootstrapped schema converges to the same result.

Entry points:

- db-init Job (ArgoCD PreSync hook): ``python -m app.core.migrations``
- API startup safety net: :func:`ensure_schema` via ``app.main.lifespan``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import pool

logger = logging.getLogger(__name__)

# Revision the pre-alembic production schema corresponds to: 001 created
# bloom_cards, the table the 2026-04 bootstrap left behind. 002/003 are
# guarded, so stamping the oldest plausible baseline is always safe.
ADOPTION_BASELINE = "001"


def alembic_config() -> Any:
    from alembic.config import Config as AlembicConfig

    backend_dir = Path(__file__).resolve().parents[2]
    cfg = AlembicConfig(str(backend_dir / "alembic.ini"))
    # A relative script_location resolves against the process cwd, not the
    # ini file; pin it so every entry point works from any directory.
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    return cfg


def alembic_head() -> str | None:
    """The newest migration revision shipped in this image."""
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def sync_database_url() -> str:
    """Settings URL normalized to the sync psycopg2 driver.

    Never feed this to ``config.set_main_option`` — configparser
    interpolation chokes on ``%`` in URL-encoded passwords.
    """
    from app.core.config import settings

    return (
        settings.DATABASE_URL
        .replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgres://", "postgresql://")
    )


def _needs_adoption() -> bool:
    """True when the DB has real tables but no alembic_version tracking."""
    engine = sa.create_engine(sync_database_url(), poolclass=pool.NullPool)
    try:
        inspector = sa.inspect(engine)
        return bool(
            inspector.has_table("bloom_cards")
            and not inspector.has_table("alembic_version")
        )
    finally:
        engine.dispose()


def ensure_schema() -> None:
    """Bring the database to alembic head from any starting state."""
    from alembic import command

    cfg = alembic_config()
    if _needs_adoption():
        logger.warning(
            "Database predates alembic tracking; stamping baseline %s before upgrade",
            ADOPTION_BASELINE,
        )
        command.stamp(cfg, ADOPTION_BASELINE)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_schema()
