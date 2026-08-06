"""
Auth gating for mutating endpoints (defect D1, 2026-07-16 audit).

Ingestion and interaction endpoints were publicly writable in production:
the Janua verifier existed but was wired to nothing. These tests pin the
contract: unauthenticated writes 401, the service API key opens the gate,
and reading another user's history is forbidden.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient

from app.core import auth as auth_module
from app.core.config import settings


@pytest.fixture(autouse=True)
def _enforce_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every test in this module with auth on and a known service key."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "INGEST_API_KEY", "test-service-key")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/ingest/owid",
        "/api/v1/ingest/owid/all",
        "/api/v1/ingest/openalex",
        "/api/v1/ingest/aesthetics",
        "/api/v1/ingest/aesthetics/all",
        "/api/v1/ingest/neocities",
        "/api/v1/ingest/narrative",
    ],
)
async def test_ingest_posts_require_auth(client: AsyncClient, path: str) -> None:
    """Unauthenticated ingestion writes are rejected."""
    response = await client.post(path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_wrong_api_key_rejected(client: AsyncClient) -> None:
    """A wrong service key does not open the gate."""
    response = await client.post(
        "/api/v1/ingest/owid", headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ingest_service_key_accepted(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The configured service key authenticates the ingestion CronJob."""
    fake_card = SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        source_type="OWID",
        title="Test",
        summary=None,
        original_url="https://example.com",
        data_payload={"chart_type": "line"},
        bias_score=None,
        constructiveness_score=None,
        blindspot_tags=None,
        score_provenance=None,
        created_at="2026-07-16T00:00:00",
    )

    async def fake_ingest(self: Any, db: Any, *args: Any, **kwargs: Any) -> Any:
        return fake_card

    from app.ingestion.owid import OWIDConnector

    monkeypatch.setattr(OWIDConnector, "ingest_to_database", fake_ingest)

    response = await client.post(
        "/api/v1/ingest/owid", headers={"X-API-Key": "test-service-key"}
    )
    assert response.status_code == 200
    assert response.json()["source_type"] == "OWID"


@pytest.mark.asyncio
async def test_ingest_get_catalogs_stay_public(client: AsyncClient) -> None:
    """Read-only catalog endpoints remain unauthenticated."""
    for path in (
        "/api/v1/ingest/datasets",
        "/api/v1/ingest/openalex/topics",
        "/api/v1/ingest/aesthetics/channels",
    ):
        response = await client.get(path)
        assert response.status_code == 200, path


@pytest.mark.asyncio
async def test_track_interaction_requires_auth(client: AsyncClient) -> None:
    """Interaction writes are rejected without credentials."""
    response = await client.post(
        "/api/v1/interactions/track",
        json={"user_id": "u1", "card_id": "c1", "action": "read"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_recent_interactions_forbidden_for_other_users(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user token cannot read another user's reading history."""

    async def fake_user(
        credentials: Any = None, x_api_key: Any = None
    ) -> auth_module.User:
        return auth_module.User(id="user-a", email="a@example.com", roles=["user"])

    from app.main import app

    app.dependency_overrides[auth_module.require_write_access] = fake_user
    try:
        response = await client.get("/api/v1/interactions/recent/user-b")
        assert response.status_code == 403

        response = await client.get("/api/v1/interactions/recent/user-a")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(auth_module.require_write_access, None)


@pytest.mark.asyncio
async def test_recent_interactions_service_key_allowed(client: AsyncClient) -> None:
    """The service identity may read any user's history (feed context)."""
    response = await client.get(
        "/api/v1/interactions/recent/anyone",
        headers={"X-API-Key": "test-service-key"},
    )
    assert response.status_code == 200
