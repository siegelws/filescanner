from __future__ import annotations

from celery import Celery

from app.config import get_settings

_settings = get_settings()

celery = Celery(
    "scanner",
    broker=_settings.CELERY_BROKER_URL,
    backend=_settings.CELERY_RESULT_BACKEND,
    include=["app.workers.scan_tasks"],
)

celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,        # one task at a time per worker slot — VMs are heavy
    task_default_queue="scans",
    task_routes={
        "app.workers.scan_tasks.dispatch_scan": {"queue": "scans"},
        "app.workers.scan_tasks.run_engine_scan": {"queue": "engine"},
    },
    broker_connection_retry_on_startup=True,
)
