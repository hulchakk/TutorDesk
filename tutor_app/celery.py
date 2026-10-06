import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tutor_app.settings.dev")

app = Celery("tutor_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
