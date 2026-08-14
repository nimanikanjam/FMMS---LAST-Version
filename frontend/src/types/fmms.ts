export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LinkedDriver {
  id: string;
  customer_number: string;
  name: string;
  personnel_number: string;
}

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  personnel_number?: string;
  linked_driver?: LinkedDriver | null;
  assigned_vehicle_id?: string | null;
  assigned_vehicle_plate?: string | null;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface UserAccount {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  personnel_number: string;
  assigned_vehicle_id: string | null;
  assigned_vehicle_plate: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  token_type: string;
  access_expires_at: string;
  refresh_expires_at: string;
  user: AuthUser;
}

export interface RefreshTokenResponse {
  access: string;
  token_type: string;
  access_expires_at: string;
}

export type VehicleStatus =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'UNDER_REPAIR'
  | 'UNDER_EXTERNAL_REPAIR'
  | 'WAITING_DRIVER_CONFIRMATION'
  | 'EXITED_CENTER'
  | 'SUSPENDED'
  | 'OUT_OF_SERVICE'
  | 'DECOMMISSIONED';

export interface AssignedVehicleDriver {
  id: string | null;
  customer_number: string;
  name: string | null;
}

export type DriverStatus = 'ACTIVE' | 'DECOMMISSIONED';

export interface DriverAssignedVehicle {
  id: string;
  vehicle_number: string;
  license_plate: string;
}

export interface Driver {
  id: string;
  customer_number: string;
  name: string;
  status: DriverStatus | string;
  created_at: string;
  updated_at: string;
  mobile: string | null;
  personnel_number: string | null;
  gender: string | null;
  nilofar_code: string | null;
  current_vehicle_as_driver?: DriverAssignedVehicle | null;
  current_vehicle_as_assistant?: DriverAssignedVehicle | null;
}

export interface DriverSummary {
  active_count: number;
  decommissioned_count: number;
  with_vehicle_count: number;
  last_sap_sync_at: string | null;
}

export interface DriverVehicleAssignmentHistoryItem {
  id: string;
  sync_run_id: string;
  request_id: string;
  synced_at: string;
  vehicle_id: string;
  vehicle_number: string;
  license_plate: string;
  driver_role: 'DRIVER' | 'ASSISTANT' | string;
  driver_customer_number: string | null;
}

