"""OpenAlex connector for scholarly works."""

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.analysis.scoring import get_scoring_service
from app.core.config import settings
from app.ingestion.common import get_card_for_url
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)


class OpenAlexConnector:
    """
    Connector for fetching frontier science works from OpenAlex.

    OpenAlex exposes paper metadata and abstracts as structured JSON. This
    connector keeps the raw provenance identifiers in the card payload so the
    frontend can show work-level source context without treating papers as
    opaque article summaries.
    """

    OPENALEX_API_BASE = "https://api.openalex.org"

    TOPICS = {
        "renewable_energy": "renewable energy",
        "public_health": "public health",
        "climate_adaptation": "climate adaptation",
        "materials_science": "materials science",
        "sustainable_agriculture": "sustainable agriculture",
    }

    def __init__(self, timeout: int = 30):
        """Initialize the connector."""
        self.timeout = timeout

    async def fetch_works(
        self,
        topic_key: str = "renewable_energy",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Fetch highly cited OpenAlex works for a configured topic.

        Args:
            topic_key: Key from TOPICS.
            limit: Number of works to fetch.

        Returns:
            List of raw OpenAlex work dictionaries.
        """
        if topic_key not in self.TOPICS:
            logger.error(f"Unknown OpenAlex topic: {topic_key}")
            return []

        params: dict[str, str | int] = {
            "search": self.TOPICS[topic_key],
            "sort": "cited_by_count:desc",
            "per-page": max(1, min(limit, 25)),
        }
        if settings.OPENALEX_EMAIL:
            params["mailto"] = settings.OPENALEX_EMAIL

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.OPENALEX_API_BASE}/works", params=params)
                response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not isinstance(results, list):
                return []
            return [work for work in results if isinstance(work, dict)]
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching OpenAlex works: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing OpenAlex works: {e}")
            return []

    def _abstract_from_inverted_index(self, value: Any) -> str:
        """Convert OpenAlex abstract_inverted_index into readable text."""
        if not isinstance(value, dict):
            return ""

        positioned_words: list[tuple[int, str]] = []
        for word, positions in value.items():
            if not isinstance(word, str) or not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int):
                    positioned_words.append((position, word))

        positioned_words.sort(key=lambda item: item[0])
        return " ".join(word for _, word in positioned_words)

    def normalize_work(self, work: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize a raw OpenAlex work into BloomCard fields."""
        title = work.get("display_name") or work.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        authors = []
        for authorship in work.get("authorships", []):
            if not isinstance(authorship, dict):
                continue
            author = authorship.get("author", {})
            if isinstance(author, dict) and isinstance(author.get("display_name"), str):
                authors.append(author["display_name"])

        abstract = self._abstract_from_inverted_index(work.get("abstract_inverted_index"))
        open_access = work.get("open_access", {})
        primary_location = work.get("primary_location", {})
        source = primary_location.get("source", {}) if isinstance(primary_location, dict) else {}

        oa_url = ""
        if isinstance(open_access, dict):
            oa_url = str(open_access.get("oa_url") or "")
        landing_page_url = ""
        if isinstance(primary_location, dict):
            landing_page_url = str(primary_location.get("landing_page_url") or "")

        concepts = []
        for concept in work.get("concepts", []):
            if isinstance(concept, dict) and isinstance(concept.get("display_name"), str):
                concepts.append(concept["display_name"])

        publication_year = work.get("publication_year")
        cited_by_count = work.get("cited_by_count") or 0
        work_id = str(work.get("id") or "")

        summary = abstract[:280].strip()
        if len(abstract) > 280:
            summary += "..."
        if not summary:
            year_text = f" ({publication_year})" if publication_year else ""
            summary = f"Scholarly work from OpenAlex{year_text}."

        return {
            "title": title.strip(),
            "summary": summary,
            "original_url": landing_page_url or work_id,
            "data_payload": {
                "abstract": abstract,
                "authors": authors,
                "publication_year": publication_year,
                "doi": work.get("doi"),
                "openalex_id": work_id,
                "cited_by_count": cited_by_count,
                "pdf_url": oa_url,
                "source": source.get("display_name") if isinstance(source, dict) else None,
                "concepts": concepts[:8],
            },
        }

    async def ingest_to_database(
        self,
        session: AsyncSession,
        topic_key: str = "renewable_energy",
        limit: int = 5,
    ) -> list[BloomCard]:
        """
        Fetch OpenAlex works and insert them into the database.

        Args:
            session: Database session.
            topic_key: Topic key from TOPICS.
            limit: Number of works to fetch.

        Returns:
            Created BloomCard instances.
        """
        works = await self.fetch_works(topic_key=topic_key, limit=limit)
        cards: list[BloomCard] = []

        for work in works:
            normalized = self.normalize_work(work)
            if not normalized:
                continue

            try:
                embedding_text = f"{normalized['title']}. {normalized['summary']}"
                embedding = get_nlp_processor().generate_embedding(embedding_text)
                existing = await get_card_for_url(session, normalized["original_url"])
                if existing is not None:
                    logger.debug(
                        f"OpenAlex card already exists: {normalized['original_url']}"
                    )
                    cards.append(existing)
                    continue

                card = BloomCard(
                    source_type="OPENALEX",
                    title=normalized["title"],
                    summary=normalized["summary"],
                    original_url=normalized["original_url"],
                    data_payload=normalized["data_payload"],
                    embedding=embedding,
                )
                await get_scoring_service().apply_scores(card)
                session.add(card)
                await session.flush()
                await session.refresh(card)
                cards.append(card)
            except Exception as e:
                logger.error(f"Error creating OpenAlex card: {e}")
                continue

        logger.info(f"Ingested {len(cards)} OpenAlex cards for topic {topic_key}")
        return cards
