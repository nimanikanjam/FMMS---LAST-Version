"""
FMMSUser Test Factory.

Provides a factory_boy factory for creating FMMSUser instances
in tests. Used by all test suites that need authenticated users
or user-attributed records.
"""

from __future__ import annotations

from typing import Any

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory


class FMMSUserFactory(DjangoModelFactory):
    """
    Factory for creating FMMSUser test instances.

    Generates unique email addresses per instance using factory.Sequence.
    All users are active and non-staff by default.

    Usage:
        user = FMMSUserFactory()
        admin = FMMSUserFactory(role="ADMIN", is_staff=True)
        tech  = FMMSUserFactory(role="WORKSHOP_SUPERVISOR", full_name="Ali Mohammadi")
    """

    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@fmms.test")
    full_name = factory.Faker("name")
    role = "VIEWER"
    is_active = True
    is_staff = False
    is_superuser = False

    @classmethod
    def _create(
        cls,
        model_class: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Use the custom manager's create_user to hash the password correctly."""
        password = kwargs.pop("password", "testpass123!")
        return model_class.objects.create_user(*args, password=password, **kwargs)
