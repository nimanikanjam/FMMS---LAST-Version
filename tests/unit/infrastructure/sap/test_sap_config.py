"""Unit tests for SAP environment configuration."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured

from infrastructure.sap.config import SAPConfig


def test_sap_write_defaults_to_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SAP_WRITE", raising=False)

    config = SAPConfig.from_env()

    assert config.write_enabled is True


def test_sap_write_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAP_WRITE", "False")

    config = SAPConfig.from_env()

    assert config.write_enabled is False


def test_real_odata_read_does_not_require_rfc_host_when_writes_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAP_USE_MOCK", "False")
    monkeypatch.setenv("SAP_WRITE", "False")
    monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
    monkeypatch.setenv("SAP_CLIENT", "100")
    monkeypatch.setenv("SAP_USERNAME", "readonly-user")
    monkeypatch.setenv("SAP_PASSWORD", "readonly-password")
    monkeypatch.delenv("SAP_ASHOST", raising=False)

    config = SAPConfig.from_env()

    assert config.ashost == ""


def test_real_bapi_write_requires_rfc_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAP_USE_MOCK", "False")
    monkeypatch.setenv("SAP_WRITE", "True")
    monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
    monkeypatch.setenv("SAP_CLIENT", "100")
    monkeypatch.setenv("SAP_USERNAME", "write-user")
    monkeypatch.setenv("SAP_PASSWORD", "write-password")
    monkeypatch.delenv("SAP_ASHOST", raising=False)

    with pytest.raises(ImproperlyConfigured, match="SAP_ASHOST"):
        SAPConfig.from_env()


def test_vehicle_driver_new_env_vars_take_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_SERVICE", "NEW_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ENTITY_SET", "NewEntity")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", "OLD_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", "OldEntity")
    monkeypatch.setenv("SAP_EQUIPMENT_SERVICE", "LEGACY_SERVICE")
    monkeypatch.setenv("SAP_EQUIPMENT_ENTITY_SET", "LegacyEntity")

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "NEW_SERVICE"
    assert config.vehicle_driver_entity_set == "NewEntity"


def test_vehicle_driver_odata_env_vars_are_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ENTITY_SET", raising=False)
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", "OLD_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", "OldEntity")

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "OLD_SERVICE"
    assert config.vehicle_driver_entity_set == "OldEntity"


def test_vehicle_driver_legacy_equipment_env_vars_are_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ENTITY_SET", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", raising=False)
    monkeypatch.setenv("SAP_EQUIPMENT_SERVICE", "LEGACY_SERVICE")
    monkeypatch.setenv("SAP_EQUIPMENT_ENTITY_SET", "LegacyEntity")

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "LEGACY_SERVICE"
    assert config.vehicle_driver_entity_set == "LegacyEntity"


def test_vehicle_driver_defaults_match_current_cds_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ENTITY_SET", raising=False)
    monkeypatch.delenv("SAP_EQUIPMENT_SERVICE", raising=False)
    monkeypatch.delenv("SAP_EQUIPMENT_ENTITY_SET", raising=False)

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "ZC_VEHICLEDRIVER_CDS"
    assert config.vehicle_driver_entity_set == "ZC_VehicleDriver"


def test_sap_write_defaults_to_enabled(monkeypatch) -> None:
    monkeypatch.delenv("SAP_WRITE", raising=False)
    monkeypatch.delenv("SAP_write", raising=False)

    config = SAPConfig.from_env()

    assert config.write_enabled is True


def test_sap_write_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("SAP_WRITE", "False")

    config = SAPConfig.from_env()

    assert config.write_enabled is False


def test_sap_write_lowercase_alias_is_supported(monkeypatch) -> None:
    monkeypatch.delenv("SAP_WRITE", raising=False)
    monkeypatch.setenv("SAP_write", "False")

    config = SAPConfig.from_env()

    assert config.write_enabled is False
