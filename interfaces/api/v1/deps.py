"""Composition root for REST API v1 services.

This module is the sole API-layer location that imports concrete repositories
and SAP adapters. Views consume only the factories defined here.
"""

from __future__ import annotations

from apps.authentication.infrastructure.user_profile_reader import (
    DjangoUserProfileReader,
)
from apps.driver.application.services.exit_center_service import DriverExitCenterService
from apps.driver.application.services.get_driver_service import (
    GetDriverService,
    ListDriversService,
)
from apps.driver.application.services.get_driver_summary_service import (
    GetDriverSummaryService,
)
from apps.driver.infrastructure.repositories import DjangoDriverRepository
from apps.driver.infrastructure.summary_readers import DjangoDriverSummaryReader
from apps.driver.infrastructure.vehicle_assignment_reader import (
    DjangoDriverVehicleAssignmentReader,
)
from apps.fault.application.services.assign_fault_service import AssignFaultService
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.application.services.distribution_fault_decision_service import (
    DistributionFaultDecisionService,
)
from apps.fault.application.services.get_fault_service import (
    GetFaultService,
    ListFaultsService,
)
from apps.fault.application.services.report_fault_service import ReportFaultService
from apps.fault.application.services.sync_fault_catalog_from_sap_service import (
    ListFaultCatalogService,
    SyncFaultCatalogFromSAPService,
)
from apps.fault.infrastructure.catalog_repositories import DjangoFaultCatalogRepository
from apps.fault.infrastructure.repositories import DjangoFaultRepository
from apps.handover.application.services.handover_service import (
    ConfirmVehicleHandoverService,
    CreateVehicleHandoverService,
    ListVehicleHandoversService,
)
from apps.handover.infrastructure.repositories import DjangoVehicleHandoverRepository
from apps.inspection.application.services.add_inspection_item_service import (
    AddInspectionItemService,
)
from apps.inspection.application.services.create_inspection_service import (
    CreateInspectionService,
)
from apps.inspection.application.services.get_inspection_service import (
    GetInspectionService,
    ListInspectionsService,
)
from apps.inspection.application.services.report_inspection_fault_service import (
    ReportInspectionFaultService,
)
from apps.inspection.application.services.submit_inspection_service import (
    SubmitInspectionService,
)
from apps.inspection.application.services.sync_inspection_templates_from_sap_service import (
    ListInspectionTemplatesService,
    SyncInspectionTemplatesFromSAPService,
)
from apps.inspection.infrastructure.repositories import DjangoInspectionRepository
from apps.inspection.infrastructure.template_repositories import (
    DjangoInspectionTemplateRepository,
)
from apps.integration.application.services.list_sap_sync_runs_service import (
    ListSAPSyncRunsService,
)
from apps.integration.application.services.retry_failed_sap_transactions_service import (
    RetryFailedSAPTransactionsService,
)
from apps.integration.application.services.run_sap_sync_service import RunSAPSyncService
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository
from apps.material.application.services.material_request_service import (
    ApproveMaterialRequestService,
    CreateMaterialRequestService,
    ListMaterialRequestsService,
    ReceiveMaterialRequestService,
)
from apps.material.application.services.parts_availability_decision_service import (
    DecidePartsAvailabilityService,
    IssuePurchasedPartsService,
)
from apps.material.application.services.sync_central_stock_from_sap_service import (
    ListCentralStockService,
    SyncCentralStockFromSAPService,
)
from apps.material.infrastructure.inventory_adapter import (
    StubInventoryAvailabilityAdapter,
)
from apps.material.infrastructure.repositories import (
    DjangoInventoryTransactionRepository,
    DjangoMaterialRequestRepository,
)
from apps.material.infrastructure.stock_repositories import DjangoCentralStockRepository
from apps.preventive_maintenance.application.services.complete_pm_work_order_service import (
    CompletePMWorkOrderService,
)
from apps.preventive_maintenance.application.services.create_pm_plan_service import (
    CreatePMPlanService,
)
from apps.preventive_maintenance.application.services.get_pm_service import (
    GetPMPlanService,
    ListPMPlansService,
    ListPMWorkOrdersService,
)
from apps.preventive_maintenance.application.services.trigger_overdue_pm_work_orders_service import (
    TriggerOverduePMWorkOrdersService,
)
from apps.preventive_maintenance.application.services.trigger_pm_work_order_service import (
    TriggerPMWorkOrderService,
)
from apps.preventive_maintenance.infrastructure.repositories import (
    DjangoPMPlanRepository,
    DjangoPMWorkOrderRepository,
)
from apps.procurement.application.services.add_pr_line_item_service import (
    AddPRLineItemService,
)
from apps.procurement.application.services.create_purchase_requisition_service import (
    CreatePurchaseRequisitionService,
)
from apps.procurement.application.services.get_procurement_service import (
    GetPurchaseOrderService,
    GetPurchaseRequisitionService,
    ListPurchaseRequisitionsService,
)
from apps.procurement.application.services.receive_po_from_sap_service import (
    ReceivePOFromSAPService,
)
from apps.procurement.application.services.submit_pr_to_sap_service import (
    SubmitPRToSAPService,
)
from apps.procurement.infrastructure.repositories import (
    DjangoPurchaseOrderRepository,
    DjangoPurchaseRequisitionRepository,
)
from apps.repair.application.services.add_repair_activity_service import (
    AddRepairActivityService,
    AddRepairPartService,
    DeleteRepairActivityService,
    DeleteRepairPartService,
    UpdateRepairActivityService,
    UpdateRepairPartService,
)
from apps.repair.application.services.approve_repair_order_service import (
    AcceptRepairOrderService,
    ApproveRepairOrderService,
    AssignWorkshopService,
    ListExternalWorkshopReferralRequestsService,
    RejectRepairOrderByTransportService,
    RejectRepairOrderService,
)
from apps.repair.application.services.assign_repair_order_service import (
    AssignRepairOrderService,
)
from apps.repair.application.services.create_repair_order_service import (
    CreateRepairOrderService,
)
from apps.repair.application.services.external_invoice_service import (
    ApproveExternalInvoiceService,
    ListExternalInvoicesService,
    UploadExternalInvoiceService,
)
from apps.repair.application.services.external_workshop_service import (
    AssignExternalWorkshopService,
    CancelExternalWorkshopAssignmentService,
    CloseExternalRepairService,
    ConfirmExternalWorkshopDeliveryService,
    ConfirmExternalWorkshopPickupService,
    GetExternalWorkshopAssignmentService,
    ListExternalWorkshopAssignmentsService,
    ReviewExternalRepairService,
)
from apps.repair.application.services.get_repair_order_service import (
    GetRepairOrderService,
    ListRepairOrdersService,
)
from apps.repair.application.services.register_internal_repair_cost_service import (
    RegisterInternalRepairCostService,
)
from apps.repair.application.services.repair_order_timeline_service import (
    GetRepairOrderTimelineService,
    RecordRepairOrderEventService,
)
from apps.repair.application.services.sync_repair_to_sap_service import (
    SyncRepairToSAPService,
)
from apps.repair.application.services.transport_handover_decision_service import (
    ApproveTransportHandoverService,
    RejectTransportHandoverService,
)
from apps.repair.application.services.update_repair_status_service import (
    CancelRepairOrderService,
    CompleteRepairOrderService,
    StartRepairService,
)
from apps.repair.application.services.workshop_technical_decision_service import (
    WorkshopTechnicalDecisionService,
)
from apps.repair.infrastructure.event_repositories import (
    DjangoRepairOrderEventRepository,
)
from apps.repair.infrastructure.external_workshop_repositories import (
    DjangoExternalWorkshopRepository,
)
from apps.repair.infrastructure.internal_cost_repositories import (
    DjangoInternalRepairCostRepository,
)
from apps.repair.infrastructure.invoice_repositories import (
    DjangoExternalRepairInvoiceRepository,
)
from apps.repair.infrastructure.repositories import (
    DjangoExternalWorkshopReferralRepository,
    DjangoRepairOrderRepository,
)
from apps.vehicle.application.services.change_vehicle_status_service import (
    ChangeVehicleStatusService,
)
from apps.vehicle.application.services.get_vehicle_service import (
    GetVehicleService,
    ListVehiclesService,
)
from apps.vehicle.application.services.get_vehicle_summary_service import (
    GetVehicleSummaryService,
)
from apps.vehicle.application.services.list_driver_assignment_history_service import (
    ListDriverVehicleAssignmentHistoryService,
    ListVehicleDriverAssignmentHistoryService,
)
from apps.vehicle.application.services.record_component_history_service import (
    ListVehicleComponentHistoryService,
    RecordComponentHistoryFromRepairService,
)
from apps.vehicle.application.services.record_odometer_service import (
    GetVehicleCurrentOdometerService,
    ListVehicleOdometerHistoryService,
    RecordVehicleOdometerService,
)
from apps.vehicle.application.services.sync_vehicles_from_sap_service import (
    SyncVehiclesFromSAPService,
)
from apps.vehicle.infrastructure.component_history_repositories import (
    DjangoVehicleComponentHistoryRepository,
)
from apps.vehicle.infrastructure.odometer_readers import (
    DjangoFaultVehicleOdometerReader,
)
from apps.vehicle.infrastructure.repositories import DjangoVehicleRepository
from infrastructure.sap.adapters.bapi.pm_notification_bapi_adapter import (
    PMNotificationBAPIAdapter,
)
from infrastructure.sap.adapters.bapi.pm_order_bapi_adapter import PMOrderBAPIAdapter
from infrastructure.sap.adapters.bapi.purchase_requisition_bapi_adapter import (
    PurchaseRequisitionBAPIAdapter,
)
from infrastructure.sap.adapters.bapi.vehicle_assignment_bapi_adapter import (
    VehicleAssignmentBAPIAdapter,
)
from infrastructure.sap.adapters.bapi.vehicle_measurement_bapi_adapter import (
    VehicleMeasurementBAPIAdapter,
)
from infrastructure.sap.adapters.odata.central_stock_odata_adapter import (
    CentralStockODataAdapter,
)
from infrastructure.sap.adapters.odata.fault_catalog_odata_adapter import (
    FaultCatalogODataAdapter,
)
from infrastructure.sap.adapters.odata.object_part_catalog_odata_adapter import (
    ObjectPartCatalogODataAdapter,
)
from infrastructure.sap.adapters.odata.vehicle_driver_odata_adapter import (
    VehicleDriverODataAdapter,
)
from infrastructure.sap.client.bapi_client import SAPBAPIClient
from infrastructure.sap.client.base import ISAPClient
from infrastructure.sap.client.disabled_client import DisabledSAPWriteClient
from infrastructure.sap.client.mock.mock_client import MockSAPClient
from infrastructure.sap.client.odata_client import SAPODataClient
from infrastructure.sap.config import SAPConfig
from infrastructure.sap.transaction.sap_transaction_manager import SAPTransactionManager


