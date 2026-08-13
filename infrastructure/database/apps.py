"""Django app config for infrastructure database utilities."""

from __future__ import annotations

from django.apps import AppConfig


class DatabaseConfig(AppConfig):
    """Registers shared database models and operational commands."""

    name = "infrastructure.database"
    label = "fmms_database"
    verbose_name = "FMMS Database Infrastructure"
