"""
Perspective scoring via Selva, MADFAM's LLM gateway.

Selva exposes an OpenAI-compatible API at ``SELVA_BASE_URL`` (see
ECOSYSTEM.md: "every LLM call should route through Selva at /v1"). This
service scores cards at ingestion time and stamps ``score_provenance`` so
the API/UI only ever present machine-measured values (defect D5 contract,
2026-07-16 audit).

Dormant by default: with ``SELVA_BASE_URL`` unset, ``apply_scores`` is a
no-op and cards flow through unscored (scores hidden downstream). Scoring
failures never block ingestion — a card without scores beats no card.
"""

import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You score short content summaries for a "slow web" content aggregator.
Respond with ONLY a JSON object, no prose, with exactly these keys:
- "bias_score": number 0.0-1.0 (0.0 = right-leaning framing,
  0.5 = neutral/apolitical, 1.0 = left-leaning framing)
- "constructiveness_score": number 0.0-100.0 (how informative,
  constructive, and non-sensationalist the content is)
- "blindspot_tags": array of 0-3 short kebab-case topic tags naming
  perspectives or domains this content surfaces that mainstream feeds
  under-cover
"""


@dataclass
class PerspectiveScores:
    """Machine-measured perspective scores with provenance."""

    bias_score: float | None
    constructiveness_score: float | None
    blindspot_tags: list[str]
    provenance: str


class SelvaScoringService:
    """Scores cards through Selva's OpenAI-compatible chat completions API."""

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        """Scoring is active only when a Selva endpoint is configured."""
        return bool(settings.SELVA_BASE_URL.strip())

    async def score_text(
        self, title: str, summary: str | None, source_type: str
    ) -> PerspectiveScores | None:
        """
        Score one piece of content. Returns None when disabled or on any
        failure — callers must treat scores as strictly optional.
        """
        if not self.enabled:
            return None

        payload = {
            "model": settings.SELVA_SCORING_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Source type: {source_type}\n"
                        f"Title: {title}\n"
                        f"Summary: {summary or '(no summary)'}"
                    ),
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        if settings.SELVA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.SELVA_API_KEY}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{settings.SELVA_BASE_URL.rstrip('/')}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            return self._parse_scores(content)
        except Exception as e:
            logger.warning(f"Selva scoring failed (card will ship unscored): {e}")
            return None

    def _parse_scores(self, content: str) -> PerspectiveScores | None:
        """Parse and clamp the model's JSON reply; reject anything malformed."""
        try:
            # Tolerate models that wrap JSON in code fences or prose.
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                raise ValueError("no JSON object in reply")
            data = json.loads(match.group(0))

            bias = data.get("bias_score")
            constructiveness = data.get("constructiveness_score")
            tags = data.get("blindspot_tags", [])

            bias_score = (
                min(1.0, max(0.0, float(bias))) if bias is not None else None
            )
            constructiveness_score = (
                min(100.0, max(0.0, float(constructiveness)))
                if constructiveness is not None
                else None
            )
            blindspot_tags = [
                str(tag)[:50] for tag in tags if isinstance(tag, (str, int))
            ][:3] if isinstance(tags, list) else []

            if bias_score is None and constructiveness_score is None:
                return None

            return PerspectiveScores(
                bias_score=bias_score,
                constructiveness_score=constructiveness_score,
                blindspot_tags=blindspot_tags,
                provenance=f"selva/{settings.SELVA_SCORING_MODEL}",
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Unparseable Selva scoring reply: {e}")
            return None

    async def apply_scores(self, card: BloomCard) -> None:
        """
        Score a card in place and stamp provenance. No-op when disabled or
        when scoring fails — the card keeps NULL scores, which the API
        hides from users.
        """
        if not self.enabled:
            return

        scores = await self.score_text(
            title=str(card.title),
            summary=card.summary if isinstance(card.summary, str) else None,
            source_type=str(card.source_type),
        )
        if scores is None:
            return

        card.bias_score = scores.bias_score  # type: ignore[assignment]
        card.constructiveness_score = scores.constructiveness_score  # type: ignore[assignment]
        card.blindspot_tags = scores.blindspot_tags
        card.score_provenance = scores.provenance  # type: ignore[assignment]


_scoring_service: SelvaScoringService | None = None


def get_scoring_service() -> SelvaScoringService:
    """Get or create the global scoring service instance."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = SelvaScoringService()
    return _scoring_service
