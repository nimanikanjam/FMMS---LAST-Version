"""SAPConfig — SAP connection settings loaded exclusively from environment.

Never hard-code credentials or endpoints. All values come from environment
variables. In development and test, ``SAP_USE_MOCK=True`` routes all SAP
calls through ``MockSAPClient`` without requiring real SAP credentials.

Required environment variables (when ``SAP_USE_MOCK`` is ``False``):
    SAP_BASE_URL      — OData base URL (e.g. https://sap.corp/sap/opu/odata/sap)
    SAP_CLIENT        — SAP client/mandant code (e.g. 100)
    SAP_USERNAME      — SAP technical user login
    SAP_PASSWORD      — SAP technical user password
    SAP_ASHOST        — SAP application server hostname (when SAP_WRITE=True)
    SAP_SYSNR         — SAP system number (when SAP_WRITE=True; default: 00)

Optional environment variables:
    SAP_TIMEOUT_SECONDS — HTTP request timeout (default: 30)
    SAP_USE_MOCK        — Use MockSAPClient instead of real SAP (default: True)
    SAP_WRITE / SAP_write — Enable SAP write integrations (default: True)
    SAP_LANG            — SAP logon language (default: EN)
    SAP_VERIFY_SSL      — Verify SAP HTTPS certificates (default: True)
    SAP_VEHICLE_DRIVER_SERVICE — Vehicle-driver OData service
        (default: ZC_VEHICLEDRIVER_CDS)
    SAP_VEHICLE_DRIVER_ENTITY_SET — Vehicle-driver entity set
        (default: ZC_VehicleDriver)
    SAP_VEHICLE_DRIVER_ODATA_SERVICE / SAP_VEHICLE_DRIVER_ODATA_ENTITY and
        legacy SAP_EQUIPMENT_* names are supported as fallbacks.
    SAP_OBJECT_PART_CATALOG_SERVICE    — Object-part catalog OData service
        (default: ZI_FLEET_CAT_B_CDS)
    SAP_OBJECT_PART_CATALOG_ENTITY_SET — Object-part catalog entity set
        (default: empty)
    SAP_FAULT_CATALOG_SERVICE    — Fault catalog OData service
        (default: ZI_B_DEFECTCATALOG9_CDS)
    SAP_FAULT_CATALOG_ENTITY_SET — Fault catalog entity set (default: empty)
    SAP_CENTRAL_STOCK_SERVICE    — Central warehouse stock OData service
        (default: ZI_STOCK_KH08_CDS)
    SAP_CENTRAL_STOCK_ENTITY_SET — Central stock entity set (default: empty)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class SAPConfig:
    """Immutable SAP connection configuration.

    All fields are read from environment variables. The class enforces that
    real credentials are present when ``use_mock`` is ``False``.

    Attributes:
        base_url: SAP OData service base URL.
        client: SAP client/mandant code.
        username: SAP technical user login.
        password: SAP technical user password.
        ashost: SAP RFC application server hostname.
        sysnr: SAP RFC system number.
        timeout_seconds: HTTP timeout for OData requests.
        use_mock: When ``True``, ``MockSAPClient`` is used for all calls.
        write_enabled: When ``True``, BAPI write calls are executed.
        lang: SAP logon language.
    """

    base_url: str
    client: str
    username: str
    password: str
    ashost: str
    sysnr: str
    timeout_seconds: int
    use_mock: bool
    write_enabled: bool
    lang: str
    verify_ssl: bool
    vehicle_driver_service: str
    vehicle_driver_entity_set: str
    object_part_catalog_service: str
    object_part_catalog_entity_set: str
    fault_catalog_service: str
    fault_catalog_entity_set: str
    central_stock_service: str
    central_stock_entity_set: str

    @classmethod
    def from_env(cls) -> SAPConfig:
        """Build a ``SAPConfig`` from current environment variables.

        Returns:
            A populated, immutable ``SAPConfig`` instance.

        Raises:
            ImproperlyConfigured: If ``SAP_USE_MOCK`` is ``False`` but required
                credentials are missing from the environment.
        """
        use_mock = _env_bool("SAP_USE_MOCK", default=True)
        write_enabled = _env_bool_first("SAP_WRITE", "SAP_write", default=True)

        base_url = os.environ.get("SAP_BASE_URL", "")
        client = os.environ.get("SAP_CLIENT", "")
        username = os.environ.get("SAP_USERNAME", "")
        password = os.environ.get("SAP_PASSWORD", "")
        ashost = os.environ.get("SAP_ASHOST", "")
        sysnr = os.environ.get("SAP_SYSNR", "00")
        lang = os.environ.get("SAP_LANG", "EN")
        verify_ssl = _env_bool("SAP_VERIFY_SSL", default=True)
        vehicle_driver_service = _env_first(
            "SAP_VEHICLE_DRIVER_SERVICE",
            "SAP_VEHICLE_DRIVER_ODATA_SERVICE",
            "SAP_EQUIPMENT_SERVICE",
            default="ZC_VEHICLEDRIVER_CDS",
        )
        vehicle_driver_entity_set = _env_first(
            "SAP_VEHICLE_DRIVER_ENTITY_SET",
            "SAP_VEHICLE_DRIVER_ODATA_ENTITY",
            "SAP_EQUIPMENT_ENTITY_SET",
            default="ZC_VehicleDriver",
        )
        object_part_catalog_service = os.environ.get(
            "SAP_OBJECT_PART_CATALOG_SERVICE",
            "ZI_FLEET_CAT_B_CDS",
        )
        object_part_catalog_entity_set = os.environ.get(
            "SAP_OBJECT_PART_CATALOG_ENTITY_SET",
            "",
        )
        fault_catalog_service = os.environ.get(
            "SAP_FAULT_CATALOG_SERVICE",
            "ZI_B_DEFECTCATALOG9_CDS",
        )
        fault_catalog_entity_set = os.environ.get(
            "SAP_FAULT_CATALOG_ENTITY_SET",
            "",
        )
        central_stock_service = os.environ.get(
            "SAP_CENTRAL_STOCK_SERVICE",
            "ZI_STOCK_KH08_CDS",
        )
        central_stock_entity_set = os.environ.get(
            "SAP_CENTRAL_STOCK_ENTITY_SET",
            "",
        )

        try:
            timeout_seconds = int(os.environ.get("SAP_TIMEOUT_SECONDS", "30"))
        except ValueError as exc:
            raise ImproperlyConfigured(
                "SAP_TIMEOUT_SECONDS must be an integer."
            ) from exc

        if not use_mock:
            missing = [
                name
                for name, val in [
                    ("SAP_BASE_URL", base_url),
                    ("SAP_CLIENT", client),
                    ("SAP_USERNAME", username),
                    ("SAP_PASSWORD", password),
                ]
                if not val
            ]
            if write_enabled and not ashost:
                missing.append("SAP_ASHOST")
            if missing:
                raise ImproperlyConfigured(
                    f"SAP_USE_MOCK is False but the following required environment "
                    f"variables are not set: {', '.join(missing)}"
                )

        return cls(
            base_url=base_url,
            client=client,
            username=username,
            password=password,
            ashost=ashost,
            sysnr=sysnr,
            timeout_seconds=timeout_seconds,
            use_mock=use_mock,
            write_enabled=write_enabled,
            lang=lang,
            verify_ssl=verify_ssl,
            vehicle_driver_service=vehicle_driver_service,
            vehicle_driver_entity_set=vehicle_driver_entity_set,
            object_part_catalog_service=object_part_catalog_service,
            object_part_catalog_entity_set=object_part_catalog_entity_set,
            fault_catalog_service=fault_catalog_service,
            fault_catalog_entity_set=fault_catalog_entity_set,
            central_stock_service=central_stock_service,
            central_stock_entity_set=central_stock_entity_set,
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes")


def _env_bool_first(*names: str, default: bool) -> bool:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None:
            return raw.strip().lower() in ("true", "1", "yes")
    return default


def _env_first(*names: str, default: str) -> str:
    """Return the first non-empty environment value from ``names``."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return default
