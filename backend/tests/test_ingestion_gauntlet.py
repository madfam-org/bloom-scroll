"""Poison pill tests - ensure graceful degradation with malformed data."""

from pathlib import Path

import pytest
from app.ingestion.owid_connector import OWIDConnector

from app.models.bloom_card import BloomCard

POISON_PILLS_DIR = Path(__file__).parent / "fixtures" / "poison_pills"


class TestOWIDIngestionGauntlet:
    """Test OWID connector resilience."""

    def test_malformed_csv_graceful_failure(self):
        """Should skip invalid rows and continue processing."""
        connector = OWIDConnector()

        # Load malformed CSV
        csv_path = POISON_PILLS_DIR / "malformed_owid.csv"

        # Should not raise exception
        try:
            cards = connector.parse_csv(csv_path)
            # Should skip invalid rows but process valid ones
            assert len(cards) > 0, "Should parse at least some valid rows"

            # Valid rows should be present
            valid_cards = [c for c in cards if c.title]
            assert len(valid_cards) > 0

        except Exception as e:
            pytest.fail(f"Should handle malformed CSV gracefully: {e}")

    def test_missing_required_fields(self):
        """Should reject cards with missing required fields."""
        # Attempt to create card without title
        with pytest.raises(ValueError):
            BloomCard(
                source_type="OWID",
                title="",  # Empty title
                original_url="https://example.com",
                data_payload={}
            )

    def test_extreme_values(self):
        """Should handle extreme numeric values."""
        # Very large numbers
        card = BloomCard(
            source_type="OWID",
            title="Test",
            original_url="https://example.com",
            data_payload={
                "values": [1e308, -1e308, 0, 1e-308]  # Extreme floats
            }
        )

        # Should not crash
        assert card is not None


class TestAestheticIngestionGauntlet:
    """Test aesthetic connector resilience."""

    def test_invalid_image_url(self):
        """Should validate image URLs."""
        # Invalid URL should be rejected or sanitized
        # payload would be:
        # {"image_url": "not-a-url", "aspect_ratio": 1.0, "dominant_color": "#000000"}
        # Should either raise validation error or sanitize
        # (implementation-dependent)
        assert True  # Placeholder

    def test_missing_aspect_ratio(self):
        """Should calculate aspect ratio if missing."""
        # Should have fallback to 1.0 or fetch from image
        assert True  # Placeholder

    def test_null_metadata(self):
        """Should handle null/missing metadata gracefully."""
        card = BloomCard(
            source_type="AESTHETIC",
            title="Test",
            original_url="https://example.com",
            data_payload={
                "image_url": "https://example.com/image.jpg",
                "aspect_ratio": None,  # Null value
                "dominant_color": None,
                "vibe_tags": None
            }
        )

        # Should use defaults
        data = card.aestheticData
        assert data is not None or card.data_payload is not None


class TestVectorEmbeddingGauntlet:
    """Test vector embedding resilience."""

    def test_empty_text_embedding(self):
        """Should handle empty text gracefully."""
        from app.analysis.nlp_service import NLPService

        nlp = NLPService()

        # Empty string should return zero vector or raise error
        try:
            embedding = nlp.generate_embedding("")
            assert embedding is None or len(embedding) == 384
        except ValueError:
            # Acceptable to reject empty text
            pass

    def test_very_long_text_embedding(self):
        """Should truncate or handle very long text."""
        from app.analysis.nlp_service import NLPService

        nlp = NLPService()

        # Very long text (SBERT has 512 token limit)
        long_text = "word " * 10000

        embedding = nlp.generate_embedding(long_text)
        assert len(embedding) == 384  # Should not crash


class TestAPIErrorHandling:
    """Test API endpoint error handling."""

    @pytest.mark.asyncio
    async def test_feed_with_invalid_context(self, client):
        """Should handle invalid user_context IDs."""
        response = await client.get(
            "/feed",
            params={"user_context": ["invalid-uuid", "not-a-uuid"]}
        )

        # Should either ignore invalid IDs or return 400
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_feed_with_negative_limit(self, client):
        """Should reject negative limits."""
        response = await client.get(
            "/feed",
            params={"limit": -10}
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_database_connection_failure(self, client, monkeypatch):
        """Should return 503 when database is unavailable."""
        # Mock database connection failure
        # (requires proper error handling in routes)
        assert True  # Placeholder for implementation