def _sap_client() -> ISAPClient:
    """Build the SAP client used exclusively by outbound write adapters.

    Returns:
        ``DisabledSAPWriteClient`` when ``SAP_WRITE`` is false,
        ``MockSAPClient`` in mock mode, or ``SAPBAPIClient`` for live RFC/BAPI.
    """
    config = SAPConfig.from_env()
    if not config.write_enabled:
        return DisabledSAPWriteClient()
    if config.use_mock:
        return MockSAPClient()
    return SAPBAPIClient(
        ashost=config.ashost,
        sysnr=config.sysnr,
        client=config.client,
        user=config.username,
        passwd=config.password,
        lang=config.lang,
    )


def _sap_odata_client() -> MockSAPClient | SAPODataClient:
    """Build the SAP OData client used for read integrations."""
    config = SAPConfig.from_env()
    if config.use_mock:
        return MockSAPClient()
    return SAPODataClient(
        base_url=config.base_url,
        username=config.username,
        password=config.password,
        client_code=config.client,
        timeout_seconds=config.timeout_seconds,
        verify_ssl=config.verify_ssl,
    )


def _sap_writes_enabled() -> bool:
    """Return whether outbound SAP write integrations are enabled."""
    return SAPConfig.from_env().write_enabled


def _vehicle_driver_adapter() -> VehicleDriverODataAdapter:
    """Return the configured SAP vehicle-driver adapter."""
    config = SAPConfig.from_env()
    return VehicleDriverODataAdapter(
        _sap_odata_client(),
        service=config.vehicle_driver_service,
        entity_set=config.vehicle_driver_entity_set,
    )


