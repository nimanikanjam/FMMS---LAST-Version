"""Composition-root tests for independent SAP read and write modes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from infrastructure.sap.client.base import SAPClientError
from infrastructure.sap.client.disabled_client import DisabledSAPWriteClient
from infrastructure.sap.client.mock.mock_client import MockSAPClient
from infrastructure.sap.client.odata_client import SAPODataClient
from interfaces.api.v1 import deps


def _configure_real_reads_with_writes_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAP_USE_MOCK", "False")
    monkeypatch.setenv("SAP_WRITE", "False")
    monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
    monkeypatch.setenv("SAP_CLIENT", "100")
    monkeypatch.setenv("SAP_USERNAME", "readonly-user")
    monkeypatch.setenv("SAP_PASSWORD", "readonly-password")
    monkeypatch.setenv("SAP_ASHOST", "sap.example.test")


def test_real_odata_client_remains_enabled_when_sap_writes_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    client = deps._sap_odata_client()

    assert isinstance(client, SAPODataClient)


def test_write_client_is_fail_closed_when_sap_writes_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    client = deps._sap_client()

    assert isinstance(client, DisabledSAPWriteClient)
    with pytest.raises(SAPClientError, match="SAP_WRITE=False"):
        client.bapi_call("BAPI_SHOULD_NEVER_RUN", {})


def test_write_client_uses_mock_when_writes_and_mock_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAP_USE_MOCK", "True")
    monkeypatch.setenv("SAP_WRITE", "True")

    client = deps._sap_client()

    assert isinstance(client, MockSAPClient)


def test_write_client_uses_real_bapi_when_live_writes_are_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)
    monkeypatch.setenv("SAP_WRITE", "True")
    monkeypatch.setenv("SAP_SYSNR", "01")
    monkeypatch.setenv("SAP_LANG", "FA")
    client = MagicMock()
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(deps, "SAPBAPIClient", constructor)

    result = deps._sap_client()

    assert result is client
    constructor.assert_called_once_with(
        ashost="sap.example.test",
        sysnr="01",
        client="100",
        user="readonly-user",
        passwd="readonly-password",
        lang="FA",
    )


def test_transaction_manager_receives_global_write_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    manager = deps.get_sap_transaction_manager()

    assert manager._writes_enabled is False


def test_inspection_fault_service_omits_sap_write_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    service = deps.get_report_inspection_fault_service()

    assert service._sap_tx is None
    assert service._sap_pm_notification is None
    assert service._sap_measurement is None


def test_manual_fault_service_omits_sap_write_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    service = deps.get_report_fault_service()

    assert service._sap_tx is None
    assert service._sap_pm_notification is None
    assert service._sap_measurement is None


def test_distribution_service_omits_sap_write_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    service = deps.get_distribution_fault_decision_service()

    assert service._sap_tx is None
    assert service._sap_vehicle_assignment is None


def test_pm_trigger_service_omits_sap_write_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    service = deps.get_trigger_pm_work_order_service()

    assert service._tx_manager is None
    assert service._sap is None


def test_explicit_write_services_are_composed_with_both_guards_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_real_reads_with_writes_disabled(monkeypatch)

    repair_sync = deps.get_sync_repair_to_sap_service()
    pr_submit = deps.get_submit_pr_to_sap_service()
    retry_service = deps.get_retry_failed_sap_transactions_service()

    for service in (repair_sync, pr_submit):
        assert service._tx_manager._writes_enabled is False
        assert isinstance(service._sap._client, DisabledSAPWriteClient)
    assert retry_service._manager._writes_enabled is False
