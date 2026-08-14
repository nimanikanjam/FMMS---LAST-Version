"""
Milestone 1 Baseline Tests.

Validates that the Django configuration, core modules,
and authentication model are correctly wired. These tests
run without a database connection.
"""


class TestDjangoSetup:
    """Verify Django project configuration loads correctly."""

    def test_django_settings_importable(self) -> None:
        """Django settings module must be importable without errors."""
        from django.conf import settings

        assert settings.AUTH_USER_MODEL == "authentication.FMMSUser"
        assert settings.USE_TZ is True
        assert settings.TIME_ZONE == "UTC"

    def test_installed_apps_contains_authentication(self) -> None:
        """Authentication app must be in INSTALLED_APPS."""
        from django.conf import settings

        assert "apps.authentication" in settings.INSTALLED_APPS

    def test_middleware_contains_request_id(self) -> None:
        """RequestIDMiddleware must be active in MIDDLEWARE from M1."""
        from django.conf import settings

        assert "core.middleware.request_id.RequestIDMiddleware" in settings.MIDDLEWARE

    def test_middleware_contains_audit_log(self) -> None:
        """AuditLogMiddleware must be active in MIDDLEWARE from M1."""
        from django.conf import settings

        assert "core.middleware.audit_log.AuditLogMiddleware" in settings.MIDDLEWARE

    def test_migration_modules_configured(self) -> None:
        """Migration modules must point to infrastructure directories."""
        from django.conf import settings

        assert settings.MIGRATION_MODULES.get("authentication") == (
            "apps.authentication.infrastructure.migrations"
        )


class TestCoreExceptions:
    """Verify the FMMS exception hierarchy is correctly defined."""

    def test_base_exception_instantiable(self) -> None:
        """FMMSBaseException must be instantiable with default message."""
        from core.exceptions.base_exception import FMMSBaseException

        exc = FMMSBaseException()
        assert exc.message == "An unexpected error occurred."
        assert exc.error_code == "FMMS_ERROR"
        assert exc.details == {}

    def test_not_found_error(self) -> None:
        """FMMSNotFoundError must have correct defaults."""
        from core.exceptions.base_exception import FMMSNotFoundError

        exc = FMMSNotFoundError(message="Vehicle not found", details={"id": "abc"})
        assert exc.error_code == "NOT_FOUND"
        assert exc.message == "Vehicle not found"
        assert exc.details == {"id": "abc"}

    def test_exceptions_are_base_exception_subclasses(self) -> None:
        """All FMMS exceptions must inherit from FMMSBaseException."""
        from core.exceptions.base_exception import (
            FMMSBaseException,
            FMMSConflictError,
            FMMSIntegrationError,
            FMMSNotFoundError,
            FMMSPermissionError,
            FMMSStateError,
            FMMSValidationError,
        )

        for exc_class in [
            FMMSNotFoundError,
            FMMSValidationError,
            FMMSPermissionError,
            FMMSConflictError,
            FMMSStateError,
            FMMSIntegrationError,
        ]:
            assert issubclass(exc_class, FMMSBaseException)
            assert issubclass(exc_class, Exception)


class TestStructuredLogger:
    """Verify the structured logger factory behaves correctly."""

    def test_get_structured_logger_returns_adapter(self) -> None:
        """get_structured_logger must return an FMMSLoggerAdapter."""
        from core.logging.structured_logger import (
            FMMSLoggerAdapter,
            get_structured_logger,
        )

        logger = get_structured_logger(domain="vehicle", module="test_module")
        assert isinstance(logger, FMMSLoggerAdapter)

    def test_logger_has_correct_domain(self) -> None:
        """Logger adapter must bind the domain to its extra context."""
        from core.logging.structured_logger import get_structured_logger

        logger = get_structured_logger(domain="repair", module="test_module")
        assert (logger.extra or {}).get("domain") == "repair"

    def test_logger_namespace(self) -> None:
        """Logger must use fmms.<domain>.<module> namespace."""
        from core.logging.structured_logger import get_structured_logger

        logger = get_structured_logger(domain="fault", module="my_service")
        assert logger.logger.name == "fmms.fault.my_service"


class TestJSONFormatter:
    """Verify the structured JSON log formatter produces correct output."""

    def test_format_produces_valid_json(self) -> None:
        """Formatter must produce valid JSON for every log record."""
        import json
        import logging

        from core.logging.formatters import FMMSJSONFormatter

        formatter = FMMSJSONFormatter()
        record = logging.LogRecord(
            name="fmms.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"
        assert parsed["service"] == "fmms"
        assert "timestamp" in parsed
        assert "module" in parsed

    def test_format_includes_all_mandatory_fields(self) -> None:
        """Formatter output must include all FMMS mandatory log fields."""
        import json
        import logging

        from core.logging.formatters import FMMSJSONFormatter

        formatter = FMMSJSONFormatter()
        record = logging.LogRecord(
            name="fmms.vehicle",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        mandatory_fields = {
            "timestamp",
            "level",
            "service",
            "domain",
            "module",
            "message",
        }
        assert mandatory_fields.issubset(parsed.keys())


class TestFMMSUserModel:
    """Verify FMMSUser model structure without database access."""

    def test_user_model_importable(self) -> None:
        """FMMSUser must be importable from the infrastructure layer."""
        from apps.authentication.infrastructure.models import FMMSUser

        assert FMMSUser is not None

    def test_user_model_role_choices(self) -> None:
        """FMMSUserRole must define all supported FMMS roles."""
        from apps.authentication.infrastructure.models import FMMSUserRole

        roles = {choice[0] for choice in FMMSUserRole.choices}
        assert roles == {
            "ADMIN",
            "DISTRIBUTION",
            "TRANSPORT",
            "WORKSHOP_SUPERVISOR",
            "DRIVER",
            "VIEWER",
        }

    def test_user_model_username_field(self) -> None:
        """FMMSUser must use username as the login identifier."""
        from apps.authentication.infrastructure.models import FMMSUser

        assert FMMSUser.USERNAME_FIELD == "username"

    def test_user_model_required_fields(self) -> None:
        """email and full_name must be required fields."""
        from apps.authentication.infrastructure.models import FMMSUser

        assert "email" in FMMSUser.REQUIRED_FIELDS
        assert "full_name" in FMMSUser.REQUIRED_FIELDS

    def test_database_model_mixins_are_abstract(self) -> None:
        """Shared persistence mixins must not create standalone tables."""
        from infrastructure.database.model_mixins import (
            BusinessRecordModel,
            SoftDeleteMixin,
            TimestampMixin,
            UserAuditMixin,
            UUIDPrimaryKeyMixin,
        )

        mixins = (
            UUIDPrimaryKeyMixin,
            TimestampMixin,
            UserAuditMixin,
            SoftDeleteMixin,
            BusinessRecordModel,
        )
        assert all(model._meta.abstract for model in mixins)
