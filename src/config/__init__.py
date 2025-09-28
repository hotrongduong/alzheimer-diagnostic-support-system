# File này đảm bảo Celery app được import khi Django khởi động.
from .celery import app as celery_app

__all__ = ('celery_app',)