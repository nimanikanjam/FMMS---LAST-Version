"""Architecture tests for project-wide operational tooling."""

from django.apps import apps
from django.core.management import get_commands


def test_operations_app_owns_project_wide_commands() -> None:
    """Operational commands are discovered through the dedicated Django app."""
    config = apps.get_app_config("fmms_operations")

    assert config.name == "infrastructure.operations"
    assert get_commands()["reset_workflow_data"] == "infrastructure.operations"


def test_database_package_is_not_a_django_app() -> None:
    """Shared ORM primitives remain a plain Python package."""
    assert not apps.is_installed("infrastructure.database")
