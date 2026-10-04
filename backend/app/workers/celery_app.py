from celery import Celery
from app.config import settings

celery = Celery(
    "ai_tutor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery.conf.update(task_serializer="json", accept_content=["json"], timezone="UTC")
celery.autodiscover_tasks(["app.workers"])