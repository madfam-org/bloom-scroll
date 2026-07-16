"""
Feed pagination honesty + score provenance gating (defects D2/D5, 2026-07-16 audit).
"""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.bloom_card import BloomCard


@pytest.mark.asyncio
async def test_feed_has_next_page_false_when_no_unseen_cards(
    client: AsyncClient,
) -> None:
    """An empty corpus must not advertise a next page (old bug: it did,
    based purely on read_count arithmetic, re-serving duplicates)."""
    response = await client.get("/api/v1/feed", params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["cards"] == []
    assert body["pagination"]["has_next_page"] is False


@pytest.mark.asyncio
async def test_feed_rejects_invalid_exclude_ids(client: AsyncClient) -> None:
    """exclude_ids must be valid UUIDs."""
    response = await client.get(
        "/api/v1/feed", params={"exclude_ids": "not-a-uuid"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_feed_accepts_valid_exclude_ids(client: AsyncClient) -> None:
    """Valid exclude_ids are accepted and excluded server-side."""
    response = await client.get(
        "/api/v1/feed", params={"exclude_ids": str(uuid4())}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_livez_does_not_touch_database(client: AsyncClient) -> None:
    """/livez is process-alive only (liveness must survive DB loss)."""
    response = await client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_reports_freshness(client: AsyncClient) -> None:
    """/health carries an informational freshness check that never flips
    the overall status (stale content is a monitor alert, not an outage)."""
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "freshness" in body["checks"]
    assert body["status"] == "healthy"


class TestScoreProvenanceGating:
    """to_dict must not emit unmeasured perspective scores (defect D5)."""

    def _card(self, **overrides: object) -> BloomCard:
        defaults: dict[str, object] = {
            "id": uuid4(),
            "source_type": "OWID",
            "title": "Test card",
            "summary": "Summary",
            "original_url": "https://example.com",
            "data_payload": {},
            "bias_score": 0.42,
            "constructiveness_score": 88.0,
            "blindspot_tags": ["climate"],
            "score_provenance": None,
            "created_at": datetime(2026, 7, 16),
        }
        defaults.update(overrides)
        return BloomCard(**defaults)

    def test_unmeasured_scores_are_nulled(self) -> None:
        meta = self._card().to_dict(include_meta=True)["meta"]
        assert meta["bias_score"] is None
        assert meta["constructiveness_score"] is None
        assert meta["blindspot_tags"] == []
        assert meta["score_provenance"] is None

    def test_measured_scores_are_emitted_with_provenance(self) -> None:
        card = self._card(score_provenance="selva/test-model@1")
        meta = card.to_dict(include_meta=True)["meta"]
        assert meta["bias_score"] == 0.42
        assert meta["constructiveness_score"] == 88.0
        assert meta["blindspot_tags"] == ["climate"]
        assert meta["score_provenance"] == "selva/test-model@1"

    def test_reason_tag_still_present_without_provenance(self) -> None:
        meta = self._card().to_dict(include_meta=True, reason_tag="EXPLORE")["meta"]
        assert meta["reason_tag"] == "EXPLORE"
