"""Celery application factory for FMMS background tasks.

The Celery app is loaded from Django settings and autodiscovers task modules
under ``infrastructure.messaging.tasks``.
"""

from __future__ import annotations

import os

from celery import Celery
from django.core.exceptions import ImproperlyConfigured

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    raise ImproperlyConfigured(
        "DJANGO_SETTINGS_MODULE is required before starting a Celery process."
    )

app = Celery("fmms")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Explicit imports keep task registration deterministic for workers and tests.
app.conf.imports = (
    "infrastructure.messaging.tasks.sap_retry_tasks",
    "infrastructure.messaging.tasks.sap_sync_tasks",
    "infrastructure.messaging.tasks.maintenance_tasks",
)
