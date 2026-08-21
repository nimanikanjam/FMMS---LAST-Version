"""MockSAPClient — full SAP simulation for development and testing.

Simulates four scenarios configurable per-instance or per-call:

- ``SUCCESS``:   Returns canned responses matching real SAP OData/BAPI shapes.
- ``BAPI_ERROR``: Returns a BAPI RETURN table with ``TYPE='E'`` (business error).
- ``TRANSPORT_ERROR``: Raises ``SAPClientError`` immediately (network failure).
- ``DUPLICATE``: Returns a BAPI RETURN table signalling a duplicate document.

Usage::

    client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
    response = client.odata_get_xml("ZC_VEHICLEDRIVER_CDS")

    # Override scenario per call:
    response = client.bapi_call(
        "BAPI_ALM_NOTIF_CREATE",
        params={},
        _scenario=SAPMockScenario.BAPI_ERROR,
    )
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any

from infrastructure.sap.client.base import ISAPClient, SAPClientError
from infrastructure.sap.client.mock import scenarios as sc

logger = logging.getLogger(__name__)


class SAPMockScenario(StrEnum):
    """Configures which simulation scenario the MockSAPClient applies.

    Attributes:
        SUCCESS: Normal happy-path responses for all SAP operations.
        BAPI_ERROR: SAP returns a business error in the RETURN table.
        TRANSPORT_ERROR: Communication failure before SAP processes the request.
        DUPLICATE: SAP rejects the request as a duplicate document.
    """

    SUCCESS = "SUCCESS"
    BAPI_ERROR = "BAPI_ERROR"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    DUPLICATE = "DUPLICATE"


# ---------------------------------------------------------------------------
# OData response routing — maps (service, entity_prefix) → canned response
# ---------------------------------------------------------------------------

_ODATA_GET_ROUTES: dict[tuple[str, str], dict] = {
    ("API_DEFECTCODE_SRV", "DefectCode("): sc.ODATA_DEFECT_CODE_SINGLE,
    ("API_DEFECTCODE_SRV", "DefectCodeSet"): sc.ODATA_DEFECT_CODE_LIST,
    ("OBJECT_PART_CATALOG", "CatalogSet"): sc.ODATA_OBJECT_PART_LIST,
    ("OBJECT_PART_CATALOG", "CatalogEntry("): sc.ODATA_OBJECT_PART_SINGLE,
    ("API_PRODUCT_SRV", "A_Product("): sc.ODATA_MATERIAL_SINGLE,
    ("API_PRODUCT_SRV", "A_ProductPlant"): sc.ODATA_MATERIAL_LIST,
    ("API_MATERIAL_STOCK_SRV", "MatlStkInAcctMod("): sc.ODATA_STOCK_SINGLE,
    ("API_MATERIAL_STOCK_SRV", "MatlStkInAcctMod"): sc.ODATA_STOCK_LIST,
    ("ZC_VEHICLEDRIVER_CDS", "ZC_VehicleDriver"): sc.ODATA_VEHICLE_DRIVER_LIST,
}

_BASE_DIR = Path(__file__).resolve().parents[4]
_ODATA_XML_ROUTES: dict[str, Path] = {
    "ZC_VEHICLEDRIVER_CDS": _BASE_DIR
    / "docs"
    / "odata"
    / "جدول اطلاعات خودرو و راننده.xml",
    "ZI_FLEET_CAT_B_CDS": _BASE_DIR / "docs" / "odata" / "چک لیست روزانه.xml",
    "ZI_B_DEFECTCATALOG9_CDS": _BASE_DIR / "docs" / "odata" / "ایرادات.xml",
    "ZC_REPAIR01_CODE_CDS": _BASE_DIR / "docs" / "odata" / "فعالیت_تعمیرات.xml",
    "ZI_STOCK_KH08_CDS": _BASE_DIR
    / "docs"
    / "odata"
    / "موجودی انبار مرکزی قطعات یدکی.xml",
}

# Natural key each consumer collapses a fixture on. Some SAP CDS views emit
# several rows per key (one per valuation view), and the fixtures captured
# those rows verbatim. Callers store one row per key, so serving the raw
# fixture makes "rows received" and "rows stored" disagree — collapse here so
# the mock hands out exactly what a caller can persist.
_XML_DEDUP_KEYS: dict[str, tuple[str, ...]] = {
    "ZI_STOCK_KH08_CDS": (
        "Material",
        "Plant",
        "StorageLocation",
        "InventoryStockType",
    ),
}

# Column whose non-zero value wins when collapsing duplicates. In the stock
# fixture the trailing duplicate always carries 0.00, so picking it would drop
# the real valuation.
_XML_DEDUP_PREFERRED_COLUMN: dict[str, str] = {
    "ZI_STOCK_KH08_CDS": "StockValueInDisplayCurrency",
}

# BAPI response routing — maps function_module → (success, error, duplicate)
_BAPI_ROUTES: dict[str, tuple[dict, dict, dict]] = {
    "BAPI_ALM_NOTIF_CREATE": (
        sc.BAPI_PM_NOTIFICATION_CREATE_SUCCESS,
        sc.BAPI_PM_NOTIFICATION_ERROR,
        sc.BAPI_PM_NOTIFICATION_DUPLICATE,
    ),
    "BAPI_ALM_NOTIF_CLOSE": (
        sc.BAPI_PM_NOTIFICATION_CLOSE_SUCCESS,
        sc.BAPI_PM_NOTIFICATION_ERROR,
        sc.BAPI_PM_NOTIFICATION_ERROR,
    ),
    "MEASUREM_DOCUM_RFC_SINGLE_001": (
        sc.BAPI_VEHICLE_MEASUREMENT_UPDATE_SUCCESS,
        sc.BAPI_VEHICLE_MEASUREMENT_UPDATE_ERROR,
        sc.BAPI_VEHICLE_MEASUREMENT_UPDATE_ERROR,
    ),
    "ZFM_FLEET_ASSIGN_REPLACEMENT": (
        sc.BAPI_REPLACEMENT_ASSIGNMENT_SUCCESS,
        sc.BAPI_REPLACEMENT_ASSIGNMENT_ERROR,
        sc.BAPI_REPLACEMENT_ASSIGNMENT_ERROR,
    ),
    "BAPI_ALM_ORDER_MAINTAIN": (
        sc.BAPI_PM_ORDER_CREATE_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_ALM_ORDER_COMPLETE": (
        sc.BAPI_PM_ORDER_COMPLETE_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_ALM_ORDER_READ": (
        sc.BAPI_PM_ORDER_GET_SUCCESS,
        sc.BAPI_PM_ORDER_ERROR,
        sc.BAPI_PM_ORDER_ERROR,
    ),
    "BAPI_PR_CREATE": (
        sc.BAPI_PR_CREATE_SUCCESS,
        sc.BAPI_PR_CREATE_ERROR,
        sc.BAPI_PR_CREATE_DUPLICATE,
    ),
    "BAPI_PR_GET_DETAIL": (
        sc.BAPI_PR_GET_SUCCESS,
        sc.BAPI_PR_CREATE_ERROR,
        sc.BAPI_PR_CREATE_ERROR,
    ),
    "BAPI_PO_CREATE1": (
        sc.BAPI_PO_CREATE_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_PO_APPROVE": (
        sc.BAPI_PO_APPROVE_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_PO_GET_DETAIL": (
        sc.BAPI_PO_GET_SUCCESS,
        sc.BAPI_PO_CREATE_ERROR,
        sc.BAPI_PO_CREATE_ERROR,
    ),
    "BAPI_GOODSMVT_CREATE_GR": (
        sc.BAPI_GR_POST_SUCCESS,
        sc.BAPI_GR_POST_ERROR,
        sc.BAPI_GR_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CANCEL_GR": (
        sc.BAPI_GR_REVERSE_SUCCESS,
        sc.BAPI_GR_POST_ERROR,
        sc.BAPI_GR_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CREATE_GI": (
        sc.BAPI_GI_POST_SUCCESS,
        sc.BAPI_GI_POST_ERROR,
        sc.BAPI_GI_POST_ERROR,
    ),
    "BAPI_GOODSMVT_CANCEL_GI": (
        sc.BAPI_GI_REVERSE_SUCCESS,
        sc.BAPI_GI_POST_ERROR,
        sc.BAPI_GI_POST_ERROR,
    ),
    "BAPI_SERVICE_PO_CREATE": (
        sc.BAPI_SERVICE_PO_CREATE_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
    "BAPI_SERVICE_PO_CONFIRM": (
        sc.BAPI_SERVICE_PO_CONFIRM_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
    "BAPI_SERVICE_PO_GET": (
        sc.BAPI_SERVICE_PO_GET_SUCCESS,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
        sc.BAPI_SERVICE_PO_CREATE_ERROR,
    ),
}


# ---------------------------------------------------------------------------
# XML fixture loading
# ---------------------------------------------------------------------------


def _is_blank_or_zero(text: str) -> bool:
    """Report whether a SAP numeric string is empty or numerically zero."""
    cleaned = text.strip().replace(",", "")
    if not cleaned:
        return True
    try:
        return Decimal(cleaned) == 0
    except InvalidOperation:
        return False


def _column_names(root: ET.Element) -> list[str]:
    """Read the ``Columns/Column@Name`` list from a fixture root."""
    return [
        str(column.attrib.get("Name", "")).strip()
        for column in root.findall("./Columns/Column")
    ]


def _row_values(row: ET.Element) -> list[str]:
    """Read the ordered ``Value`` texts of one fixture row."""
    return [(value.text or "").strip() for value in row.findall("./Value")]


def _collapse_duplicate_rows(root: ET.Element, service: str) -> bool:
    """Drop duplicate rows in place, keeping the most complete one per key.

    No-op for services without a configured key, or when the fixture lacks one
    of the key columns.

    Returns:
        ``True`` when rows were actually removed.
    """
    key_columns = _XML_DEDUP_KEYS.get(service)
    rows_parent = root.find("./Rows")
    if not key_columns or rows_parent is None:
        return False

    positions = {name: index for index, name in enumerate(_column_names(root))}
    if any(column not in positions for column in key_columns):
        logger.warning(
            "MockSAPClient: fixture is missing dedup key columns",
            extra={"service": service, "key_columns": key_columns},
        )
        return False

    preferred = _XML_DEDUP_PREFERRED_COLUMN.get(service, "")
    preferred_position = positions.get(preferred, -1)

    def value_at(values: list[str], position: int) -> str:
        return values[position] if 0 <= position < len(values) else ""

    ordered_keys: list[tuple[str, ...]] = []
    winners: dict[tuple[str, ...], ET.Element] = {}
    winner_is_zero: dict[tuple[str, ...], bool] = {}

    for row in list(rows_parent):
        values = _row_values(row)
        key = tuple(value_at(values, positions[column]) for column in key_columns)
        is_zero = _is_blank_or_zero(value_at(values, preferred_position))
        if key not in winners:
            ordered_keys.append(key)
            winners[key] = row
            winner_is_zero[key] = is_zero
            continue
        # Later rows only win when they fill in a value the incumbent lacks.
        if winner_is_zero[key] and not is_zero:
            winners[key] = row
            winner_is_zero[key] = is_zero

    original_count = len(list(rows_parent))
    if len(winners) == original_count:
        return False

    logger.debug(
        "MockSAPClient: collapsed duplicate fixture rows",
        extra={
            "service": service,
            "rows_in_fixture": original_count,
            "rows_served": len(winners),
        },
    )
    for row in list(rows_parent):
        rows_parent.remove(row)
    for key in ordered_keys:
        rows_parent.append(winners[key])
    return True


def _load_fixture_text(service: str) -> str | None:
    """Return the XML fixture for a service, with duplicate rows collapsed.

    The file is returned verbatim unless rows were actually dropped, so
    fixtures without duplicates keep their original formatting.
    """
    path = _ODATA_XML_ROUTES.get(service)
    if path is None:
        return None
    raw = path.read_text(encoding="utf-8-sig")
    if service not in _XML_DEDUP_KEYS:
        return raw
    root = ET.fromstring(raw)  # noqa: S314
    if not _collapse_duplicate_rows(root, service):
        return raw
    return ET.tostring(root, encoding="unicode")


def _fixture_rows_as_dicts(service: str) -> list[dict[str, str]] | None:
    """Return the fixture for a service as OData-style row dictionaries."""
    text = _load_fixture_text(service)
    if text is None:
        return None
    root = ET.fromstring(text)  # noqa: S314
    columns = _column_names(root)
    rows: list[dict[str, str]] = []
    for row in root.findall("./Rows/Row"):
        values = _row_values(row)
        rows.append(
            {
                column: values[index] if index < len(values) else ""
                for index, column in enumerate(columns)
                if column
            }
        )
    return rows


class MockSAPClient(ISAPClient):
    """Simulated SAP client for development and testing.

    Provides canned responses that mirror real SAP OData/BAPI response shapes
    without requiring a live SAP system. Used in all non-production environments
    (``SAP_USE_MOCK=True``).

    Args:
        scenario: The default scenario applied to all calls.
            Can be overridden per-call via the ``_scenario`` kwarg
            accepted by all methods.

    Example::

        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        result = client.odata_get_xml("ZC_VEHICLEDRIVER_CDS")
        assert "VehicleNumber" in result
    """

    def __init__(self, scenario: SAPMockScenario = SAPMockScenario.SUCCESS) -> None:
        self._scenario = scenario

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_scenario(self, override: SAPMockScenario | None) -> SAPMockScenario:
        return override if override is not None else self._scenario

    @staticmethod
    def _route_odata(service: str, entity: str) -> dict[str, Any]:
        """Find the canned OData response for a (service, entity) pair."""
        for (svc, entity_prefix), response in _ODATA_GET_ROUTES.items():
            if svc == service and entity.startswith(entity_prefix):
                return response
        logger.warning(
            "MockSAPClient: no route for OData GET",
            extra={"service": service, "entity": entity},
        )
        return {"d": {"results": []}}

    @staticmethod
    def _route_bapi(function_module: str, scenario: SAPMockScenario) -> dict[str, Any]:
        """Find and select the canned BAPI response for a function module."""
        routes = _BAPI_ROUTES.get(function_module)
        if routes is None:
            logger.warning(
                "MockSAPClient: no route for BAPI call",
                extra={"function_module": function_module},
            )
            routes = (
                {"RETURN": sc._SAP_SUCCESS_RETURN},
                {"RETURN": sc._SAP_ERROR_RETURN},
                {"RETURN": sc._SAP_DUPLICATE_RETURN},
            )
        success_resp, error_resp, duplicate_resp = routes
        if scenario == SAPMockScenario.SUCCESS:
            return success_resp
        if scenario == SAPMockScenario.DUPLICATE:
            return duplicate_resp
        return error_resp  # BAPI_ERROR

    # ------------------------------------------------------------------
    # ISAPClient implementation
    # ------------------------------------------------------------------

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate an OData GET request.

        Args:
            service: OData service name.
            entity: Entity set or key expression.
            params: Ignored in mock.
            _scenario: Optional per-call scenario override.

        Returns:
            Canned OData response matching real SAP response shape.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.odata_get",
            extra={"service": service, "entity": entity, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling OData GET {service}/{entity}"
            )
        # Adapters that read a collection over JSON must see the same data as
        # those reading the XML feed; otherwise the fixture is bypassed and
        # only the small canned scenario is returned. Key lookups — entities
        # like ``Foo(Bar='1')`` — still fall through to the canned responses.
        if "(" not in entity:
            rows = _fixture_rows_as_dicts(service)
            if rows is not None:
                return {"d": {"results": rows}}
        return self._route_odata(service, entity)

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate an OData POST request.

        Args:
            service: OData service name.
            entity: Entity set.
            payload: Request body (ignored in mock).
            _scenario: Optional per-call scenario override.

        Returns:
            Canned OData response.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.odata_post",
            extra={"service": service, "entity": entity, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling OData POST {service}/{entity}"
            )
        return self._route_odata(service, entity)

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
        _scenario: SAPMockScenario | None = None,
    ) -> dict[str, Any]:
        """Simulate a BAPI/RFC function module call.

        Args:
            function_module: BAPI/RFC function module name.
            params: Function parameters (ignored in mock).
            _scenario: Optional per-call scenario override.

        Returns:
            Canned BAPI response with ``RETURN`` table.

        Raises:
            SAPClientError: If scenario is ``TRANSPORT_ERROR``.
        """
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.bapi_call",
            extra={"function_module": function_module, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling BAPI {function_module}"
            )
        return self._route_bapi(function_module, scenario)

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
        _scenario: SAPMockScenario | None = None,
    ) -> str:
        """Return raw XML from local OData fixture files."""
        scenario = self._resolve_scenario(_scenario)
        logger.debug(
            "MockSAPClient.odata_get_xml",
            extra={"service": service, "entity": entity, "scenario": scenario},
        )
        if scenario == SAPMockScenario.TRANSPORT_ERROR:
            raise SAPClientError(
                f"[MOCK] Transport error calling OData GET XML {service}/{entity}"
            )
        text = _load_fixture_text(service)
        if text is None:
            logger.warning(
                "MockSAPClient: no route for OData GET XML",
                extra={"service": service, "entity": entity},
            )
            return '<?xml version="1.0"?><Root><Columns></Columns><Rows></Rows></Root>'
        return text