def get_vehicle_repository() -> DjangoVehicleRepository:
    """Return the vehicle repository."""
    return DjangoVehicleRepository()


def get_driver_repository() -> DjangoDriverRepository:
    """Return the driver repository."""
    return DjangoDriverRepository()


def get_inspection_repository() -> DjangoInspectionRepository:
    """Return the inspection repository."""
    return DjangoInspectionRepository()


def get_inspection_template_repository() -> DjangoInspectionTemplateRepository:
    """Return the inspection template repository."""
    return DjangoInspectionTemplateRepository()


def get_fault_repository() -> DjangoFaultRepository:
    """Return the fault repository."""
    return DjangoFaultRepository()


def get_fault_catalog_repository() -> DjangoFaultCatalogRepository:
    """Return the fault catalog repository."""
    return DjangoFaultCatalogRepository()


def get_material_request_repository() -> DjangoMaterialRequestRepository:
    """Return the material request repository."""
    return DjangoMaterialRequestRepository()


def get_central_stock_repository() -> DjangoCentralStockRepository:
    """Return the central warehouse stock repository."""
    return DjangoCentralStockRepository()


def get_inventory_transaction_repository() -> DjangoInventoryTransactionRepository:
    """Return the inventory transaction repository."""
    return DjangoInventoryTransactionRepository()


def get_vehicle_handover_repository() -> DjangoVehicleHandoverRepository:
    """Return the vehicle handover repository."""
    return DjangoVehicleHandoverRepository()


def get_repair_order_repository() -> DjangoRepairOrderRepository:
    """Return the repair-order repository."""
    return DjangoRepairOrderRepository()


def get_external_workshop_referral_repository() -> (
    DjangoExternalWorkshopReferralRepository
):
    """Return external workshop referral repository."""
    return DjangoExternalWorkshopReferralRepository()


def get_external_invoice_repository() -> DjangoExternalRepairInvoiceRepository:
    """Return external invoice repository."""
    return DjangoExternalRepairInvoiceRepository()


def get_external_workshop_repository() -> DjangoExternalWorkshopRepository:
    """Return external workshop workflow repository."""
    return DjangoExternalWorkshopRepository()


def get_pm_plan_repository() -> DjangoPMPlanRepository:
    """Return the PM-plan repository."""
    return DjangoPMPlanRepository()


def get_pm_work_order_repository() -> DjangoPMWorkOrderRepository:
    """Return the PM-work-order repository."""
    return DjangoPMWorkOrderRepository()


def get_purchase_requisition_repository() -> DjangoPurchaseRequisitionRepository:
    """Return the purchase-requisition repository."""
    return DjangoPurchaseRequisitionRepository()


