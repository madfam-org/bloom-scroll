"""Our World in Data (OWID) connector for fetching datasets."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.processor import get_nlp_processor
from app.models.bloom_card import BloomCard
from app.schemas.bloom_card import OWIDDataPayload

logger = logging.getLogger(__name__)


class OWIDConnector:
    """
    Connector for fetching data from Our World in Data.

    OWID provides raw CSV/JSON data that can be rendered natively
    in the frontend instead of static images.
    """

    # OWID GitHub raw content base URL
    OWID_RAW_BASE = "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets"

    # Example datasets (can be expanded)
    DATASETS = {
        "co2_emissions": {
            "path": "CO2 emissions/CO2 emissions.csv",
            "indicator": "CO2 emissions",
            "unit": "tonnes",
        },
        "life_expectancy": {
            "path": "Life expectancy/Life expectancy.csv",
            "indicator": "Life expectancy",
            "unit": "years",
        },
        "child_mortality": {
            "path": "Child mortality/Child mortality.csv",
            "indicator": "Child mortality",
            "unit": "deaths per 1,000 live births",
        },
    }

    def __init__(self, timeout: int = 30):
        """Initialize the connector."""
        self.timeout = timeout

    def parse_csv(
        self,
        csv_path: str | Path,
        dataset_key: str = "co2_emissions",
        entity: str = "World",
        years_back: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Parse a local OWID-style CSV fixture into a data payload.

        Malformed rows are dropped rather than raising. This keeps ingestion
        resilient to poison-pill rows while preserving valid data points.
        """
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Error reading OWID CSV {csv_path}: {e}")
            return None

        return self._build_payload_from_dataframe(df, dataset_key, entity, years_back)

    def _build_payload_from_dataframe(
        self,
        df: pd.DataFrame,
        dataset_key: str,
        entity: str,
        years_back: int | None,
    ) -> dict[str, Any] | None:
        """Normalize an OWID dataframe into a chart payload."""
        if dataset_key not in self.DATASETS:
            logger.error(f"Unknown dataset key: {dataset_key}")
            return None

        if "Year" not in df.columns:
            logger.warning("OWID data missing Year column")
            return None

        dataset_info = self.DATASETS[dataset_key]
        df_filtered = df.copy()

        if "Entity" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Entity"] == entity].copy()

        if df_filtered.empty:
            logger.warning(f"No data found for entity: {entity}")
            return None

        value_column = df_filtered.columns[-1]
        if value_column == "Entity" and len(df_filtered.columns) >= 2:
            value_column = df_filtered.columns[-2]

        df_filtered["Year"] = pd.to_numeric(df_filtered["Year"], errors="coerce")
        df_filtered[value_column] = pd.to_numeric(df_filtered[value_column], errors="coerce")
        df_filtered = df_filtered.dropna(subset=["Year", value_column])

        if years_back is not None:
            current_year = datetime.now().year
            start_year = current_year - years_back
            df_filtered = df_filtered[df_filtered["Year"] >= start_year]

        df_filtered = df_filtered.sort_values("Year")

        if df_filtered.empty:
            logger.warning(f"No valid numeric data found for entity: {entity}")
            return None

        payload = OWIDDataPayload(
            chart_type="line",
            years=[int(year) for year in df_filtered["Year"].tolist()],
            values=[float(value) for value in df_filtered[value_column].tolist()],
            unit=dataset_info["unit"],
            indicator=dataset_info["indicator"],
            entity=entity,
        )

        return payload.model_dump()

    async def fetch_dataset(
        self,
        dataset_key: str,
        entity: str = "World",
        years_back: int = 20,
    ) -> dict[str, Any] | None:
        """
        Fetch a dataset from OWID and format for BloomCard.

        Args:
            dataset_key: Key from DATASETS dict (e.g., 'co2_emissions')
            entity: Country/region name (default: 'World')
            years_back: Number of years to fetch (default: 20)

        Returns:
            Dictionary with formatted data payload, or None if fetch fails
        """
        if dataset_key not in self.DATASETS:
            logger.error(f"Unknown dataset key: {dataset_key}")
            return None

        dataset_info = self.DATASETS[dataset_key]
        url = f"{self.OWID_RAW_BASE}/{dataset_info['path']}"

        try:
            logger.info(f"Fetching OWID dataset from {url}")

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

            # Parse CSV
            from io import StringIO

            df = pd.read_csv(StringIO(response.text))

            data_payload = self._build_payload_from_dataframe(
                df,
                dataset_key,
                entity,
                years_back,
            )
            if not data_payload:
                return None

            logger.info(
                f"Successfully fetched {len(data_payload['years'])} data points for {entity} - "
                f"{dataset_info['indicator']}"
            )

            return data_payload

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching OWID data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing OWID data: {e}")
            return None

    async def ingest_to_database(
        self,
        session: AsyncSession,
        dataset_key: str,
        entity: str = "World",
        years_back: int = 20,
    ) -> BloomCard | None:
        """
        Fetch OWID data and insert into database.

        Args:
            session: Database session
            dataset_key: Dataset to fetch
            entity: Country/region
            years_back: Years to fetch

        Returns:
            Created BloomCard instance, or None if failed
        """
        # Fetch data
        data_payload = await self.fetch_dataset(dataset_key, entity, years_back)
        if not data_payload:
            return None

        dataset_info = self.DATASETS[dataset_key]

        # Generate text for embedding
        title = f"{dataset_info['indicator']} - {entity}"
        summary = (
            f"Historical data on {dataset_info['indicator'].lower()} for {entity} "
            f"over the past {years_back} years."
        )
        embedding_text = f"{title}. {summary}"

        # Generate embedding
        nlp = get_nlp_processor()
        embedding = nlp.generate_embedding(embedding_text)

        # Create BloomCard
        card = BloomCard(
            source_type="OWID",
            title=title,
            summary=summary,
            original_url=f"https://ourworldindata.org/grapher/{dataset_key.replace('_', '-')}",
            data_payload=data_payload,
            embedding=embedding,
        )

        # Add to session
        session.add(card)
        await session.flush()
        await session.refresh(card)

        logger.info(f"Created BloomCard {card.id} for OWID dataset {dataset_key}")

        return card


async def ingest_all_owid_datasets(session: AsyncSession) -> list[BloomCard]:
    """
    Ingest all available OWID datasets for World entity.

    Args:
        session: Database session

    Returns:
        List of created BloomCards
    """
    connector = OWIDConnector()
    cards = []

    for dataset_key in connector.DATASETS.keys():
        card = await connector.ingest_to_database(session, dataset_key)
        if card:
            cards.append(card)

    return cards
