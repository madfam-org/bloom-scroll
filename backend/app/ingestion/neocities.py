"""Neocities connector for indie-web site discovery (PRD §3.1, INDIE_WEB)."""

import logging
import re
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.analysis.scoring import get_scoring_service
from app.ingestion.common import get_card_for_url
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)

USER_AGENT = "BloomScroll/0.1 (almanac.solar content aggregator)"


class NeocitiesConnector:
    """
    Surfaces recently-updated, human-made Neocities sites.

    Discovery parses the public browse page (Neocities has no browse API);
    per-site metadata comes from the official ``/api/info`` endpoint.
    Both verified working on 2026-07-16.
    """

    BROWSE_URL = "https://neocities.org/browse"
    INFO_URL = "https://neocities.org/api/info"

    # Sites with fewer than this many tags tend to be empty shells.
    MIN_TAGS = 1

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def fetch_recent_sites(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Discover recently-updated sites and fetch their metadata.

        Returns a list of {sitename, tags, last_updated, views} dicts.
        Failures on individual sites are skipped, not fatal.
        """
        headers = {"User-Agent": USER_AGENT}
        sites: list[dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers=headers, follow_redirects=True
            ) as client:
                response = await client.get(
                    self.BROWSE_URL, params={"sort_by": "last_updated"}
                )
                response.raise_for_status()
                # Site tiles link to /site/{name}; dedupe preserving order.
                names = list(dict.fromkeys(re.findall(r'href="/site/([\w-]+)"', response.text)))

                for name in names:
                    if len(sites) >= limit:
                        break
                    try:
                        info_response = await client.get(
                            self.INFO_URL, params={"sitename": name}
                        )
                        info_response.raise_for_status()
                        info = info_response.json().get("info", {})
                    except Exception as e:
                        logger.debug(f"Neocities info failed for {name}: {e}")
                        continue

                    tags = info.get("tags") or []
                    if len(tags) < self.MIN_TAGS:
                        continue
                    sites.append(
                        {
                            "sitename": name,
                            "tags": tags,
                            "last_updated": info.get("last_updated"),
                            "views": info.get("views"),
                        }
                    )
        except httpx.HTTPError as e:
            logger.error(f"Neocities browse fetch failed: {e}")
            return []

        return sites

    async def ingest_to_database(
        self, session: AsyncSession, limit: int = 10
    ) -> list[BloomCard]:
        """Ingest recently-updated Neocities sites as INDIE_WEB cards."""
        sites = await self.fetch_recent_sites(limit)
        cards: list[BloomCard] = []
        nlp = get_nlp_processor()

        for site in sites:
            name = site["sitename"]
            original_url = f"https://{name}.neocities.org"

            existing = await get_card_for_url(session, original_url)
            if existing is not None:
                logger.debug(f"Neocities card already exists: {original_url}")
                cards.append(existing)
                continue

            tags = ", ".join(str(tag) for tag in site["tags"][:5])
            title = f"{name} — a hand-made corner of the web"
            summary = (
                f"A recently-updated personal site on Neocities"
                f"{f', tagged {tags}' if tags else ''}. "
                "Human-curated, no algorithm, no feed."
            )
            card = BloomCard(
                source_type="INDIE_WEB",
                title=title,
                summary=summary,
                original_url=original_url,
                data_payload={
                    "category": "indie_web",
                    "sitename": name,
                    "tags": site["tags"],
                    "last_updated": site["last_updated"],
                    "views": site["views"],
                },
                embedding=nlp.generate_embedding(f"{title}. {summary}"),
            )
            await get_scoring_service().apply_scores(card)
            session.add(card)
            cards.append(card)

        if cards:
            await session.flush()
        logger.info(f"Neocities ingestion produced {len(cards)} cards")
        return cards