def get_purchase_order_repository() -> DjangoPurchaseOrderRepository:
    """Return the purchase-order repository."""
    return DjangoPurchaseOrderRepository()


def get_sap_transaction_repository() -> DjangoSAPTransactionRepository:
    """Return the SAP transaction repository."""
    return DjangoSAPTransactionRepository()


def get_sap_transaction_manager() -> SAPTransactionManager:
    """Return the sole SAP write gateway (composition-root wiring)."""
    return SAPTransactionManager(
        repository=get_sap_transaction_repository(),
        writes_enabled=_sap_writes_enabled(),
    )


def get_user_profile_reader() -> DjangoUserProfileReader:
    """Return the FMMS user profile reader."""
    return DjangoUserProfileReader()


def get_change_vehicle_status_service() -> ChangeVehicleStatusService:
    """Return ChangeVehicleStatusService."""
    return ChangeVehicleStatusService(
        get_vehicle_repository(),
        get_repair_order_repository(),
        get_fault_repository(),
    )


def get_sync_vehicles_from_sap_service() -> SyncVehiclesFromSAPService:
    """Return SyncVehiclesFromSAPService for bulk vehicle-driver import."""
    return SyncVehiclesFromSAPService(
        get_vehicle_repository(),
        _vehicle_driver_adapter(),
        get_driver_repository(),
    )


def get_record_vehicle_odometer_service() -> RecordVehicleOdometerService:
    """Return RecordVehicleOdometerService."""
    return RecordVehicleOdometerService(get_vehicle_repository())


def get_list_vehicle_odometer_history_service() -> ListVehicleOdometerHistoryService:
    """Return ListVehicleOdometerHistoryService."""
    return ListVehicleOdometerHistoryService(get_vehicle_repository())


def get_get_vehicle_current_odometer_service() -> GetVehicleCurrentOdometerService:
    """Return GetVehicleCurrentOdometerService."""
    return GetVehicleCurrentOdometerService(get_vehicle_repository())


def get_list_vehicle_driver_assignment_history_service() -> (
    ListVehicleDriverAssignmentHistoryService
):
    """Return ListVehicleDriverAssignmentHistoryService."""
    return ListVehicleDriverAssignmentHistoryService(
        get_vehicle_repository(),
        get_driver_repository(),
    )


def get_list_driver_vehicle_assignment_history_service() -> (
    ListDriverVehicleAssignmentHistoryService
):
    """Return ListDriverVehicleAssignmentHistoryService."""
    return ListDriverVehicleAssignmentHistoryService(get_driver_repository())


def get_get_vehicle_service() -> GetVehicleService:
    """Return GetVehicleService."""
    return GetVehicleService(get_vehicle_repository(), get_driver_repository())


def get_list_vehicles_service() -> ListVehiclesService:
    """Return ListVehiclesService."""
    return ListVehiclesService(get_vehicle_repository(), get_driver_repository())


def get_get_vehicle_summary_service() -> GetVehicleSummaryService:
    """Return GetVehicleSummaryService."""
    return GetVehicleSummaryService()


def get_get_driver_service() -> GetDriverService:
    """Return GetDriverService."""
    return GetDriverService(
        get_driver_repository(),
        DjangoDriverVehicleAssignmentReader(),
    )


def get_list_drivers_service() -> ListDriversService:
    """Return ListDriversService."""
    return ListDriversService(
        get_driver_repository(),
        DjangoDriverVehicleAssignmentReader(),
    )


def get_get_driver_summary_service() -> GetDriverSummaryService:
    """Return GetDriverSummaryService."""
    return GetDriverSummaryService(DjangoDriverSummaryReader())


def get_driver_exit_center_service() -> DriverExitCenterService:
    """Return DriverExitCenterService."""
    return DriverExitCenterService(
        get_driver_repository(),
        get_vehicle_repository(),
        get_inspection_repository(),
        get_fault_repository(),
        get_repair_order_repository(),
    )


def get_create_inspection_service() -> CreateInspectionService:
    """Return CreateInspectionService."""
    return CreateInspectionService(
        get_inspection_repository(),
        get_vehicle_repository(),
        get_driver_repository(),
    )


def get_get_inspection_service() -> GetInspectionService:
    """Return GetInspectionService."""
    return GetInspectionService(
        get_inspection_repository(),
        get_fault_repository(),
        get_driver_repository(),
    )


def get_list_inspections_service() -> ListInspectionsService:
    """Return ListInspectionsService."""
    return ListInspectionsService(
        get_inspection_repository(),
        get_fault_repository(),
        get_driver_repository(),
    )


def get_add_inspection_item_service() -> AddInspectionItemService:
    """Return AddInspectionItemService."""
    return AddInspectionItemService(get_inspection_repository())


def get_submit_inspection_service() -> SubmitInspectionService:
    """Return SubmitInspectionService."""
    return SubmitInspectionService(
        get_inspection_repository(),
        get_fault_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
    )


