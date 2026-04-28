"""Are.na Aesthetics connector for fetching visual culture."""

import logging
from io import BytesIO
from typing import Any

import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.models.bloom_card import BloomCard

logger = logging.getLogger(__name__)


class AestheticsConnector:
    """
    Connector for fetching aesthetic images from Are.na.

    Are.na is a visual research platform where users curate
    collections (channels) of images and links.
    """

    # Are.na API base URL
    ARENA_API_BASE = "https://api.are.na/v2"

    # Curated channels focused on aesthetics
    CHANNELS = {
        "y2k": "y2k-aesthetic",
        "frutiger_aero": "frutiger-aero",
        "vaporwave": "vaporwave",
        "brutalism": "digital-brutalism",
        "solarpunk": "solarpunk",
        "webcore": "webcore",
    }

    def __init__(self, timeout: int = 30):
        """Initialize the connector."""
        self.timeout = timeout

    async def fetch_channel_blocks(
        self,
        channel_slug: str,
        limit: int = 10,
    ) -> list[dict[str, Any]] | None:
        """
        Fetch blocks (items) from an Are.na channel.

        Args:
            channel_slug: Channel identifier (e.g., "y2k-aesthetic")
            limit: Number of blocks to fetch (default: 10)

        Returns:
            List of block dictionaries, or None if fetch fails
        """
        url = f"{self.ARENA_API_BASE}/channels/{channel_slug}"

        try:
            logger.info(f"Fetching Are.na channel: {channel_slug}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params={"per": limit})
                response.raise_for_status()

            data = response.json()
            contents = data.get("contents", [])

            # Filter for image blocks only
            image_blocks = [
                block for block in contents
                if block.get("class") == "Image" and block.get("image")
            ]

            logger.info(f"Found {len(image_blocks)} image blocks in {channel_slug}")
            return image_blocks

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Are.na channel: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing Are.na data: {e}")
            return None

    async def calculate_aspect_ratio(self, image_url: str) -> float:
        """
        Download image and calculate aspect ratio (width/height).

        This is CRITICAL for preventing layout shifts in the frontend.

        Args:
            image_url: URL of the image

        Returns:
            Aspect ratio as float (width/height)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(image_url)
                response.raise_for_status()

            # Open image with PIL
            img = Image.open(BytesIO(response.content))
            width, height = img.size

            # Calculate aspect ratio
            aspect_ratio = width / height if height > 0 else 1.0

            logger.info(f"Image {image_url}: {width}x{height} = {aspect_ratio:.2f}")
            return aspect_ratio

        except Exception as e:
            logger.error(f"Error calculating aspect ratio: {e}")
            return 1.0  # Default to square if calculation fails

    def extract_dominant_color(self, image_data: bytes) -> str:
        """
        Extract dominant color from image for placeholder.

        Args:
            image_data: Raw image bytes

        Returns:
            Hex color string (e.g., "#FF00AA")
        """
        try:
            img = Image.open(BytesIO(image_data))
            # Resize to 1x1 to get average color
            img = img.resize((1, 1), Image.LANCZOS)
            pixel = img.getpixel((0, 0))

            # Handle RGBA vs RGB
            if isinstance(pixel, tuple):
                r, g, b = pixel[:3]
                return f"#{r:02x}{g:02x}{b:02x}"
            else:
                return "#808080"  # Gray fallback

        except Exception as e:
            logger.error(f"Error extracting dominant color: {e}")
            return "#808080"

    async def ingest_to_database(
        self,
        session: AsyncSession,
        channel_key: str = "y2k",
        limit: int = 10,
    ) -> list[BloomCard]:
        """
        Fetch aesthetic images and insert into database.

        Args:
            session: Database session
            channel_key: Key from CHANNELS dict
            limit: Number of images to fetch

        Returns:
            List of created BloomCard instances
        """
        if channel_key not in self.CHANNELS:
            logger.error(f"Unknown channel key: {channel_key}")
            return []

        channel_slug = self.CHANNELS[channel_key]

        # Fetch blocks from Are.na
        blocks = await self.fetch_channel_blocks(channel_slug, limit)
        if not blocks:
            return []

        cards = []

        for block in blocks:
            try:
                # Extract image data
                image_data = block.get("image", {})
                image_url = image_data.get("original", {}).get("url")

                if not image_url:
                    continue

                # Calculate aspect ratio
                aspect_ratio = await self.calculate_aspect_ratio(image_url)

                # Extract metadata
                title = block.get("title") or block.get("generated_title") or "Untitled"
                description = block.get("description") or ""
                source_url = block.get("source", {}).get("url") or f"https://www.are.na/block/{block.get('id')}"

                # Create data payload
                data_payload = {
                    "image_url": image_url,
                    "aspect_ratio": aspect_ratio,
                    "dominant_color": "#808080",  # TODO: Calculate from image
                    "vibe_tags": [channel_key],
                    "arena_block_id": block.get("id"),
                }

                # Generate embedding
                summary_text = (
                    description[:200]
                    if description
                    else f"Visual from {channel_key} aesthetic"
                )
                embedding_text = f"{title}. {summary_text}"
                nlp = get_nlp_processor()
                embedding = nlp.generate_embedding(embedding_text)

                # Create BloomCard
                card = BloomCard(
                    source_type="AESTHETIC",
                    title=title,
                    summary=summary_text,
                    original_url=source_url,
                    data_payload=data_payload,
                    embedding=embedding,
                )

                session.add(card)
                await session.flush()
                await session.refresh(card)

                cards.append(card)
                logger.info(f"Created aesthetic card {card.id}: {title}")

            except Exception as e:
                logger.error(f"Error processing block: {e}")
                continue

        logger.info(f"Ingested {len(cards)} aesthetic cards from {channel_slug}")
        return cards


async def ingest_all_aesthetics(
    session: AsyncSession,
    limit_per_channel: int = 5,
) -> list[BloomCard]:
    """
    Ingest images from all aesthetic channels.

    Args:
        session: Database session
        limit_per_channel: Number of images per channel

    Returns:
        List of created BloomCards
    """
    connector = AestheticsConnector()
    all_cards = []

    for channel_key in connector.CHANNELS.keys():
        cards = await connector.ingest_to_database(session, channel_key, limit_per_channel)
        all_cards.extend(cards)

    return all_cards
