"""Celery worker configuration for background tasks."""

import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "bloom_scroll",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
)


@celery_app.task(name="ingest_owid_all")
def ingest_owid_all_task() -> dict:
    """
    Background task to ingest all OWID datasets.

    This will be implemented later when we need scheduled ingestion.
    For now, we use the API endpoint directly.
    """
    logger.info("Starting OWID ingestion task")
    return {"status": "not_implemented"}


# Periodic tasks configuration (Celery Beat)
celery_app.conf.beat_schedule = {
    "daily-owid-ingestion": {
        "task": "ingest_owid_all",
        "schedule": 86400.0,  # 24 hours
    },
}
