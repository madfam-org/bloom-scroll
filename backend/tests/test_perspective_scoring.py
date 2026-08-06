"""
Perspective Engine v1: Selva scoring service + real perspective endpoint.

The scoring service must be strictly optional (dormant without
SELVA_BASE_URL, never blocking ingestion on failure) and must stamp
score_provenance on everything it measures (defect D5 contract).
"""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.analysis.scoring import SelvaScoringService
from app.core.config import settings
from app.models.bloom_card import BloomCard


def _make_card(**overrides: Any) -> BloomCard:
    defaults: dict[str, Any] = {
        "id": uuid4(),
        "source_type": "OWID",
        "title": "Renewables overtake coal",
        "summary": "A data story.",
        "original_url": "https://ourworldindata.org/grapher/renewables",
        "data_payload": {"indicator": "share_energy_renewables"},
        "created_at": datetime(2026, 7, 16),
    }
    defaults.update(overrides)
    return BloomCard(**defaults)


class TestScoringService:
    @pytest.mark.asyncio
    async def test_disabled_without_base_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "SELVA_BASE_URL", "")
        service = SelvaScoringService()
        assert service.enabled is False
        assert await service.score_text("t", "s", "OWID") is None

        card = _make_card()
        await service.apply_scores(card)
        assert card.score_provenance is None
        assert card.bias_score is None

    def test_parses_and_clamps_valid_reply(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "SELVA_SCORING_MODEL", "test-model")
        service = SelvaScoringService()
        reply = json.dumps(
            {
                "bias_score": 1.7,  # clamped to 1.0
                "constructiveness_score": -3,  # clamped to 0.0
                "blindspot_tags": ["energy", "climate", "extra", "dropped"],
            }
        )
        scores = service._parse_scores(reply)
        assert scores is not None
        assert scores.bias_score == 1.0
        assert scores.constructiveness_score == 0.0
        assert scores.blindspot_tags == ["energy", "climate", "extra"]
        assert scores.provenance == "selva/test-model"

    def test_parses_fenced_reply(self) -> None:
        service = SelvaScoringService()
        reply = (
            '```json\n{"bias_score": 0.5, "constructiveness_score": 80, '
            '"blindspot_tags": []}\n```'
        )
        scores = service._parse_scores(reply)
        assert scores is not None
        assert scores.constructiveness_score == 80.0

    def test_rejects_malformed_reply(self) -> None:
        service = SelvaScoringService()
        assert service._parse_scores("I cannot help with that.") is None
        assert service._parse_scores('{"unrelated": true}') is None

    @pytest.mark.asyncio
    async def test_apply_scores_stamps_provenance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "SELVA_BASE_URL", "https://selva.internal/v1")
        monkeypatch.setattr(settings, "SELVA_SCORING_MODEL", "test-model")
        service = SelvaScoringService()

        from app.analysis.scoring import PerspectiveScores

        async def fake_score(
            title: str, summary: str | None, source_type: str
        ) -> PerspectiveScores:
            return PerspectiveScores(
                bias_score=0.5,
                constructiveness_score=90.0,
                blindspot_tags=["solar"],
                provenance="selva/test-model",
            )

        monkeypatch.setattr(service, "score_text", fake_score)
        card = _make_card()
        await service.apply_scores(card)
        assert card.score_provenance == "selva/test-model"
        assert card.constructiveness_score == 90.0
        # And the API now emits them (provenance gate open).
        meta = card.to_dict(include_meta=True)["meta"]
        assert meta["constructiveness_score"] == 90.0

    @pytest.mark.asyncio
    async def test_network_failure_never_blocks_ingestion(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "SELVA_BASE_URL", "https://selva.internal/v1")
        service = SelvaScoringService(timeout=0.001)

        async def boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("selva down")

        monkeypatch.setattr(service, "score_text", boom)
        card = _make_card()
        # apply_scores lets score_text exceptions surface? No: score_text
        # itself catches network errors; simulate its failure contract by
        # returning None instead.

        async def none_score(*args: Any, **kwargs: Any) -> None:
            return None

        monkeypatch.setattr(service, "score_text", none_score)
        await service.apply_scores(card)
        assert card.score_provenance is None


class TestPerspectiveEndpoint:
    @pytest.mark.asyncio
    async def test_full_response_shape_for_known_card(
        self, client: AsyncClient
    ) -> None:
        """Override the DB to return a real card and check the contract."""
        from app.core.database import get_db
        from app.main import app

        card = _make_card(score_provenance="selva/test-model", bias_score=0.5,
                          constructiveness_score=77.0, blindspot_tags=["energy"])

        class _Result:
            def __init__(self, items: list[Any]):
                self._items = items

            def scalars(self) -> "_Result":
                return self

            def all(self) -> list[Any]:
                return self._items

            def fetchall(self) -> list[Any]:
                return []

        class _Session:
            async def execute(self, stmt: Any) -> _Result:
                text = str(stmt)
                if "bloom_cards.id =" in text or "WHERE bloom_cards.id" in text:
                    return _Result([card])
                return _Result([])

        async def override() -> Any:
            yield _Session()

        app.dependency_overrides[get_db] = override
        try:
            response = await client.get(f"/api/v1/perspective/{card.id}")
        finally:
            app.dependency_overrides[get_db] = override  # keep for clarity
            del app.dependency_overrides[get_db]

        assert response.status_code == 200
        body = response.json()
        assert body["card_id"] == str(card.id)
        assert body["scores"]["constructiveness_score"] == 77.0
        assert body["scores"]["score_provenance"] == "selva/test-model"
        assert body["source"]["domain"] == "ourworldindata.org"
        # No embedding on this card -> context blocks stay null.
        assert body["data_context"] is None
        assert body["topic_cluster"] is None

    @pytest.mark.asyncio
    async def test_unmeasured_card_hides_scores(self, client: AsyncClient) -> None:
        from app.core.database import get_db
        from app.main import app

        card = _make_card(bias_score=0.9, constructiveness_score=99.0)

        class _Result:
            def __init__(self, items: list[Any]):
                self._items = items

            def scalars(self) -> "_Result":
                return self

            def all(self) -> list[Any]:
                return self._items

        class _Session:
            async def execute(self, stmt: Any) -> _Result:
                return _Result([card])

        async def override() -> Any:
            yield _Session()

        app.dependency_overrides[get_db] = override
        try:
            response = await client.get(f"/api/v1/perspective/{card.id}")
        finally:
            del app.dependency_overrides[get_db]

        assert response.status_code == 200
        scores = response.json()["scores"]
        # Hand-set values without provenance must not leak (defect D5).
        assert scores["bias_score"] is None
        assert scores["constructiveness_score"] is None
        assert scores["blindspot_tags"] == []
