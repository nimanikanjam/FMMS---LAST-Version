"""Fail-closed SAP client used while outbound writes are disabled."""

from __future__ import annotations

from typing import Any

from infrastructure.sap.client.base import ISAPClient, SAPClientError

_DISABLED_MESSAGE = "SAP writes are disabled by SAP_WRITE=False."


class DisabledSAPWriteClient(ISAPClient):
    """Reject every transport call if a write adapter is invoked accidentally.

    The transaction manager is the primary write gate. This client is a second
    guard at the transport boundary and lets write-related services be composed
    safely while writes are disabled.
    """

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise SAPClientError(_DISABLED_MESSAGE)

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        raise SAPClientError(_DISABLED_MESSAGE)

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise SAPClientError(_DISABLED_MESSAGE)

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        raise SAPClientError(_DISABLED_MESSAGE)
