"""
Celery application configuration for async task processing.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "homeworkplus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "app.workers.tasks.process_image": {"queue": "ai"},
        "app.workers.tasks.ingest_document": {"queue": "rag"},
        "app.workers.tasks.generate_tts": {"queue": "voice"},
    },
    beat_schedule={},
)
