"""
Content ingestion layer.

Responsible for fetching and normalizing content from diverse sources:
- Our World in Data (OWID)
- OpenAlex (Science papers)
- Aesthetics Wiki / CARI Institute
- Neocities (Indie Web)
- RSS-Bridge (General news)
"""

from app.ingestion.openalex import OpenAlexConnector

__all__ = ["OpenAlexConnector"]