def get_report_inspection_fault_service() -> ReportInspectionFaultService:
    """Return ReportInspectionFaultService."""
    if not _sap_writes_enabled():
        return ReportInspectionFaultService(
            get_inspection_repository(),
            get_fault_repository(),
            get_repair_order_repository(),
            get_vehicle_repository(),
        )
    client = _sap_client()
    return ReportInspectionFaultService(
        get_inspection_repository(),
        get_fault_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_sap_transaction_manager(),
        PMNotificationBAPIAdapter(client),
        VehicleMeasurementBAPIAdapter(client),
        DjangoFaultVehicleOdometerReader(),
    )


def get_list_inspection_templates_service() -> ListInspectionTemplatesService:
    """Return ListInspectionTemplatesService."""
    return ListInspectionTemplatesService(get_inspection_template_repository())


def get_sync_inspection_templates_from_sap_service() -> (
    SyncInspectionTemplatesFromSAPService
):
    """Return SyncInspectionTemplatesFromSAPService."""
    config = SAPConfig.from_env()
    return SyncInspectionTemplatesFromSAPService(
        get_inspection_template_repository(),
        ObjectPartCatalogODataAdapter(
            _sap_odata_client(),
            service=config.object_part_catalog_service,
            entity_set=config.object_part_catalog_entity_set,
        ),
    )


def get_list_fault_catalog_service() -> ListFaultCatalogService:
    """Return ListFaultCatalogService."""
    return ListFaultCatalogService(get_fault_catalog_repository())


def get_sync_fault_catalog_from_sap_service() -> SyncFaultCatalogFromSAPService:
    """Return SyncFaultCatalogFromSAPService."""
    config = SAPConfig.from_env()
    return SyncFaultCatalogFromSAPService(
        get_fault_catalog_repository(),
        FaultCatalogODataAdapter(
            _sap_odata_client(),
            service=config.fault_catalog_service,
            entity_set=config.fault_catalog_entity_set,
        ),
    )


def get_list_central_stock_service() -> ListCentralStockService:
    """Return ListCentralStockService."""
    return ListCentralStockService(get_central_stock_repository())


def get_sync_central_stock_from_sap_service() -> SyncCentralStockFromSAPService:
    """Return SyncCentralStockFromSAPService."""
    config = SAPConfig.from_env()
    return SyncCentralStockFromSAPService(
        get_central_stock_repository(),
        CentralStockODataAdapter(
            _sap_odata_client(),
            service=config.central_stock_service,
            entity_set=config.central_stock_entity_set,
        ),
    )


def get_run_sap_sync_service() -> RunSAPSyncService:
    """Return the global SAP read-sync orchestration service."""
    return RunSAPSyncService(
        get_sync_vehicles_from_sap_service(),
        get_sync_inspection_templates_from_sap_service(),
        get_sync_fault_catalog_from_sap_service(),
        get_sync_central_stock_from_sap_service(),
    )


def get_list_sap_sync_runs_service() -> ListSAPSyncRunsService:
    """Return ListSAPSyncRunsService."""
    return ListSAPSyncRunsService()


def get_report_fault_service() -> ReportFaultService:
    """Return ReportFaultService."""
    if not _sap_writes_enabled():
        return ReportFaultService(
            get_fault_repository(),
            get_vehicle_repository(),
            get_repair_order_repository(),
            get_user_profile_reader(),
        )
    client = _sap_client()
    return ReportFaultService(
        get_fault_repository(),
        get_vehicle_repository(),
        get_repair_order_repository(),
        get_user_profile_reader(),
        get_sap_transaction_manager(),
        PMNotificationBAPIAdapter(client),
        VehicleMeasurementBAPIAdapter(client),
        DjangoFaultVehicleOdometerReader(),
    )


def get_get_fault_service() -> GetFaultService:
    """Return GetFaultService."""
    return GetFaultService(get_fault_repository(), get_user_profile_reader())


def get_list_faults_service() -> ListFaultsService:
    """Return ListFaultsService."""
    return ListFaultsService(get_fault_repository(), get_user_profile_reader())


def get_assign_fault_service() -> AssignFaultService:
    """Return AssignFaultService."""
    return AssignFaultService(get_fault_repository())


def get_close_fault_service() -> CloseFaultService:
    """Return CloseFaultService."""
    return CloseFaultService(
        get_fault_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_distribution_fault_decision_service() -> DistributionFaultDecisionService:
    """Return DistributionFaultDecisionService."""
    if not _sap_writes_enabled():
        return DistributionFaultDecisionService(
            get_fault_repository(),
            get_vehicle_repository(),
            get_repair_order_repository(),
            get_record_repair_order_event_service(),
        )
    client = _sap_client()
    return DistributionFaultDecisionService(
        get_fault_repository(),
        get_vehicle_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
        get_sap_transaction_manager(),
        VehicleAssignmentBAPIAdapter(client),
    )


def get_repair_order_event_repository() -> DjangoRepairOrderEventRepository:
    """Return the repair-order event repository."""
    return DjangoRepairOrderEventRepository()


def get_record_repair_order_event_service() -> RecordRepairOrderEventService:
    """Return RecordRepairOrderEventService."""
    return RecordRepairOrderEventService(get_repair_order_event_repository())


def get_get_repair_order_timeline_service() -> GetRepairOrderTimelineService:
    """Return GetRepairOrderTimelineService."""
    return GetRepairOrderTimelineService(
        get_repair_order_repository(),
        get_repair_order_event_repository(),
    )


def get_create_repair_order_service() -> CreateRepairOrderService:
    """Return CreateRepairOrderService."""
    return CreateRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
        get_record_repair_order_event_service(),
    )


