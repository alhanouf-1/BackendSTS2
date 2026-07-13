from celery import Celery
from celery.schedules import crontab
from app.config.settings import settings

celery_app = Celery(
    "sts_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=[
        "app.tasks.email_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.progress_tasks"
    ],
    # Re-try database/broker connection failures on startup
    broker_connection_retry_on_startup=True
)

# Cron jobs configuration via celery-beat
celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-hourly": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired_tokens",
        "schedule": crontab(minute="0", hour="*"),  # Every hour
    },
    "cleanup-expired-class-chats-hourly": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired_class_chats",
        "schedule": crontab(minute="0", hour="*"),  # Every hour
    },
    "process-account-purging-daily": {
        "task": "app.tasks.cleanup_tasks.process_account_purging",
        "schedule": crontab(minute="0", hour="0"),  # Daily at midnight
    }
}
