"""OpenAlex ingestion normalization tests."""

import pytest
from httpx import AsyncClient

from app.ingestion.openalex import OpenAlexConnector


def test_openalex_normalize_work_reconstructs_abstract() -> None:
    connector = OpenAlexConnector()
    normalized = connector.normalize_work(
        {
            "id": "https://openalex.org/W123",
            "display_name": "Solar microgrids improve rural resilience",
            "publication_year": 2026,
            "cited_by_count": 42,
            "doi": "https://doi.org/10.1234/example",
            "abstract_inverted_index": {
                "Solar": [0],
                "microgrids": [1],
                "improve": [2],
                "resilience": [4],
                "rural": [3],
            },
            "authorships": [
                {"author": {"display_name": "Ada Lovelace"}},
                {"author": {"display_name": "Grace Hopper"}},
            ],
            "open_access": {"oa_url": "https://example.org/paper.pdf"},
            "primary_location": {
                "landing_page_url": "https://example.org/paper",
                "source": {"display_name": "Journal of Useful Systems"},
            },
            "concepts": [{"display_name": "Renewable energy"}],
        }
    )

    assert normalized is not None
    assert normalized["title"] == "Solar microgrids improve rural resilience"
    assert normalized["summary"] == "Solar microgrids improve rural resilience"
    assert normalized["original_url"] == "https://example.org/paper"
    assert normalized["data_payload"]["authors"] == ["Ada Lovelace", "Grace Hopper"]
    assert normalized["data_payload"]["pdf_url"] == "https://example.org/paper.pdf"
    assert normalized["data_payload"]["source"] == "Journal of Useful Systems"
    assert normalized["data_payload"]["concepts"] == ["Renewable energy"]


def test_openalex_normalize_work_rejects_missing_title() -> None:
    connector = OpenAlexConnector()

    assert connector.normalize_work({"id": "https://openalex.org/W123"}) is None


@pytest.mark.asyncio
async def test_openalex_topics_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ingest/openalex/topics")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert "renewable_energy" in data["topics"]