def get_get_repair_order_service() -> GetRepairOrderService:
    """Return GetRepairOrderService."""
    return GetRepairOrderService(get_repair_order_repository())


def get_list_repair_orders_service() -> ListRepairOrdersService:
    """Return ListRepairOrdersService."""
    return ListRepairOrdersService(get_repair_order_repository())


def get_assign_repair_order_service() -> AssignRepairOrderService:
    """Return AssignRepairOrderService."""
    return AssignRepairOrderService(get_repair_order_repository())


def get_approve_repair_order_service() -> ApproveRepairOrderService:
    """Return ApproveRepairOrderService."""
    return ApproveRepairOrderService(
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_assign_workshop_service() -> AssignWorkshopService:
    """Return AssignWorkshopService."""
    return AssignWorkshopService(
        get_repair_order_repository(),
        get_external_workshop_referral_repository(),
        get_vehicle_repository(),
        get_create_vehicle_handover_service(),
        get_record_repair_order_event_service(),
    )


def get_reject_repair_order_by_transport_service() -> (
    RejectRepairOrderByTransportService
):
    """Return RejectRepairOrderByTransportService."""
    return RejectRepairOrderByTransportService(
        get_repair_order_repository(),
        get_fault_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_list_external_workshop_referral_requests_service() -> (
    ListExternalWorkshopReferralRequestsService
):
    """Return ListExternalWorkshopReferralRequestsService."""
    return ListExternalWorkshopReferralRequestsService(
        get_external_workshop_referral_repository()
    )


def get_assign_external_workshop_service() -> AssignExternalWorkshopService:
    """Return AssignExternalWorkshopService."""
    return AssignExternalWorkshopService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_confirm_external_workshop_delivery_service() -> (
    ConfirmExternalWorkshopDeliveryService
):
    """Return ConfirmExternalWorkshopDeliveryService."""
    return ConfirmExternalWorkshopDeliveryService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_confirm_external_workshop_pickup_service() -> (
    ConfirmExternalWorkshopPickupService
):
    """Return ConfirmExternalWorkshopPickupService."""
    return ConfirmExternalWorkshopPickupService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_review_external_repair_service() -> ReviewExternalRepairService:
    """Return ReviewExternalRepairService."""
    return ReviewExternalRepairService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_close_external_repair_service() -> CloseExternalRepairService:
    """Return CloseExternalRepairService."""
    return CloseExternalRepairService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_fault_repository(),
        get_record_component_history_from_repair_service(),
        get_record_repair_order_event_service(),
    )


def get_cancel_external_workshop_assignment_service() -> (
    CancelExternalWorkshopAssignmentService
):
    """Return CancelExternalWorkshopAssignmentService."""
    return CancelExternalWorkshopAssignmentService(
        get_external_workshop_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_get_external_workshop_assignment_service() -> (
    GetExternalWorkshopAssignmentService
):
    """Return GetExternalWorkshopAssignmentService."""
    return GetExternalWorkshopAssignmentService(get_external_workshop_repository())


def get_list_external_workshop_assignments_service() -> (
    ListExternalWorkshopAssignmentsService
):
    """Return ListExternalWorkshopAssignmentsService."""
    return ListExternalWorkshopAssignmentsService(get_external_workshop_repository())


def get_workshop_technical_decision_service() -> WorkshopTechnicalDecisionService:
    """Return WorkshopTechnicalDecisionService."""
    return WorkshopTechnicalDecisionService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
        get_sync_repair_to_sap_service() if _sap_writes_enabled() else None,
        get_vehicle_handover_repository(),
        get_record_repair_order_event_service(),
    )


def get_accept_repair_order_service() -> AcceptRepairOrderService:
    """Return AcceptRepairOrderService (maps to repairable decision)."""
    return AcceptRepairOrderService(get_workshop_technical_decision_service())


def get_reject_repair_order_service() -> RejectRepairOrderService:
    """Return RejectRepairOrderService (maps to عدم نیاز به تعمیر)."""
    return RejectRepairOrderService(get_workshop_technical_decision_service())


def get_vehicle_component_history_repository() -> (
    DjangoVehicleComponentHistoryRepository
):
    """Return vehicle component history repository."""
    return DjangoVehicleComponentHistoryRepository()


def get_internal_repair_cost_repository() -> DjangoInternalRepairCostRepository:
    """Return internal repair cost repository."""
    return DjangoInternalRepairCostRepository()


def get_record_component_history_from_repair_service() -> (
    RecordComponentHistoryFromRepairService
):
    """Return RecordComponentHistoryFromRepairService."""
    return RecordComponentHistoryFromRepairService(
        get_vehicle_component_history_repository()
    )


def get_list_vehicle_component_history_service() -> ListVehicleComponentHistoryService:
    """Return ListVehicleComponentHistoryService."""
    return ListVehicleComponentHistoryService(
        get_vehicle_component_history_repository()
    )


def get_register_internal_repair_cost_service() -> RegisterInternalRepairCostService:
    """Return RegisterInternalRepairCostService."""
    return RegisterInternalRepairCostService(
        get_internal_repair_cost_repository(),
        get_repair_order_repository(),
    )


def get_approve_transport_handover_service() -> ApproveTransportHandoverService:
    """Return ApproveTransportHandoverService."""
    return ApproveTransportHandoverService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_fault_repository(),
        get_record_component_history_from_repair_service(),
        get_internal_repair_cost_repository(),
        get_record_repair_order_event_service(),
    )


