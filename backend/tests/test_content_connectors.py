"""
Phase 3 content breadth: Robin Hood interleave + new connectors.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from app.curation.bloom_algorithm import BloomAlgorithm
from app.ingestion.narrative import NarrativeConnector
from app.ingestion.neocities import NeocitiesConnector
from app.models.bloom_card import BloomCard


def _card(source_type: str, title: str = "t") -> BloomCard:
    return BloomCard(
        id=uuid4(),
        source_type=source_type,
        title=title,
        summary="s",
        original_url=f"https://example.com/{uuid4()}",
        data_payload={},
        created_at=datetime(2026, 7, 16),
    )


class TestRobinHoodInterleave:
    def test_no_adjacent_same_source_when_feasible(self) -> None:
        cards = [
            _card("OWID"), _card("OWID"), _card("OWID"),
            _card("AESTHETIC"), _card("AESTHETIC"),
            _card("OPENALEX"),
        ]
        result = BloomAlgorithm.interleave_sources(cards)
        assert len(result) == len(cards)
        assert {c.id for c in result} == {c.id for c in cards}
        adjacent_same = sum(
            1
            for a, b in zip(result, result[1:])
            if a.source_type == b.source_type
        )
        # 3 OWID / 2 AESTHETIC / 1 OPENALEX is fully interleavable.
        assert adjacent_same == 0

    def test_single_source_passes_through(self) -> None:
        cards = [_card("OWID") for _ in range(5)]
        result = BloomAlgorithm.interleave_sources(cards)
        assert [c.id for c in result] == [c.id for c in cards]

    def test_short_lists_untouched(self) -> None:
        cards = [_card("OWID"), _card("AESTHETIC")]
        assert BloomAlgorithm.interleave_sources(cards) == cards


class _FakeResult:
    def __init__(self, items: list[Any] | None = None):
        self._items = items or []

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> list[Any]:
        return self._items


class _FakeSession:
    """Session double supporting the connector write path."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    async def execute(self, stmt: Any) -> _FakeResult:
        return _FakeResult([])  # no existing cards

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        pass


class TestNeocitiesConnector:
    @pytest.mark.asyncio
    async def test_ingest_builds_indie_web_cards(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = NeocitiesConnector()

        async def fake_sites(limit: int) -> list[dict[str, Any]]:
            return [
                {
                    "sitename": "fauux",
                    "tags": ["art", "lain"],
                    "last_updated": "Wed, 10 Dec 2025 21:09:52 -0000",
                    "views": 58711061,
                }
            ]

        monkeypatch.setattr(connector, "fetch_recent_sites", fake_sites)
        session = _FakeSession()
        cards = await connector.ingest_to_database(session, limit=1)  # type: ignore[arg-type]

        assert len(cards) == 1
        card = cards[0]
        assert card.source_type == "INDIE_WEB"
        assert card.original_url == "https://fauux.neocities.org"
        assert card.data_payload["tags"] == ["art", "lain"]
        assert card.embedding is not None
        assert session.added == [card]

    @pytest.mark.asyncio
    async def test_fetch_failure_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = NeocitiesConnector(timeout=1)

        async def fake_sites(limit: int) -> list[dict[str, Any]]:
            return []

        monkeypatch.setattr(connector, "fetch_recent_sites", fake_sites)
        cards = await connector.ingest_to_database(_FakeSession(), limit=3)  # type: ignore[arg-type]
        assert cards == []


class TestNarrativeConnector:
    @pytest.mark.asyncio
    async def test_ingest_builds_narrative_cards(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        connector = NarrativeConnector()

        async def fake_tropes(limit: int) -> list[dict[str, Any]]:
            return [
                {
                    "title": "Chekhov's Gun",
                    "summary": "A dramatic principle: every element must be necessary." * 3,
                    "url": "https://tropedia.fandom.com/wiki/Chekhov's_Gun",
                }
            ]

        monkeypatch.setattr(connector, "fetch_random_tropes", fake_tropes)
        session = _FakeSession()
        cards = await connector.ingest_to_database(session, limit=1)  # type: ignore[arg-type]

        assert len(cards) == 1
        assert cards[0].source_type == "NARRATIVE"
        assert cards[0].data_payload["category"] == "narrative_trope"

    @pytest.mark.asyncio
    async def test_summary_extraction_filters_stubs(self) -> None:
        connector = NarrativeConnector()
        html = "<p>short</p><p>" + "A substantive paragraph about narrative devices. " * 6 + "</p>"

        class _Response:
            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict[str, Any]:
                return {"parse": {"text": {"*": html}}}

        class _Client:
            async def get(self, *args: Any, **kwargs: Any) -> _Response:
                return _Response()

        summary = await connector._fetch_page_summary(_Client(), "Test")  # type: ignore[arg-type]
        assert summary is not None
        assert "substantive paragraph" in summary
