"""Application configuration behavior tests."""

import pytest

from app.main import _is_production_env


def test_production_env_detects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV=production should enable production behavior."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("PYTHON_ENV", raising=False)
    monkeypatch.setenv("ENV", "production")

    assert _is_production_env() is True


def test_production_env_detects_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENVIRONMENT=production should also enable production behavior."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("PYTHON_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    assert _is_production_env() is True


def test_development_env_keeps_docs_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development-like env values should not be treated as production."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("PYTHON_ENV", "development")

    assert _is_production_env() is False
