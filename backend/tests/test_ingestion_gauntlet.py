"""Poison pill tests - ensure graceful degradation with malformed data."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis.processor import NLPProcessor
from app.ingestion.aesthetics import AestheticsConnector
from app.ingestion.owid import OWIDConnector
from app.models.bloom_card import BloomCard
from app.schemas.bloom_card import BloomCardCreate

POISON_PILLS_DIR = Path(__file__).parent / "fixtures" / "poison_pills"


class TestOWIDIngestionGauntlet:
    """Test OWID connector resilience."""

    def test_malformed_csv_graceful_failure(self):
        """Malformed rows should be skipped while valid numeric rows survive."""
        connector = OWIDConnector()
        payload = connector.parse_csv(POISON_PILLS_DIR / "malformed_owid.csv")

        assert payload is not None
        assert payload["years"] == [2020, 2024]
        assert payload["values"][0] == 10.5
        assert payload["values"][1] == pytest.approx(1e18)
        assert payload["entity"] == "World"

    def test_missing_required_fields_rejected_by_schema(self):
        """API creation schema rejects empty required fields."""
        with pytest.raises(ValidationError):
            BloomCardCreate(
                source_type="OWID",
                title="",
                original_url="https://example.com",
                data_payload={},
            )

    def test_model_tolerates_extreme_values(self):
        """SQLAlchemy model construction should not crash on extreme payload values."""
        card = BloomCard(
            source_type="OWID",
            title="Test",
            original_url="https://example.com",
            data_payload={"values": [1e308, -1e308, 0, 1e-308]},
        )

        assert card.data_payload["values"][0] == 1e308


class TestAestheticIngestionGauntlet:
    """Test aesthetic connector resilience."""

    @pytest.mark.asyncio
    async def test_invalid_image_url_falls_back_to_square_ratio(self):
        """Invalid image URLs should return a safe aspect-ratio fallback."""
        connector = AestheticsConnector(timeout=1)

        assert await connector.calculate_aspect_ratio("not-a-url") == 1.0

    def test_invalid_image_bytes_fall_back_to_gray(self):
        """Invalid image data should return a safe placeholder color."""
        connector = AestheticsConnector()

        assert connector.extract_dominant_color(b"not-an-image") == "#808080"

    def test_null_metadata_payload_is_still_storable(self):
        """Malformed source metadata should not prevent storing the raw payload."""
        card = BloomCard(
            source_type="AESTHETIC",
            title="Test",
            original_url="https://example.com",
            data_payload={
                "image_url": "https://example.com/image.jpg",
                "aspect_ratio": None,
                "dominant_color": None,
                "vibe_tags": None,
            },
        )

        assert card.data_payload["aspect_ratio"] is None


class TestVectorEmbeddingGauntlet:
    """Test vector embedding resilience."""

    def test_empty_text_embedding_returns_zero_vector(self):
        """Empty text should not load the model or raise."""
        nlp = NLPProcessor()

        embedding = nlp.generate_embedding("")

        assert embedding == [0.0] * 384

    def test_embedding_failure_returns_zero_vector(self, monkeypatch):
        """Model load/generation failures should degrade to a zero vector."""
        nlp = NLPProcessor()

        def fail_load():
            raise RuntimeError("model unavailable")

        monkeypatch.setattr(nlp, "_load_embedding_model", fail_load)

        embedding = nlp.generate_embedding("word " * 10000)

        assert embedding == [0.0] * 384


class TestAPIErrorHandling:
    """Test API endpoint validation paths that do not require a real database."""

    @pytest.mark.asyncio
    async def test_feed_with_invalid_context(self, client):
        """Invalid user_context UUIDs should be rejected before DB work."""
        response = await client.get(
            "/api/v1/feed",
            params={"user_context": ["invalid-uuid", "not-a-uuid"]},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_feed_with_negative_limit(self, client):
        """Negative limits should fail FastAPI validation."""
        response = await client.get("/api/v1/feed", params={"limit": -10})

        assert response.status_code == 422
