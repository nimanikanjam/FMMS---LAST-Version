"""Unit tests for SAPTransactionManager.

Tests cover:
- Success path: transaction created → IN_PROGRESS → SUCCESS
- Failure path: adapter raises → transaction marked FAILED
- Idempotency: same key called twice → cached response returned
- Retry success: FAILED transaction retried → SUCCESS
- Retry exhaustion: retry called when can_retry=False → EXHAUSTED
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.domain.exceptions import (
    SAPIdempotencyError,
    SAPIntegrationError,
    SAPRetryExhaustedError,
)
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_transaction(
    status: SAPTransactionStatus = SAPTransactionStatus.PENDING,
    retry_count: int = 0,
    max_retries: int = 3,
    response_payload: dict[str, Any] | None = None,
    sap_document_number: str | None = None,
) -> SAPTransaction:
    now = datetime.now(tz=UTC)
    return SAPTransaction(
        id=uuid.uuid4(),
        object_type=SAPObjectType.FAULT,
        object_id=uuid.uuid4(),
        idempotency_key=f"test-key-{uuid.uuid4()}",
        status=status,
        created_at=now,
        updated_at=now,
        retry_count=retry_count,
        max_retries=max_retries,
        response_payload=response_payload,
        sap_document_number=sap_document_number,
    )


def _success_adapter(_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    return {"NOTIFNO": "10000099"}, "10000099"


def _failing_adapter(_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    raise SAPIntegrationError("SAP rejected the request")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_capture_save(
    store: list[SAPTransaction],
) -> Callable[[SAPTransaction], SAPTransaction]:
    """Return a side_effect function that captures saved transactions."""

    def _save(tx: SAPTransaction) -> SAPTransaction:
        store.append(tx)
        return tx

    return _save


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerSuccessPath:
    """execute() creates transaction, calls adapter, marks SUCCESS."""

    def test_execute_returns_response_and_document_number(self) -> None:
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = None
        repo.save.side_effect = lambda tx: tx

        manager = SAPTransactionManager(repository=repo)
        response, doc_number = manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key="fault-notif-001",
            request_payload={"equipment": "10000001"},
            adapter_call=_success_adapter,
        )

        assert response == {"NOTIFNO": "10000099"}
        assert doc_number == "10000099"

    def test_execute_saves_transaction_three_times(self) -> None:
        """PENDING → IN_PROGRESS → SUCCESS = 3 save() calls."""
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = None
        repo.save.side_effect = lambda tx: tx

        manager = SAPTransactionManager(repository=repo)
        manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key="fault-notif-002",
            request_payload={},
            adapter_call=_success_adapter,
        )

        assert repo.save.call_count == 3

    def test_execute_final_transaction_status_is_success(self) -> None:
        saved_transactions: list[SAPTransaction] = []
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = None
        repo.save.side_effect = _make_capture_save(saved_transactions)

        manager = SAPTransactionManager(repository=repo)
        manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key="fault-notif-003",
            request_payload={},
            adapter_call=_success_adapter,
        )

        final_tx = saved_transactions[-1]
        assert final_tx.status == SAPTransactionStatus.SUCCESS
        assert final_tx.sap_document_number == "10000099"


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerFailurePath:
    """execute() marks transaction FAILED and re-raises SAPIntegrationError."""

    def test_execute_raises_sap_integration_error_on_adapter_failure(self) -> None:
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = None
        repo.save.side_effect = lambda tx: tx

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPIntegrationError, match="SAP rejected"):
            manager.execute(
                object_type=SAPObjectType.FAULT,
                object_id=uuid.uuid4(),
                idempotency_key="fault-notif-fail-001",
                request_payload={},
                adapter_call=_failing_adapter,
            )

    def test_execute_transaction_marked_failed_after_adapter_error(self) -> None:
        saved_transactions: list[SAPTransaction] = []
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = None
        repo.save.side_effect = _make_capture_save(saved_transactions)

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPIntegrationError):
            manager.execute(
                object_type=SAPObjectType.FAULT,
                object_id=uuid.uuid4(),
                idempotency_key="fault-notif-fail-002",
                request_payload={},
                adapter_call=_failing_adapter,
            )

        final_tx = saved_transactions[-1]
        assert final_tx.status == SAPTransactionStatus.FAILED
        assert "SAP rejected" in (final_tx.error_message or "")


# ---------------------------------------------------------------------------
# Global write gate
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerWriteGate:
    """SAP_WRITE=False blocks persistence, adapter calls, and retry queries."""

    def test_execute_is_blocked_before_repository_or_adapter_call(self) -> None:
        repo = MagicMock()
        adapter = MagicMock()
        manager = SAPTransactionManager(repository=repo, writes_enabled=False)

        with pytest.raises(SAPIntegrationError, match="SAP_WRITE=False"):
            manager.execute(
                object_type=SAPObjectType.FAULT,
                object_id=uuid.uuid4(),
                idempotency_key="disabled-write",
                request_payload={},
                adapter_call=adapter,
            )

        repo.assert_not_called()
        adapter.assert_not_called()

    def test_retry_is_blocked_before_repository_or_adapter_call(self) -> None:
        repo = MagicMock()
        adapter = MagicMock()
        manager = SAPTransactionManager(repository=repo, writes_enabled=False)

        with pytest.raises(SAPIntegrationError, match="SAP_WRITE=False"):
            manager.retry(uuid.uuid4(), adapter)

        repo.assert_not_called()
        adapter.assert_not_called()

    def test_retry_sweep_is_a_noop_when_writes_are_disabled(self) -> None:
        repo = MagicMock()
        adapter = MagicMock()
        manager = SAPTransactionManager(repository=repo, writes_enabled=False)

        manager.retry_all_pending({SAPObjectType.FAULT: adapter})

        repo.assert_not_called()
        adapter.assert_not_called()


# ---------------------------------------------------------------------------
# Idempotency path
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerIdempotency:
    """execute() returns cached result without calling adapter again."""

    def test_idempotency_hit_on_success_returns_cached_response(self) -> None:
        existing = _make_transaction(
            status=SAPTransactionStatus.SUCCESS,
            response_payload={"NOTIFNO": "99999"},
            sap_document_number="99999",
        )
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = existing

        adapter_spy = MagicMock(return_value=({"NOTIFNO": "99999"}, "99999"))
        manager = SAPTransactionManager(repository=repo)
        response, doc = manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key=existing.idempotency_key,
            request_payload={},
            adapter_call=adapter_spy,
        )

        assert response == {"NOTIFNO": "99999"}
        assert doc == "99999"
        adapter_spy.assert_not_called()
        repo.save.assert_not_called()

    def test_idempotency_raises_on_in_progress_transaction(self) -> None:
        existing = _make_transaction(status=SAPTransactionStatus.IN_PROGRESS)
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = existing

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPIdempotencyError):
            manager.execute(
                object_type=SAPObjectType.FAULT,
                object_id=uuid.uuid4(),
                idempotency_key=existing.idempotency_key,
                request_payload={},
                adapter_call=_success_adapter,
            )

    def test_idempotency_raises_on_pending_transaction(self) -> None:
        existing = _make_transaction(status=SAPTransactionStatus.PENDING)
        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = existing

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPIdempotencyError):
            manager.execute(
                object_type=SAPObjectType.FAULT,
                object_id=uuid.uuid4(),
                idempotency_key=existing.idempotency_key,
                request_payload={},
                adapter_call=_success_adapter,
            )

    def test_failed_transaction_is_resumed_on_execute(self) -> None:
        """Re-submit with the same key resumes a FAILED transaction."""
        failed = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=0,
            max_retries=3,
        )
        saved: list[SAPTransaction] = []

        def _save(tx: SAPTransaction) -> SAPTransaction:
            saved.append(tx)
            return tx

        repo = MagicMock()
        repo.get_by_idempotency_key.return_value = failed
        repo.save.side_effect = _save

        manager = SAPTransactionManager(repository=repo)
        response, doc = manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=failed.object_id,
            idempotency_key=failed.idempotency_key,
            request_payload={"retry": True},
            adapter_call=_success_adapter,
        )

        assert doc
        assert response
        assert failed.status == SAPTransactionStatus.SUCCESS
        assert failed.retry_count == 1


# ---------------------------------------------------------------------------
# Retry path
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerRetry:
    """retry() re-invokes the adapter and updates transaction state."""

    def test_retry_success_marks_transaction_success(self) -> None:
        failed_tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=1,
            max_retries=3,
        )
        saved: list[SAPTransaction] = []
        repo = MagicMock()
        repo.get_by_id.return_value = failed_tx
        repo.save.side_effect = _make_capture_save(saved)

        manager = SAPTransactionManager(repository=repo)
        response, doc = manager.retry(failed_tx.id, _success_adapter)

        assert response == {"NOTIFNO": "10000099"}
        final_tx = saved[-1]
        assert final_tx.status == SAPTransactionStatus.SUCCESS

    def test_retry_failure_marks_transaction_failed(self) -> None:
        failed_tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=1,
            max_retries=3,
        )
        saved: list[SAPTransaction] = []
        repo = MagicMock()
        repo.get_by_id.return_value = failed_tx
        repo.save.side_effect = _make_capture_save(saved)

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPIntegrationError):
            manager.retry(failed_tx.id, _failing_adapter)

        final_tx = saved[-1]
        assert final_tx.status == SAPTransactionStatus.FAILED


# ---------------------------------------------------------------------------
# Retry exhaustion
# ---------------------------------------------------------------------------


class TestSAPTransactionManagerRetryExhaustion:
    """retry() raises SAPRetryExhaustedError when can_retry is False."""

    def test_retry_exhausted_raises_error(self) -> None:
        exhausted_tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=3,
            max_retries=3,
        )
        repo = MagicMock()
        repo.get_by_id.return_value = exhausted_tx
        repo.save.side_effect = lambda tx: tx

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPRetryExhaustedError):
            manager.retry(exhausted_tx.id, _success_adapter)

    def test_retry_exhausted_transaction_saved_as_exhausted(self) -> None:
        exhausted_tx = _make_transaction(
            status=SAPTransactionStatus.FAILED,
            retry_count=3,
            max_retries=3,
        )
        saved: list[SAPTransaction] = []
        repo = MagicMock()
        repo.get_by_id.return_value = exhausted_tx
        repo.save.side_effect = _make_capture_save(saved)

        manager = SAPTransactionManager(repository=repo)
        with pytest.raises(SAPRetryExhaustedError):
            manager.retry(exhausted_tx.id, _success_adapter)

        assert saved[-1].status == SAPTransactionStatus.EXHAUSTED
