"""Narrative-trope connector (PRD §3.1, NARRATIVE cards).

The PRD names TVTropes via the "All The Tropes" MediaWiki mirror, but
allthetropes.org sits behind Miraheze's JS bot challenge (verified blocked
2026-07-16 from datacenter egress, which is what the production cluster
uses). Tropedia (tropedia.fandom.com) exposes the same trope corpus through
Fandom's standard MediaWiki API without a challenge — verified working
2026-07-16 — so that is the mirror used here.
"""

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.analysis.scoring import get_scoring_service
from app.ingestion.common import get_card_for_url
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)

USER_AGENT = "BloomScroll/0.1 (almanac.solar content aggregator)"


class NarrativeConnector:
    """Fetches narrative-device articles from Tropedia's MediaWiki API."""

    API_URL = "https://tropedia.fandom.com/api.php"

    # Minimum plain-text length for a page to count as substantive.
    MIN_SUMMARY_CHARS = 200

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def fetch_random_tropes(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Fetch random substantive trope pages.

        Uses generator=random (fresh pages every run — a paged category
        walk would return the same head pages daily), overfetching 3x and
        filtering out subpages (titles with '/') and stub pages. The
        MediaWiki TextExtracts prop returns empty for most Tropedia pages
        (verified 2026-07-16), so page text comes from action=parse HTML
        stripped with BeautifulSoup.
        """
        headers = {"User-Agent": USER_AGENT}
        tropes: list[dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers=headers, follow_redirects=True
            ) as client:
                response = await client.get(
                    self.API_URL,
                    params={
                        "action": "query",
                        "generator": "random",
                        "grnnamespace": 0,
                        "grnlimit": min(limit * 3, 20),
                        "prop": "info",
                        "inprop": "url",
                        "format": "json",
                    },
                )
                response.raise_for_status()
                pages = response.json().get("query", {}).get("pages", {})

                for page in pages.values():
                    if len(tropes) >= limit:
                        break
                    title = page.get("title", "")
                    if not title or "/" in title:
                        continue
                    summary = await self._fetch_page_summary(client, title)
                    if not summary:
                        continue
                    tropes.append(
                        {
                            "title": title,
                            "summary": summary,
                            "url": page.get("fullurl")
                            or f"https://tropedia.fandom.com/wiki/{title.replace(' ', '_')}",
                        }
                    )
        except httpx.HTTPError as e:
            logger.error(f"Tropedia fetch failed: {e}")
            return []

        return tropes

    async def _fetch_page_summary(
        self, client: httpx.AsyncClient, title: str
    ) -> str | None:
        """Parse a page and return its first substantive paragraph."""
        try:
            response = await client.get(
                self.API_URL,
                params={
                    "action": "parse",
                    "page": title,
                    "prop": "text",
                    "format": "json",
                    "disablelimitreport": 1,
                },
            )
            response.raise_for_status()
            html = response.json().get("parse", {}).get("text", {}).get("*", "")
        except Exception as e:
            logger.debug(f"Tropedia parse failed for {title}: {e}")
            return None

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.select("table, .quote, dl, .toc, .noprint, figure, aside"):
            tag.decompose()
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) >= 80
        ]
        text = " ".join(paragraphs)
        if len(text) < self.MIN_SUMMARY_CHARS:
            return None
        return text[:600].rsplit(" ", 1)[0] + "…" if len(text) > 600 else text

    async def ingest_to_database(
        self, session: AsyncSession, limit: int = 5
    ) -> list[BloomCard]:
        """Ingest random narrative-trope articles as NARRATIVE cards."""
        tropes = await self.fetch_random_tropes(limit)
        cards: list[BloomCard] = []
        nlp = get_nlp_processor()

        for trope in tropes:
            existing = await get_card_for_url(session, trope["url"])
            if existing is not None:
                logger.debug(f"Narrative card already exists: {trope['url']}")
                cards.append(existing)
                continue

            card = BloomCard(
                source_type="NARRATIVE",
                title=trope["title"],
                summary=trope["summary"],
                original_url=trope["url"],
                data_payload={"category": "narrative_trope", "source": "tropedia"},
                embedding=nlp.generate_embedding(
                    f"{trope['title']}. {trope['summary']}"
                ),
            )
            await get_scoring_service().apply_scores(card)
            session.add(card)
            cards.append(card)

        if cards:
            await session.flush()
        logger.info(f"Narrative ingestion produced {len(cards)} cards")
        return cards
