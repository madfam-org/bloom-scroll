"""Schema convergence tests (2026-07-16 feed outage, layer 3).

Layer 1 (#106) and layer 2 (#107) made ``alembic upgrade head`` actually
run in production — where it promptly died with DuplicateTable, because the
prod database was bootstrapped by hand in 2026-04 and has real tables but
no ``alembic_version`` row. That failure ran inside the db-init PreSync
hook, so it blocked every ArgoCD sync.

These tests cover the adoption path in ``app.core.migrations``: stamp the
baseline revision when tables exist without tracking, then upgrade, with
migrations 002/003 guarded so any partially bootstrapped schema converges.
"""

from pathlib import Path
from unittest import mock

import pytest

from app.core import migrations as m

REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeInspector:
    def __init__(self, tables: set[str]) -> None:
        self._tables = tables

    def has_table(self, name: str) -> bool:
        return name in self._tables


def _patch_inspection(monkeypatch: pytest.MonkeyPatch, tables: set[str]) -> mock.MagicMock:
    engine = mock.MagicMock()
    monkeypatch.setattr(m.sa, "create_engine", mock.MagicMock(return_value=engine))
    monkeypatch.setattr(m.sa, "inspect", mock.MagicMock(return_value=_FakeInspector(tables)))
    return engine


class TestNeedsAdoption:
    def test_pre_alembic_database_needs_adoption(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Tables exist but alembic_version doesn't: the 2026-04 prod state."""
        _patch_inspection(monkeypatch, {"bloom_cards"})
        assert m._needs_adoption() is True

    def test_tracked_database_does_not(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_inspection(monkeypatch, {"bloom_cards", "alembic_version"})
        assert m._needs_adoption() is False

    def test_fresh_database_does_not(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _patch_inspection(monkeypatch, set())
        assert m._needs_adoption() is False

    def test_engine_disposed_even_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = _patch_inspection(monkeypatch, set())
        monkeypatch.setattr(m.sa, "inspect", mock.MagicMock(side_effect=RuntimeError("boom")))
        with pytest.raises(RuntimeError):
            m._needs_adoption()
        engine.dispose.assert_called_once()


class TestEnsureSchema:
    def test_adoption_stamps_baseline_before_upgrade(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, str]] = []
        monkeypatch.setattr(m, "_needs_adoption", lambda: True)
        monkeypatch.setattr(
            "alembic.command.stamp", lambda cfg, rev: calls.append(("stamp", rev))
        )
        monkeypatch.setattr(
            "alembic.command.upgrade", lambda cfg, rev: calls.append(("upgrade", rev))
        )

        m.ensure_schema()

        assert calls == [("stamp", m.ADOPTION_BASELINE), ("upgrade", "head")]

    def test_tracked_database_upgrades_without_stamp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[str, str]] = []
        monkeypatch.setattr(m, "_needs_adoption", lambda: False)
        monkeypatch.setattr(
            "alembic.command.stamp", lambda cfg, rev: calls.append(("stamp", rev))
        )
        monkeypatch.setattr(
            "alembic.command.upgrade", lambda cfg, rev: calls.append(("upgrade", rev))
        )

        m.ensure_schema()

        assert calls == [("upgrade", "head")]

    def test_baseline_is_the_initial_revision(self) -> None:
        """001 created bloom_cards — the table the 2026-04 bootstrap left.

        Stamping anything newer would skip the guarded replay of 002/003
        that converges partially bootstrapped schemas.
        """
        assert m.ADOPTION_BASELINE == "001"


class TestOfflineSqlGeneration:
    """`alembic upgrade head --sql` must emit the full DDL.

    Regression for #107 (percent-encoded passwords crashed configparser
    interpolation) and proof the new existence guards skip inspection in
    offline mode instead of dying on the mock connection.
    """

    NASTY_URL = "postgresql+asyncpg://bloom:p%40ss%25word@db.internal:5432/bloom"

    def test_full_ddl_generated_with_percent_url(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from alembic import command
        from app.core.config import settings

        monkeypatch.setattr(settings, "DATABASE_URL", self.NASTY_URL)
        command.upgrade(m.alembic_config(), "head", sql=True)

        ddl = capsys.readouterr().out
        assert "CREATE TABLE bloom_cards" in ddl
        assert "CREATE INDEX IF NOT EXISTS ix_bloom_cards_embedding_hnsw" in ddl
        assert "CREATE TABLE user_interactions" in ddl
        assert "score_provenance" in ddl
        assert "UPDATE bloom_cards" in ddl

    def test_index_guards_survive_offline_generation(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from alembic import command
        from app.core.config import settings

        monkeypatch.setattr(settings, "DATABASE_URL", self.NASTY_URL)
        command.upgrade(m.alembic_config(), "head", sql=True)

        ddl = capsys.readouterr().out
        for index in (
            "ix_user_interactions_user_id",
            "ix_user_interactions_card_id",
            "ix_user_interactions_created_at",
            "ix_user_interactions_user_created",
        ):
            assert f"CREATE INDEX IF NOT EXISTS {index}" in ddl


class TestDbInitJobManifest:
    def test_job_uses_adoption_aware_entry_point(self) -> None:
        """The PreSync Job must run the adoption-aware module, not raw
        `alembic upgrade head`, or pre-alembic databases block every sync."""
        manifest = (REPO_ROOT / "infra/k8s/production/db-init-job.yaml").read_text()
        assert "python -m app.core.migrations" in manifest
        assert "alembic upgrade head" not in manifest
