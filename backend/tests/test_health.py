"""
Health endpoint tests for Bloom Scroll API.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test that health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "ok"]


@pytest.mark.asyncio
async def test_health_includes_version(client: AsyncClient):
    """Test that health endpoint includes version info."""
    response = await client.get("/health")
    data = response.json()

    # Version should be included
    assert "version" in data or "api_version" in data
