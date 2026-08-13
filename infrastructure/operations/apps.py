"""Django application configuration for operational tooling."""

from django.apps import AppConfig


class OperationsConfig(AppConfig):
    """Register project-wide operational management commands."""

    name = "infrastructure.operations"
    label = "fmms_operations"
    verbose_name = "FMMS Operations"
