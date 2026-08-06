"""Feed endpoint tests for the current `/api/v1/feed` API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_feed_completion_when_daily_limit_reached(client: AsyncClient) -> None:
    """The finite feed should return completion once read_count reaches 20."""
    response = await client.get("/api/v1/feed", params={"read_count": 20})

    assert response.status_code == 200
    data = response.json()
    assert data["cards"] == []
    assert data["pagination"]["has_next_page"] is False
    assert data["pagination"]["daily_limit"] == 20
    assert data["completion"]["message"] == "The Garden is Watered."


@pytest.mark.asyncio
async def test_feed_clamps_limit_to_remaining_daily_cards(client: AsyncClient) -> None:
    """The API should not return pagination metadata beyond the daily cap."""
    response = await client.get(
        "/api/v1/feed",
        params={"read_count": 19, "limit": 20},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["limit"] == 1
    assert data["pagination"]["daily_limit"] == 20


@pytest.mark.asyncio
async def test_feed_rejects_negative_limit(client: AsyncClient) -> None:
    """FastAPI validation should reject invalid limits."""
    response = await client.get("/api/v1/feed", params={"limit": -1})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feed_rejects_invalid_user_context_uuid(client: AsyncClient) -> None:
    """Invalid UUIDs should be rejected before feed generation."""
    response = await client.get(
        "/api/v1/feed",
        params={"user_context": ["not-a-uuid"]},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_perspective_endpoint_rejects_non_uuid(client: AsyncClient) -> None:
    """The perspective endpoint validates card_id as UUID."""
    response = await client.get("/api/v1/perspective/test-card")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_perspective_endpoint_404_for_unknown_card(client: AsyncClient) -> None:
    """An unknown card id yields 404 (real endpoint since 2026-07-16)."""
    response = await client.get(
        "/api/v1/perspective/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
