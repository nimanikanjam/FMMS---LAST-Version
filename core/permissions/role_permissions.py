"""Role-based permission classes for the FMMS REST API.

Permissions inspect ``request.user.role`` on the custom ``FMMSUser`` model.
They contain no business rules — only authorization gates for the API layer.

FMMS has six roles: DRIVER, TRANSPORT, DISTRIBUTION, WORKSHOP_SUPERVISOR
(one operational unit each), ADMIN (full edit access everywhere), and
VIEWER (read-only access everywhere). Every gate below therefore allows
VIEWER to read (SAFE methods) even where it denies VIEWER from writing.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def _role(user: Any) -> str | None:
    return getattr(user, "role", None)


def _is_admin(user: Any) -> bool:
    return bool(getattr(user, "is_superuser", False) or _role(user) == "ADMIN")


class IsFMMSAuthenticated(BasePermission):
    """Require an authenticated FMMS user."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True when the request has an authenticated user."""
        return bool(request.user and request.user.is_authenticated)


class _WriteRolesOrReadOnlyViewer(BasePermission):
    """Base: ADMIN always allowed; extra roles may write; VIEWER may only read.

    Subclasses set ``write_roles`` to the non-ADMIN roles allowed to write.
    """

    write_roles: frozenset[str] = frozenset()

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Gate access by role, with a read-only carve-out for VIEWER."""
        user: Any = request.user
        if not (user and user.is_authenticated):
            return False
        if _is_admin(user):
            return True
        role = _role(user)
        if role in self.write_roles:
            return True
        if request.method in SAFE_METHODS:
            return role == "VIEWER"
        return False


class IsAdminRole(_WriteRolesOrReadOnlyViewer):
    """Allow ADMIN (or superuser) to write; VIEWER may only read."""


class IsSupervisorOrAbove(_WriteRolesOrReadOnlyViewer):
    """Allow any operational-unit supervisor (or ADMIN) to write; VIEWER may only read."""

    write_roles = frozenset({"TRANSPORT", "DISTRIBUTION", "WORKSHOP_SUPERVISOR"})


class IsWorkshopSupervisorOrAbove(_WriteRolesOrReadOnlyViewer):
    """Allow the workshop (repairs) supervisor or ADMIN to write; VIEWER may only read."""

    write_roles = frozenset({"WORKSHOP_SUPERVISOR"})


class IsDistributionSupervisorOrAbove(_WriteRolesOrReadOnlyViewer):
    """Allow the distribution supervisor or ADMIN to write; VIEWER may only read."""

    write_roles = frozenset({"DISTRIBUTION"})


class IsTransportSupervisorOrAbove(_WriteRolesOrReadOnlyViewer):
    """Allow the transport supervisor or ADMIN to write; VIEWER may only read."""

    write_roles = frozenset({"TRANSPORT"})


class IsDriverOrTechnicianOrAbove(_WriteRolesOrReadOnlyViewer):
    """Allow DRIVER, the workshop supervisor, or ADMIN to write; VIEWER may only read.

    Used for driver-facing confirmation actions (vehicle handover, repair
    driver confirmation).
    """

    write_roles = frozenset({"DRIVER", "WORKSHOP_SUPERVISOR"})


class IsReadOnlyOrTechnicianOrAbove(BasePermission):
    """Allow any authenticated user for SAFE methods; writes need WORKSHOP_SUPERVISOR+.

    VIEWER (and every other role) may read. Mutating methods require
    WORKSHOP_SUPERVISOR or ADMIN.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Gate write access by role while allowing authenticated reads."""
        user: Any = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_admin(user) or _role(user) == "WORKSHOP_SUPERVISOR"


class IsReadOnlyOrDriverOrTechnicianOrAbove(BasePermission):
    """SAFE methods for any auth user; writes for DRIVER or WORKSHOP_SUPERVISOR+.

    Used for driver daily checklist / odometer / exit-center workflows.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Gate write access including DRIVER while allowing authenticated reads."""
        user: Any = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_admin(user) or _role(user) in {"WORKSHOP_SUPERVISOR", "DRIVER"}
