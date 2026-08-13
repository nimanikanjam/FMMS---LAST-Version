"""Django ORM models for the SAP Integration bounded context.

SAPTransactionModel enforces the idempotency key uniqueness required by ADR-008.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class SAPSyncRunModel(BusinessRecordModel):
    """Persistence model for one SAP read synchronisation run."""

    class TriggerSource(models.TextChoices):
        API = "API", "API"
        CELERY = "CELERY", "Celery"
        JOB = "JOB", "Job"

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        PARTIAL_SUCCESS = "PARTIAL_SUCCESS", "Partial success"

    trigger_source = models.CharField(
        max_length=20,
        choices=TriggerSource.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        db_index=True,
    )
    request_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    triggered_by_id = models.UUIDField(null=True, blank=True, default=None)
    started_at = models.DateTimeField(db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, default=None)
    summary = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        app_label = "integration"
        db_table = "sap_sync_run"
        verbose_name = "SAP Sync Run"
        verbose_name_plural = "SAP Sync Runs"
        indexes = [
            models.Index(
                fields=["trigger_source", "started_at"],
                name="sap_sync_run_source_time_idx",
            ),
            models.Index(
                fields=["status", "started_at"],
                name="sap_sync_run_status_time_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"SAPSyncRun {self.id} [{self.status}]"


class SAPSyncRunItemModel(BusinessRecordModel):
    """Persistence model for one item inside a SAP read sync run."""

    sync_run = models.ForeignKey(
        SAPSyncRunModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=SAPSyncRunModel.Status.choices,
        db_index=True,
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()
    summary = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        app_label = "integration"
        db_table = "sap_sync_run_item"
        verbose_name = "SAP Sync Run Item"
        verbose_name_plural = "SAP Sync Run Items"
        indexes = [
            models.Index(
                fields=["name", "finished_at"],
                name="sap_sync_item_name_time_idx",
            ),
            models.Index(
                fields=["sync_run", "name"],
                name="sap_sync_item_run_name_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"SAPSyncRunItem {self.name} [{self.status}]"


class SAPTransactionModel(BusinessRecordModel):
    """Persistence model for a SAP integration transaction aggregate root.

    The ``idempotency_key`` has a unique constraint — the repository must
    check this key before creating a new transaction to prevent duplicates.

    Attributes:
        object_type: The FMMS business object type being synchronized.
        object_id: UUID of the FMMS business object.
        idempotency_key: Unique key generated per operation to prevent duplicates.
        status: Current lifecycle status of this transaction.
        retry_count: Number of retry attempts completed.
        max_retries: Maximum retry attempts allowed.
        request_payload: JSON payload sent to SAP.
        response_payload: JSON response received from SAP (nullable).
        sap_document_number: SAP-assigned document number on success (optional).
        error_message: Last error text from SAP (optional).
        completed_at: UTC timestamp when the transaction reached a terminal state.
    """

    object_type = models.CharField(max_length=30, db_index=True)
    object_id = models.UUIDField(db_index=True)
    idempotency_key = models.CharField(max_length=255)
    status = models.CharField(max_length=20, db_index=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(null=True, blank=True, default=None)
    sap_document_number = models.CharField(max_length=30, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "integration"
        db_table = "sap_transaction"
        verbose_name = "SAP Transaction"
        verbose_name_plural = "SAP Transactions"
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="unique_sap_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["object_type", "object_id"],
                name="sap_tx_object_idx",
            ),
            models.Index(
                fields=["status", "retry_count"],
                name="sap_tx_retry_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"SAPTransaction {self.id} [{self.status}]"