def get_reject_transport_handover_service() -> RejectTransportHandoverService:
    """Return RejectTransportHandoverService."""
    return RejectTransportHandoverService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_create_material_request_service() -> CreateMaterialRequestService:
    """Return CreateMaterialRequestService."""
    return CreateMaterialRequestService(
        get_material_request_repository(),
        get_repair_order_repository(),
        get_central_stock_repository(),
        get_record_repair_order_event_service(),
    )


def get_list_material_requests_service() -> ListMaterialRequestsService:
    """Return ListMaterialRequestsService."""
    return ListMaterialRequestsService(
        get_material_request_repository(),
        get_central_stock_repository(),
    )


def get_decide_parts_availability_service() -> DecidePartsAvailabilityService:
    """Return DecidePartsAvailabilityService (explicit transport decision)."""
    return DecidePartsAvailabilityService(
        get_material_request_repository(),
        get_central_stock_repository(),
        get_inventory_transaction_repository(),
        get_create_purchase_requisition_service(),
        get_add_pr_line_item_service(),
        get_record_repair_order_event_service(),
    )


def get_issue_purchased_parts_service() -> IssuePurchasedPartsService:
    """Return IssuePurchasedPartsService."""
    return IssuePurchasedPartsService(
        get_material_request_repository(),
        get_inventory_transaction_repository(),
        get_central_stock_repository(),
        get_record_repair_order_event_service(),
    )


def get_approve_material_request_service() -> ApproveMaterialRequestService:
    """Return ApproveMaterialRequestService (compat auto-availability wrapper)."""
    return ApproveMaterialRequestService(
        get_material_request_repository(),
        StubInventoryAvailabilityAdapter(),
        get_decide_parts_availability_service(),
        get_record_repair_order_event_service(),
    )


def get_receive_material_request_service() -> ReceiveMaterialRequestService:
    """Return ReceiveMaterialRequestService."""
    return ReceiveMaterialRequestService(
        get_material_request_repository(),
        get_repair_order_repository(),
        get_central_stock_repository(),
        get_record_repair_order_event_service(),
    )


def get_create_vehicle_handover_service() -> CreateVehicleHandoverService:
    """Return CreateVehicleHandoverService."""
    return CreateVehicleHandoverService(get_vehicle_handover_repository())


def get_list_vehicle_handovers_service() -> ListVehicleHandoversService:
    """Return ListVehicleHandoversService."""
    return ListVehicleHandoversService(get_vehicle_handover_repository())


def get_confirm_vehicle_handover_service() -> ConfirmVehicleHandoverService:
    """Return ConfirmVehicleHandoverService."""
    return ConfirmVehicleHandoverService(
        get_vehicle_handover_repository(),
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
        get_external_invoice_repository(),
        get_fault_repository(),
        get_record_component_history_from_repair_service(),
    )


def get_start_repair_service() -> StartRepairService:
    """Return StartRepairService."""
    return StartRepairService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_complete_repair_order_service() -> CompleteRepairOrderService:
    """Return CompleteRepairOrderService."""
    return CompleteRepairOrderService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_material_request_repository(),
        get_create_vehicle_handover_service(),
        get_record_repair_order_event_service(),
    )


def get_cancel_repair_order_service() -> CancelRepairOrderService:
    """Return CancelRepairOrderService."""
    return CancelRepairOrderService(
        get_repair_order_repository(),
        get_external_workshop_repository(),
        get_record_repair_order_event_service(),
    )


def get_add_repair_activity_service() -> AddRepairActivityService:
    """Return AddRepairActivityService."""
    return AddRepairActivityService(get_repair_order_repository())


def get_update_repair_activity_service() -> UpdateRepairActivityService:
    """Return UpdateRepairActivityService."""
    return UpdateRepairActivityService(get_repair_order_repository())


def get_delete_repair_activity_service() -> DeleteRepairActivityService:
    """Return DeleteRepairActivityService."""
    return DeleteRepairActivityService(get_repair_order_repository())


def get_add_repair_part_service() -> AddRepairPartService:
    """Return AddRepairPartService."""
    return AddRepairPartService(get_repair_order_repository())


def get_update_repair_part_service() -> UpdateRepairPartService:
    """Return UpdateRepairPartService."""
    return UpdateRepairPartService(get_repair_order_repository())


def get_delete_repair_part_service() -> DeleteRepairPartService:
    """Return DeleteRepairPartService."""
    return DeleteRepairPartService(get_repair_order_repository())