export interface InspectionTemplate {
  id: string;
  code_group: string;
  code: string;
  group_text: string;
  code_text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ChecklistResult = 'PASS' | 'FAIL' | 'NOT_APPLICABLE' | 'NA';
export type FailureSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type InspectionType = 'PRE_TRIP' | 'POST_TRIP' | 'PERIODIC' | 'UNSCHEDULED';
export type InspectionStatus = 'DRAFT' | 'SUBMITTED' | 'REVIEWED' | string;

export interface InspectionItemInput {
  category: string;
  description: string;
  result: ChecklistResult;
  notes?: string | null;
  severity?: FailureSeverity | null;
}

export interface Inspection {
  id: string;
  vehicle_id: string;
  inspection_type: InspectionType | string;
  odometer_value: number;
  odometer_unit: string;
  status: InspectionStatus;
  inspected_at: string;
  created_at: string;
  updated_at: string;
  items: Array<{
    id: string;
    category: string;
    description: string;
    result: ChecklistResult | string;
    notes: string | null;
    severity: FailureSeverity | string | null;
  }>;
  driver_id: string | null;
  has_failures: boolean;
  overall_result: 'PASS' | 'FAIL' | string;
  related_fault_ids: string[];
  driver?: { id: string; name: string } | null;
}

export interface Vehicle {
  id: string;
  vehicle_number: string;
  license_plate: string;
  status: VehicleStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
  commissioning_date: string | null;
  driver1: AssignedVehicleDriver | null;
  driver2: AssignedVehicleDriver | null;
}

export interface VehicleSummary {
  active_fleet_count: number;
  operational_fleet_count: number;
  under_repair_fleet_count: number;
  unusable_fleet_count: number;
  last_sap_sync_at: string | null;
  average_odometer_km: number;
  average_faults_last_30_days: number;
}

export interface OdometerReading {
  id: string;
  vehicle_id: string;
  reading_date: string;
  odometer_km: number;
  source: string;
  recorded_by: string;
  recorded_at: string;
  updated_at: string;
}

export interface VehicleDriverAssignmentHistory {
  assigned_at: string;
  driver1: AssignedVehicleDriver | null;
  driver2: AssignedVehicleDriver | null;
}

export interface Fault {
  id: string;
  vehicle_id: string;
  code: string;
  description: string;
  severity: string;
  status: string;
  inspection_id?: string | null;
  sap_notification_number?: string | null;
  distribution_decision_note?: string | null;
  items?: Array<{
    id: string;
    component: string;
    description: string;
    severity: string;
    inspection_item_id?: string | null;
  }>;
  reported_at?: string;
  created_at?: string;
}

export interface FaultCatalog {
  id: string;
  code_group: string;
  code: string;
  group_text: string;
  code_text: string;
  defect_class: string;
  defect_class_text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** SAP's real defect catalog (with severity) — fault-type options offered while failing a daily-inspection item. */
export interface InspectionDefectOption {
  id: string;
  code_group: string;
  code: string;
  group_text: string;
  code_text: string;
  defect_class: string;
  defect_class_text: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RepairOrder {
  id: string;
  vehicle_id: string;
  fault_id: string;
  status: string;
  workshop_type?: string;
  workshop_id?: string;
  sap_order_number?: string;
  transport_rejection_reason?: string | null;
  transport_approval_note?: string | null;
  workshop_decision_note?: string | null;
  updated_at?: string;
  completed_at?: string | null;
  estimated_delivery_at?: string | null;
  parts?: RepairPart[];
  activities?: RepairActivity[];
}

export interface VehicleHandover {
  id: string;
  repair_order_id: string;
  vehicle_id: string;
  status: 'WAITING_DRIVER_CONFIRMATION' | 'ACCEPTED' | 'REJECTED' | string;
  created_at: string;
  updated_at: string;
  comment?: string | null;
  driver_id?: string | null;
  confirmed_at?: string | null;
}

export interface ExternalWorkshopDelivery {
  id: string;
  assignment_id: string;
  repair_order_id: string;
  vehicle_id: string;
  delivery_datetime: string;
  workshop_name: string;
  workshop_address: string;
  workshop_phone: string;
  vehicle_odometer: number;
  notes: string;
  delivered_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ExternalWorkshopPickup {
  id: string;
  assignment_id: string;
  repair_order_id: string;
  vehicle_id: string;
  pickup_datetime: string;
  vehicle_odometer: number;
  notes: string;
  picked_up_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ExternalRepairReview {
  id: string;
  assignment_id: string;
  repair_order_id: string;
  invoice_attachment?: string | null;
  repair_services: Array<Record<string, unknown>>;
  replaced_parts: Array<Record<string, unknown>>;
  repair_cost?: string | null;
  additional_notes: string;
  sap_purchase_order_number?: string | null;
  sap_invoice_document_number?: string | null;
  status: 'DRAFT' | 'COMPLETED' | string;
  reviewed_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface ExternalWorkshopAssignment {
  id: string;
  repair_order_id: string;
  vehicle_id: string;
  fault_id: string;
  workshop_id?: string | null;
  workshop_name: string;
  workshop_address: string;
  assignment_date: string;
  repair_reason: string;
  description: string;
  status: 'ACTIVE' | 'CANCELLED' | 'COMPLETED' | string;
  assigned_by_id: string;
  cancellation_reason?: string | null;
  cancellation_note?: string | null;
  cancelled_by_id?: string | null;
  cancelled_at?: string | null;
  created_at: string;
  updated_at: string;
  delivery?: ExternalWorkshopDelivery | null;
  pickup?: ExternalWorkshopPickup | null;
  review?: ExternalRepairReview | null;
}

export interface RepairPart {
  id: string;
  material_number: string;
  quantity: number;
  unit_of_measure?: string;
  posted_at?: string | null;
}

export interface RepairActivity {
  id: string;
  description: string;
  labor_hours: string | number;
  performed_at: string;
  notes?: string | null;
}

export type SAPTransactionStatus =
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'SUCCESS'
  | 'FAILED'
  | 'RETRYING'
  | 'EXHAUSTED';

export type SAPObjectType =
  | 'VEHICLE'
  | 'FAULT'
  | 'REPAIR_ORDER'
  | 'PM_WORK_ORDER'
  | 'MEASUREMENT_DOCUMENT'
  | 'VEHICLE_ASSIGNMENT'
  | 'PURCHASE_REQUISITION'
  | 'PURCHASE_ORDER'
  | 'GOODS_RECEIPT'
  | 'GOODS_ISSUE';

/** One SAP write call (BAPI) with request/response payloads. */
export interface SAPTransaction {
  id: string;
  object_type: SAPObjectType | string;
  section: string;
  protocol: string;
  object_id: string;
  idempotency_key: string;
  status: SAPTransactionStatus | string;
  retry_count: number;
  max_retries: number;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown> | null;
  sap_document_number: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface SAPTransactionSummary {
  total: number;
  success: number;
  failed: number;
  pending: number;
  exhausted: number;
  last_created_at: string | null;
}

export interface SAPSyncItemResult {
  name: string;
  status: 'SUCCESS' | 'FAILED' | 'PARTIAL_SUCCESS' | string;
  started_at: string;
  finished_at: string;
  summary: Record<string, unknown>;
  error: string | null;
}

/** Central warehouse stock row synced from ZI_STOCK_KH08_CDS. */
export interface CentralStockItem {
  id: string;
  material: string;
  plant: string;
  storage_location: string;
  inventory_stock_type: string;
  material_code: string;
  material_name: string;
  inventory_stock_type_text: string;
  quantity: string | number;
  base_unit: string;
  stock_value: string | number;
  display_currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** OData read-sync run history entry. */
export interface SAPSyncRun {
  id: string;
  trigger_source: 'API' | 'CELERY' | 'JOB' | string;
  status: 'IN_PROGRESS' | 'SUCCESS' | 'FAILED' | 'PARTIAL_SUCCESS' | string;
  request_id: string;
  triggered_by: string | null;
  started_at: string;
  finished_at: string | null;
  summary: Record<string, unknown>;
  error: string | null;
  items: SAPSyncItemResult[];
}
