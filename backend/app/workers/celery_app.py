"""
Celery application instance.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "cae_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    result_expires=86400,   # 24h
    task_soft_time_limit=settings.job_timeout_seconds,
    task_time_limit=settings.job_timeout_seconds + 60,
    task_routes={
        "app.workers.tasks.run_analysis_task": {"queue": "default"},
        "app.workers.tasks.generate_report_task": {"queue": "default"},
    },
)
