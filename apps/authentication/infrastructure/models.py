"""
FMMS User Model.

Custom user model that replaces Django's default User.
Must be set as AUTH_USER_MODEL before any migrations are created.

Decision: ADR-009 — Custom User Model Before First Migration.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.authentication.infrastructure.managers import FMMSUserManager


class FMMSUserRole(models.TextChoices):
    """
    FMMS role enumeration.

    Controls what operations a user is permitted to perform.
    Role-based permission checks are enforced at the API layer.

    Six roles, one per operational unit plus two system-wide roles:
    DRIVER only sees the driver section (not the driver list), the three
    unit-supervisor roles (TRANSPORT/DISTRIBUTION/WORKSHOP_SUPERVISOR) are
    scoped to their own tab, ADMIN has full edit access everywhere, and
    VIEWER has read-only access everywhere.
    """

    DRIVER = "DRIVER", "راننده"
    TRANSPORT = "TRANSPORT", "مسئول ترابری"
    DISTRIBUTION = "DISTRIBUTION", "مسئول توزیع"
    WORKSHOP_SUPERVISOR = "WORKSHOP_SUPERVISOR", "مسئول تعمیرات"
    ADMIN = "ADMIN", "مدیر کل"
    VIEWER = "VIEWER", "ناظر کل"


class FMMSUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for FMMS.

    Uses username as the login identifier.
    Includes an FMMS-specific role field for authorization.

    All business models reference this via settings.AUTH_USER_MODEL
    to remain decoupled from the concrete model import.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique user identifier (UUID4).",
    )
    email = models.EmailField(
        unique=True,
        help_text="Email address for contact and notifications.",
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Username — used as the login identifier.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="User's full display name.",
    )
    role = models.CharField(
        max_length=20,
        choices=FMMSUserRole.choices,
        default=FMMSUserRole.VIEWER,
        db_index=True,
        help_text="FMMS role — controls API permissions.",
    )
    personnel_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "SAP personnel number (کد پرسنلی). Links this login user to SAP "
            "driver/employee master data for role-scoped access."
        ),
    )
    assigned_vehicle_id = models.UUIDField(
        null=True,
        blank=True,
        default=None,
        db_index=True,
        help_text=(
            "Vehicle manually assigned by an admin (cross-domain by ID only — "
            "no FK to the vehicle app)."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive users cannot log in.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Staff users can access the Django admin.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp of account creation (UTC).",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp of last profile update (UTC).",
    )

    objects: FMMSUserManager = FMMSUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email", "full_name"]

    class Meta:
        app_label = "authentication"
        db_table = "fmms_users"
        verbose_name = "FMMS User"
        verbose_name_plural = "FMMS Users"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    def __repr__(self) -> str:
        return f"FMMSUser(id={self.id!r}, email={self.email!r}, role={self.role!r})"

    @property
    def is_admin(self) -> bool:
        """Return True if the user has the ADMIN role."""
        return self.role == FMMSUserRole.ADMIN

    @property
    def is_viewer(self) -> bool:
        """Return True if the user has the read-only VIEWER role."""
        return self.role == FMMSUserRole.VIEWER

    @property
    def is_driver(self) -> bool:
        """Return True if the user has the DRIVER role."""
        return self.role == FMMSUserRole.DRIVER

    @property
    def is_unit_supervisor(self) -> bool:
        """Return True if the user supervises one operational unit (transport/distribution/workshop)."""
        return self.role in (
            FMMSUserRole.TRANSPORT,
            FMMSUserRole.DISTRIBUTION,
            FMMSUserRole.WORKSHOP_SUPERVISOR,
        )
