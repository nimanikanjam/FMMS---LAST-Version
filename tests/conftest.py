"""
FMMS Pytest Configuration and Shared Fixtures.

Provides reusable fixtures available across the entire test suite.
Domain tests (unit) should not use db-dependent fixtures.
Integration and API tests use the database fixtures.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """
    Return an unauthenticated DRF API test client.

    Use for testing endpoints that don't require authentication,
    or for testing 401 responses.
    """
    return APIClient()


@pytest.fixture
def admin_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """
    Return a persisted FMMSUser with ADMIN role.

    Requires database access (db fixture). Use only in integration tests.
    """
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="ADMIN", is_staff=True, is_superuser=True)


@pytest.fixture
def supervisor_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with the ADMIN role (non-superuser).

    Used where a test needs cross-domain write access gated purely by
    role (not the ``is_superuser`` flag), since ADMIN is the only role
    that passes every per-domain supervisor permission check.
    """
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="ADMIN")


@pytest.fixture
def distribution_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with DISTRIBUTION role."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="DISTRIBUTION")


@pytest.fixture
def transport_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with TRANSPORT role."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="TRANSPORT")


@pytest.fixture
def workshop_supervisor_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with WORKSHOP_SUPERVISOR role."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="WORKSHOP_SUPERVISOR")


@pytest.fixture
def viewer_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with VIEWER role (read-only)."""
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="VIEWER")


@pytest.fixture
def authenticated_client(admin_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """
    Return an API client authenticated as an admin user.

    Uses force_authenticate to bypass token/session setup in unit-style tests.
    Each role fixture owns a distinct client so concurrent fixtures do not
    overwrite each other's credentials.
    """
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def supervisor_client(supervisor_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a supervisor."""
    client = APIClient()
    client.force_authenticate(user=supervisor_user)
    return client


@pytest.fixture
def distribution_client(distribution_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a distribution supervisor."""
    client = APIClient()
    client.force_authenticate(user=distribution_user)
    return client


@pytest.fixture
def transport_client(transport_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a transport supervisor."""
    client = APIClient()
    client.force_authenticate(user=transport_user)
    return client


@pytest.fixture
def technician_client(technician_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a technician."""
    client = APIClient()
    client.force_authenticate(user=technician_user)
    return client


@pytest.fixture
def technician_user(db: None) -> "FMMSUser":  # type: ignore[name-defined]  # noqa: F821
    """Return a persisted FMMSUser with the WORKSHOP_SUPERVISOR role.

    TECHNICIAN was merged into WORKSHOP_SUPERVISOR; kept as its own
    fixture/client since it's used across many workshop-workflow tests.
    """
    from tests.factories.user_factory import FMMSUserFactory

    return FMMSUserFactory(role="WORKSHOP_SUPERVISOR")


@pytest.fixture
def technician_client(technician_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a workshop technician."""
    client = APIClient()
    client.force_authenticate(user=technician_user)
    return client


@pytest.fixture
def workshop_supervisor_client(
    workshop_supervisor_user: "FMMSUser",
) -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a central workshop supervisor."""
    client = APIClient()
    client.force_authenticate(user=workshop_supervisor_user)
    return client


@pytest.fixture
def viewer_client(viewer_user: "FMMSUser") -> APIClient:  # type: ignore[name-defined]  # noqa: F821
    """Return an API client authenticated as a read-only viewer."""
    client = APIClient()
    client.force_authenticate(user=viewer_user)
    return client
