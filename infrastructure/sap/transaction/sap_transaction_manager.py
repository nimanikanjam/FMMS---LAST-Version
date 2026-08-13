"""SAPTransactionManager — the sole gateway for tracked SAP write operations.

Every SAP write operation that requires idempotency, retry, and audit trail
must be executed through this manager. No BAPI adapter should be called
directly without transaction tracking.

Workflow per ``execute()`` call:
    1. Idempotency check — if a SUCCESS transaction exists for the key, return it.
    2. Create ``SAPTransaction`` with status PENDING, persist.
    3. Transition to IN_PROGRESS, persist.
    4. Invoke the adapter callable.
    5. On success: mark SUCCESS, store response and SAP document number.
    6. On failure: mark FAILED, store error message.

Retry workflow (called by Celery task):
    1. Load FAILED transaction by ID.
    2. If ``can_retry`` is False → mark EXHAUSTED, raise ``SAPRetryExhaustedError``.
    3. Transition to RETRYING via ``prepare_retry()``.
    4. Re-invoke adapter callable.
    5. On success: mark SUCCESS. On failure: mark FAILED (Celery re-schedules).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

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
from apps.integration.domain.interfaces.sap_transaction_repository import (
    ISAPTransactionRepository,
)
from core.sap.ports.sap_transaction_manager_port import (
    ISAPTransactionManager,
    SAPAdapterCallable,
)

logger = logging.getLogger(__name__)


class SAPTransactionManager(ISAPTransactionManager):
    """Orchestrates idempotency, retry, and audit for all SAP write operations.

    This is the sole concrete gateway for SAP writes. Application services
    depend on ``ISAPTransactionManager`` and never manage ``SAPTransaction``
    lifecycle themselves.

    Args:
        repository: The ``ISAPTransactionRepository`` used to persist transaction state.
        writes_enabled: Global outbound-write gate loaded from ``SAP_WRITE`` by
            the composition root. When disabled, no repository or adapter call
            is made.

    Example::

        manager = SAPTransactionManager(repository=sap_tx_repo)
        response, doc_number = manager.execute(
            object_type=SAPObjectType.FAULT,
            object_id=fault.id,
            idempotency_key=f"fault-notif-{fault.id}",
            request_payload={"equipment": "10000001", "defect": "E0001"},
            adapter_call=lambda payload: pm_notification_adapter.create_notification(...),
        )
    """

    def __init__(
        self,
        repository: ISAPTransactionRepository,
        *,
        writes_enabled: bool = True,
    ) -> None:
        self._repo = repository
        self._writes_enabled = writes_enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
        idempotency_key: str,
        request_payload: dict[str, Any],
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, Any], str]:
        """Execute a tracked SAP write operation.

        Args:
            object_type: The FMMS business object type being synced.
            object_id: The UUID of the FMMS business object.
            idempotency_key: A unique key that prevents duplicate SAP submissions.
                Must be deterministic for a given business event.
            request_payload: The request data sent to SAP (stored for audit/replay).
            adapter_call: A callable that accepts ``request_payload`` and returns
                ``(response_payload, sap_document_number)``. Typically a lambda
                wrapping an adapter method call.

        Returns:
            A ``(response_payload, sap_document_number)`` tuple.
            If the idempotency key already exists with a SUCCESS status, the
            cached response is returned without calling SAP again.

        Raises:
            SAPIdempotencyError: If an existing PENDING/IN_PROGRESS transaction
                exists for this key (concurrent submission detected).
            SAPIntegrationError: If the SAP call fails after recording the
                failure in the transaction.
        """
        self._ensure_writes_enabled()
        existing = self._repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return self._handle_existing(
                existing,
                idempotency_key=idempotency_key,
                request_payload=request_payload,
                adapter_call=adapter_call,
            )

        transaction = self._create_and_start(
            object_type=object_type,
            object_id=object_id,
            idempotency_key=idempotency_key,
            request_payload=request_payload,
        )

        return self._invoke(transaction, adapter_call, request_payload)

    def retry(
        self,
        transaction_id: uuid.UUID,
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, Any], str]:
        """Retry a previously failed SAP transaction.

        Called by the Celery retry task. Transitions the transaction through
        the retry state machine and re-invokes the adapter.

        Args:
            transaction_id: The UUID of the FAILED ``SAPTransaction`` to retry.
            adapter_call: The adapter callable to re-invoke.

        Returns:
            A ``(response_payload, sap_document_number)`` tuple on success.

        Raises:
            SAPTransactionNotFoundError: If no transaction exists with this ID.
            SAPRetryExhaustedError: If ``can_retry`` is ``False`` (max retries reached).
            SAPIntegrationError: If the retry attempt also fails.
        """
        self._ensure_writes_enabled()
        transaction = self._repo.get_by_id(transaction_id)

        if not transaction.can_retry:
            completed_at = datetime.now(tz=UTC)
            transaction.mark_exhausted(completed_at=completed_at)
            self._repo.save(transaction)
            logger.error(
                "SAP transaction retry exhausted",
                extra={
                    "transaction_id": str(transaction_id),
                    "object_type": transaction.object_type,
                    "retry_count": transaction.retry_count,
                    "domain": "integration",
                },
            )
            raise SAPRetryExhaustedError(
                transaction_id=transaction_id,
                max_retries=transaction.max_retries,
            )

        transaction.prepare_retry()
        self._repo.save(transaction)

        logger.info(
            "Retrying SAP transaction",
            extra={
                "transaction_id": str(transaction_id),
                "object_type": transaction.object_type,
                "retry_count": transaction.retry_count,
                "domain": "integration",
            },
        )

        return self._invoke(transaction, adapter_call, transaction.request_payload)

    def retry_all_pending(
        self,
        adapter_call_map: dict[SAPObjectType, SAPAdapterCallable],
    ) -> None:
        """Retry all FAILED transactions that are eligible for retry.

        Intended to be called by a periodic Celery beat task. Silently skips
        transactions whose object type has no adapter call registered.

        Args:
            adapter_call_map: Maps each ``SAPObjectType`` to its adapter callable.
        """
        if not self._writes_enabled:
            logger.info(
                "Skipping SAP retry sweep because writes are disabled",
                extra={"domain": "integration"},
            )
            return

        pending = self._repo.list_pending_for_retry()
        logger.info(
            "Starting SAP retry sweep",
            extra={"pending_count": len(pending), "domain": "integration"},
        )
        for transaction in pending:
            adapter_call = adapter_call_map.get(transaction.object_type)
            if adapter_call is None:
                logger.warning(
                    "No adapter registered for retry",
                    extra={
                        "transaction_id": str(transaction.id),
                        "object_type": transaction.object_type,
                        "domain": "integration",
                    },
                )
                continue
            try:
                self.retry(transaction.id, adapter_call)
            except (SAPRetryExhaustedError, SAPIntegrationError) as exc:
                logger.error(
                    "SAP retry failed",
                    extra={
                        "transaction_id": str(transaction.id),
                        "error": str(exc),
                        "domain": "integration",
                    },
                )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_writes_enabled(self) -> None:
        """Fail before persistence or transport when SAP writes are disabled."""
        if not self._writes_enabled:
            raise SAPIntegrationError("SAP writes are disabled by SAP_WRITE=False.")

    def _handle_existing(
        self,
        existing: SAPTransaction,
        *,
        idempotency_key: str,
        request_payload: dict[str, Any],
        adapter_call: SAPAdapterCallable,
    ) -> tuple[dict[str, Any], str]:
        """Return cached result, retry FAILED, or raise for in-flight keys."""
        if existing.status == SAPTransactionStatus.SUCCESS:
            logger.info(
                "SAP idempotency hit — returning cached response",
                extra={
                    "idempotency_key": idempotency_key,
                    "transaction_id": str(existing.id),
                    "domain": "integration",
                },
            )
            return existing.response_payload or {}, existing.sap_document_number or ""

        if existing.status in (
            SAPTransactionStatus.PENDING,
            SAPTransactionStatus.IN_PROGRESS,
            SAPTransactionStatus.RETRYING,
        ):
            raise SAPIdempotencyError(
                idempotency_key=idempotency_key,
                existing_transaction_id=existing.id,
            )

        if existing.status == SAPTransactionStatus.EXHAUSTED:
            raise SAPRetryExhaustedError(
                transaction_id=existing.id,
                max_retries=existing.max_retries,
            )

        # FAILED — resume through the retry state machine on re-submit.
        if not existing.can_retry:
            raise SAPRetryExhaustedError(
                transaction_id=existing.id,
                max_retries=existing.max_retries,
            )

        existing.prepare_retry()
        existing.request_payload = request_payload
        existing.updated_at = datetime.now(tz=UTC)
        self._repo.save(existing)
        logger.info(
            "Resuming FAILED SAP transaction via execute()",
            extra={
                "idempotency_key": idempotency_key,
                "transaction_id": str(existing.id),
                "retry_count": existing.retry_count,
                "domain": "integration",
            },
        )
        return self._invoke(existing, adapter_call, request_payload)

    def _create_and_start(
        self,
        object_type: SAPObjectType,
        object_id: uuid.UUID,
        idempotency_key: str,
        request_payload: dict[str, Any],
    ) -> SAPTransaction:
        """Create a new PENDING transaction and transition it to IN_PROGRESS."""
        now = datetime.now(tz=UTC)
        transaction = SAPTransaction(
            id=uuid.uuid4(),
            object_type=object_type,
            object_id=object_id,
            idempotency_key=idempotency_key,
            status=SAPTransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
            request_payload=request_payload,
        )
        self._repo.save(transaction)
        logger.info(
            "SAP transaction created",
            extra={
                "transaction_id": str(transaction.id),
                "object_type": object_type,
                "idempotency_key": idempotency_key,
                "domain": "integration",
            },
        )

        transaction.start()
        self._repo.save(transaction)
        return transaction

    def _invoke(
        self,
        transaction: SAPTransaction,
        adapter_call: SAPAdapterCallable,
        request_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """Invoke the adapter callable and update transaction state.

        When the transaction arrives in RETRYING state (from ``retry()``),
        an explicit IN_PROGRESS transition is required before the adapter call,
        following the domain state machine: RETRYING → IN_PROGRESS → SUCCESS/FAILED.
        """
        if transaction.status == SAPTransactionStatus.RETRYING:
            transaction.status = SAPTransactionStatus.IN_PROGRESS
            self._repo.save(transaction)

        try:
            response_payload, sap_doc_number = adapter_call(request_payload)
        except SAPIntegrationError as exc:
            transaction.fail(error_message=str(exc))
            self._repo.save(transaction)
            logger.error(
                "SAP transaction failed",
                extra={
                    "transaction_id": str(transaction.id),
                    "error": str(exc),
                    "domain": "integration",
                },
            )
            raise

        completed_at = datetime.now(tz=UTC)
        transaction.succeed(
            response_payload=response_payload,
            sap_document_number=sap_doc_number or None,
            completed_at=completed_at,
        )
        self._repo.save(transaction)
        logger.info(
            "SAP transaction succeeded",
            extra={
                "transaction_id": str(transaction.id),
                "sap_document_number": sap_doc_number,
                "domain": "integration",
            },
        )
        return response_payload, sap_doc_number