def get_sync_repair_to_sap_service() -> SyncRepairToSAPService:
    """Return SyncRepairToSAPService."""
    return SyncRepairToSAPService(
        get_repair_order_repository(),
        get_vehicle_repository(),
        get_sap_transaction_manager(),
        PMOrderBAPIAdapter(_sap_client()),
    )


def get_upload_external_invoice_service() -> UploadExternalInvoiceService:
    """Return UploadExternalInvoiceService."""
    return UploadExternalInvoiceService(
        get_external_invoice_repository(),
        get_repair_order_repository(),
        get_record_repair_order_event_service(),
    )


def get_list_external_invoices_service() -> ListExternalInvoicesService:
    """Return ListExternalInvoicesService."""
    return ListExternalInvoicesService(get_external_invoice_repository())


def get_approve_external_invoice_service() -> ApproveExternalInvoiceService:
    """Return ApproveExternalInvoiceService."""
    return ApproveExternalInvoiceService(
        get_external_invoice_repository(),
        get_repair_order_repository(),
        get_fault_repository(),
        get_vehicle_repository(),
        get_record_repair_order_event_service(),
    )


def get_create_pm_plan_service() -> CreatePMPlanService:
    """Return CreatePMPlanService."""
    return CreatePMPlanService(get_pm_plan_repository(), get_vehicle_repository())


def get_get_pm_plan_service() -> GetPMPlanService:
    """Return GetPMPlanService."""
    return GetPMPlanService(get_pm_plan_repository())


def get_list_pm_plans_service() -> ListPMPlansService:
    """Return ListPMPlansService."""
    return ListPMPlansService(get_pm_plan_repository())


def get_list_pm_work_orders_service() -> ListPMWorkOrdersService:
    """Return ListPMWorkOrdersService."""
    return ListPMWorkOrdersService(get_pm_work_order_repository())


def get_trigger_pm_work_order_service() -> TriggerPMWorkOrderService:
    """Return TriggerPMWorkOrderService."""
    if not _sap_writes_enabled():
        return TriggerPMWorkOrderService(
            get_pm_plan_repository(),
            get_pm_work_order_repository(),
            get_vehicle_repository(),
        )
    return TriggerPMWorkOrderService(
        get_pm_plan_repository(),
        get_pm_work_order_repository(),
        get_vehicle_repository(),
        get_sap_transaction_manager(),
        PMNotificationBAPIAdapter(_sap_client()),
    )


def get_trigger_overdue_pm_work_orders_service() -> TriggerOverduePMWorkOrdersService:
    """Return TriggerOverduePMWorkOrdersService."""
    return TriggerOverduePMWorkOrdersService(
        get_pm_plan_repository(),
        get_trigger_pm_work_order_service(),
    )


def get_retry_failed_sap_transactions_service() -> RetryFailedSAPTransactionsService:
    """Return RetryFailedSAPTransactionsService."""
    client = _sap_client()
    return RetryFailedSAPTransactionsService(
        get_sap_transaction_manager(),
        PurchaseRequisitionBAPIAdapter(client),
        PMOrderBAPIAdapter(client),
        PMNotificationBAPIAdapter(client),
        VehicleMeasurementBAPIAdapter(client),
        VehicleAssignmentBAPIAdapter(client),
    )


def get_complete_pm_work_order_service() -> CompletePMWorkOrderService:
    """Return CompletePMWorkOrderService."""
    return CompletePMWorkOrderService(get_pm_work_order_repository())


def get_create_purchase_requisition_service() -> CreatePurchaseRequisitionService:
    """Return CreatePurchaseRequisitionService."""
    return CreatePurchaseRequisitionService(
        get_purchase_requisition_repository(),
        get_repair_order_repository(),
    )


def get_get_purchase_requisition_service() -> GetPurchaseRequisitionService:
    """Return GetPurchaseRequisitionService."""
    return GetPurchaseRequisitionService(get_purchase_requisition_repository())


def get_list_purchase_requisitions_service() -> ListPurchaseRequisitionsService:
    """Return ListPurchaseRequisitionsService."""
    return ListPurchaseRequisitionsService(get_purchase_requisition_repository())


def get_add_pr_line_item_service() -> AddPRLineItemService:
    """Return AddPRLineItemService."""
    return AddPRLineItemService(get_purchase_requisition_repository())


def get_submit_pr_to_sap_service() -> SubmitPRToSAPService:
    """Return SubmitPRToSAPService."""
    return SubmitPRToSAPService(
        get_purchase_requisition_repository(),
        get_sap_transaction_manager(),
        PurchaseRequisitionBAPIAdapter(_sap_client()),
    )


def get_get_purchase_order_service() -> GetPurchaseOrderService:
    """Return GetPurchaseOrderService."""
    return GetPurchaseOrderService(get_purchase_order_repository())


def get_receive_po_from_sap_service() -> ReceivePOFromSAPService:
    """Return ReceivePOFromSAPService."""
    return ReceivePOFromSAPService(
        get_purchase_requisition_repository(),
        get_purchase_order_repository(),
    )
