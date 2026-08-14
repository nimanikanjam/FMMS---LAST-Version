import type {
  AuthUser,
  CentralStockItem,
  Driver,
  DriverSummary,
  DriverVehicleAssignmentHistoryItem,
  ExternalWorkshopAssignment,
  Fault,
  FaultCatalog,
  FailureSeverity,
  Inspection,
  InspectionItemInput,
  InspectionTemplate,
  InspectionType,
  LoginResponse,
  OdometerReading,
  Paginated,
  RefreshTokenResponse,
  RepairOrder,
  SAPSyncRun,
  SAPTransaction,
  SAPTransactionSummary,
  Vehicle,
  VehicleDriverAssignmentHistory,
  VehicleHandover,
  VehicleSummary,
  VehicleStatus,
} from '../types/fmms';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'fmms_access_token';
const REFRESH_TOKEN_KEY = 'fmms_refresh_token';
const ACCESS_EXPIRES_AT_KEY = 'fmms_access_expires_at';
const REFRESH_EXPIRES_AT_KEY = 'fmms_refresh_expires_at';
const REFRESH_SKEW_MS = 60_000;

type ApiRequestInit = RequestInit & {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
};

let refreshPromise: Promise<string> | null = null;

export function getAccessToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function setAccessToken(token: string): void {
  if (token.trim()) localStorage.setItem(TOKEN_KEY, token.trim());
  else localStorage.removeItem(TOKEN_KEY);
}

export function setAccessTokenExpiresAt(expiresAt: string): void {
  if (expiresAt.trim()) localStorage.setItem(ACCESS_EXPIRES_AT_KEY, expiresAt.trim());
  else localStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
}

export function setRefreshToken(token: string): void {
  if (token.trim()) localStorage.setItem(REFRESH_TOKEN_KEY, token.trim());
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function setRefreshTokenExpiresAt(expiresAt: string): void {
  if (expiresAt.trim()) localStorage.setItem(REFRESH_EXPIRES_AT_KEY, expiresAt.trim());
  else localStorage.removeItem(REFRESH_EXPIRES_AT_KEY);
}

export function setAuthSession(response: LoginResponse): void {
  setAccessToken(response.access);
  setRefreshToken(response.refresh);
  setAccessTokenExpiresAt(response.access_expires_at);
  setRefreshTokenExpiresAt(response.refresh_expires_at);
}

export function clearAuthTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
  localStorage.removeItem(REFRESH_EXPIRES_AT_KEY);
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? '';
}

function isExpiredOrNear(expiresAt: string): boolean {
  const timestamp = Date.parse(expiresAt);
  if (Number.isNaN(timestamp)) return true;
  return timestamp - Date.now() <= REFRESH_SKEW_MS;
}

function shouldRefreshAccessToken(): boolean {
  const access = getAccessToken();
  const refresh = getRefreshToken();
  const refreshExpiresAt = localStorage.getItem(REFRESH_EXPIRES_AT_KEY) ?? '';
  if (!access || !refresh) return false;
  if (refreshExpiresAt && isExpiredOrNear(refreshExpiresAt)) {
    clearAuthTokens();
    return false;
  }
  const accessExpiresAt = localStorage.getItem(ACCESS_EXPIRES_AT_KEY) ?? '';
  return !accessExpiresAt || isExpiredOrNear(accessExpiresAt);
}

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const refresh = getRefreshToken();
  if (!refresh) {
    clearAuthTokens();
    throw new ApiError(401, 'نشست کاربری منقضی شده است.', null);
  }

  refreshPromise = fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
    .then(async (response) => {
      const text = await response.text();
      const data = parseResponseBody(text) as RefreshTokenResponse | null;
      if (!response.ok) {
        clearAuthTokens();
        const message = extractErrorMessage(response.status, data) || 'نشست کاربری منقضی شده است.';
        throw new ApiError(response.status, message, data);
      }
      if (!data || typeof data !== 'object' || !('access' in data)) {
        clearAuthTokens();
        throw new ApiError(response.status, 'پاسخ نامعتبر از سرور دریافت شد.', text);
      }
      const payload = data as RefreshTokenResponse;
      setAccessToken(payload.access);
      setAccessTokenExpiresAt(payload.access_expires_at);
      return payload.access;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function getValidAccessToken(): Promise<string> {
  if (shouldRefreshAccessToken()) {
    return refreshAccessToken();
  }
  return getAccessToken();
}

function parseResponseBody(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function extractErrorMessage(status: number, data: unknown): string {
  if (data && typeof data === 'object') {
    const payload = data as Record<string, unknown>;
    if (typeof payload.message === 'string' && payload.message.trim()) return payload.message;
    if (typeof payload.detail === 'string' && payload.detail.trim()) return payload.detail;
    if (Array.isArray(payload.messages) && typeof payload.messages[0] === 'string') {
      return payload.messages[0];
    }
    for (const value of Object.values(payload)) {
      if (typeof value === 'string' && value.trim()) return value;
      if (Array.isArray(value) && typeof value[0] === 'string' && value[0].trim()) {
        return value[0];
      }
    }
  }
  if (status >= 500) return 'خطای داخلی سرور. مقدار ورودی را بررسی کنید یا بعداً تلاش کنید.';
  return `خطای ${status} در ارتباط با سرور`;
}

async function request<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { auth = true, retryOnUnauthorized = true, ...fetchInit } = init;
  const token = auth ? await getValidAccessToken() : '';
  const headers = new Headers(init.headers);
  if (!(fetchInit.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchInit,
    headers,
  });
  const text = await response.text();
  const data = parseResponseBody(text);
  if (response.status === 401 && auth && retryOnUnauthorized && getRefreshToken()) {
    const refreshedToken = await refreshAccessToken();
    return request<T>(path, {
      ...fetchInit,
      headers: {
        ...Object.fromEntries(headers.entries()),
        Authorization: `Bearer ${refreshedToken}`,
      },
      auth,
      retryOnUnauthorized: false,
    });
  }
  if (!response.ok) {
    throw new ApiError(response.status, extractErrorMessage(response.status, data), data);
  }
  if (text && data === null) {
    throw new ApiError(response.status, 'پاسخ نامعتبر از سرور دریافت شد.', text);
  }
  return data as T;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResponse>('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
      auth: false,
    });
  },

  me() {
    return request<AuthUser>('/auth/me/');
  },

  getVehicleSummary() {
    return request<VehicleSummary>('/vehicles/summary/');
  },

  listVehicles(
    status?: VehicleStatus | '',
    ordering = '-created_at',
    options?: { page?: number; pageSize?: number; search?: string },
  ) {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (ordering) params.set('ordering', ordering);
    if (options?.search?.trim()) params.set('search', options.search.trim());
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Vehicle>>(`/vehicles/${query}`);
  },

  getVehicle(id: string) {
    return request<Vehicle>(`/vehicles/${id}/`);
  },

  updateVehicleStatus(id: string, status: VehicleStatus) {
    return request<Vehicle>(`/vehicles/${id}/status/`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
  },

  getOdometerHistory(vehicleId: string, options?: { fromDate?: string; toDate?: string }) {
    const params = new URLSearchParams();
    if (options?.fromDate) params.set('from_date', options.fromDate);
    if (options?.toDate) params.set('to_date', options.toDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<OdometerReading[]>(`/vehicles/${vehicleId}/odometer-history/${query}`);
  },

  getDriverAssignmentHistory(vehicleId: string, options?: { fromDate?: string; toDate?: string }) {
    const params = new URLSearchParams();
    if (options?.fromDate) params.set('from_date', options.fromDate);
    if (options?.toDate) params.set('to_date', options.toDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<VehicleDriverAssignmentHistory[]>(
      `/vehicles/${vehicleId}/driver-assignment-history/${query}`,
    );
  },

  recordOdometer(vehicleId: string, payload: { reading_date: string; odometer_km: number }) {
    return request<OdometerReading>(`/vehicles/${vehicleId}/odometer/`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, source: 'DRIVER' }),
    });
  },

  listFaults(
    vehicleId?: string,
    options?: { status?: string; page?: number; pageSize?: number },
  ) {
    const params = new URLSearchParams();
    if (vehicleId) params.set('vehicle_id', vehicleId);
    if (options?.status) params.set('status', options.status);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Fault>>(`/faults/${query}`);
  },

  getFault(id: string) {
    return request<Fault>(`/faults/${id}/`);
  },

  markFaultVehicleUsable(id: string, note = '') {
    return request<Fault>(`/faults/${id}/distribution-usable/`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  },

  markFaultVehicleUnusable(id: string, note = '') {
    return request<Fault>(`/faults/${id}/distribution-unusable/`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  },

  listFaultCatalogs(options?: {
    codeGroup?: string;
    defectClass?: string;
    search?: string;
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.codeGroup) params.set('code_group', options.codeGroup);
    if (options?.defectClass) params.set('defect_class', options.defectClass);
    if (options?.search?.trim()) params.set('search', options.search.trim());
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<FaultCatalog>>(`/fault-catalogs/${query}`);
  },

  reportFault(payload: {
    vehicle_id: string;
    code: string;
    description: string;
    severity: FailureSeverity;
    inspection_id?: string | null;
    items?: Array<{
      code: string;
      description: string;
      severity: FailureSeverity;
      component?: string;
    }>;
  }) {
    return request<Fault>('/faults/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listRepairOrders(options?: {
    vehicleId?: string;
    status?: string;
    workshopType?: string;
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.vehicleId) params.set('vehicle_id', options.vehicleId);
    if (options?.status) params.set('status', options.status);
    if (options?.workshopType) params.set('workshop_type', options.workshopType);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<RepairOrder>>(`/repair-orders/${query}`);
  },

  getRepairOrder(id: string) {
    return request<RepairOrder>(`/repair-orders/${id}/`);
  },

  approveRepairOrder(id: string, note?: string) {
    return request<{ id: string; status: string; message: string }>(
      `/repair-orders/${id}/approve/`,
      { method: 'POST', body: JSON.stringify({ note: note ?? '' }) },
    );
  },

  rejectRepairOrderByTransport(id: string, reason: string) {
    return request<{ id: string; status: string; message: string }>(
      `/repair-orders/${id}/transport-reject/`,
      { method: 'POST', body: JSON.stringify({ reason }) },
    );
  },

  assignRepairWorkshop(
    id: string,
    payload: { workshop_type: 'INTERNAL' | 'EXTERNAL'; workshop_id?: string; reason?: string },
  ) {
    return request<{
      id: string;
      status: string;
      message: string;
      workshop_type?: string | null;
    }>(`/repair-orders/${id}/assign-workshop/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  assignExternalWorkshop(
    id: string,
    payload: {
      workshop_id?: string;
      workshop_name?: string;
      workshop_address?: string;
      assignment_date: string;
      repair_reason?: string;
      description?: string;
    },
  ) {
    return request<ExternalWorkshopAssignment>(`/repair-orders/${id}/assign-external-workshop/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listExternalWorkshopAssignments(options?: { status?: string; page?: number; pageSize?: number }) {
    const params = new URLSearchParams();
    if (options?.status) params.set('status', options.status);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<ExternalWorkshopAssignment[] | Paginated<ExternalWorkshopAssignment>>(
      `/external-workshop-assignments/${query}`,
    );
  },

  getExternalWorkshopAssignment(id: string) {
    return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/`);
  },

  confirmExternalWorkshopDelivery(
    id: string,
    payload: {
      delivery_datetime: string;
      workshop_name: string;
      workshop_address: string;
      workshop_phone: string;
      vehicle_odometer: number;
      notes?: string;
    },
  ) {
    return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/confirm-delivery/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  confirmExternalWorkshopPickup(
    id: string,
    payload: { pickup_datetime: string; vehicle_odometer: number; notes?: string },
  ) {
    return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/confirm-pickup/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  reviewExternalRepair(
    id: string,
    payload: {
      invoice_file?: File | null;
      repair_services?: Array<Record<string, unknown>>;
      replaced_parts?: Array<Record<string, unknown>>;
      repair_cost?: string | number | null;
      additional_notes?: string;
    },
  ) {
    if (payload.invoice_file) {
      const formData = new FormData();
      formData.append('invoice_file', payload.invoice_file);
      formData.append('repair_services', JSON.stringify(payload.repair_services ?? []));
      formData.append('replaced_parts', JSON.stringify(payload.replaced_parts ?? []));
      if (payload.repair_cost !== undefined && payload.repair_cost !== null) {
        formData.append('repair_cost', String(payload.repair_cost));
      }
      formData.append('additional_notes', payload.additional_notes ?? '');
      return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/review/`, {
        method: 'POST',
        body: formData,
      });
    }
    return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/review/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  closeExternalRepair(id: string) {
    return request<ExternalWorkshopAssignment>(`/external-workshop-assignments/${id}/close/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  workshopTechnicalDecision(
    id: string,
    payload: { repairable: boolean; note?: string; estimated_delivery_at?: string },
  ) {
    return request<{ id: string; status: string; message: string }>(
      `/repair-orders/${id}/technical-decision/`,
      { method: 'POST', body: JSON.stringify(payload) },
    );
  },

  createRepairMaterialRequest(
    id: string,
    items: Array<{
      material_number: string;
      quantity: number;
      from_catalog?: boolean;
    }>,
  ) {
    return request(`/repair-orders/${id}/material-requests/`, {
      method: 'POST',
      body: JSON.stringify({ items }),
    });
  },

  receiveMaterialRequest(id: string) {
    return request(`/material-requests/${id}/receive/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  decideMaterialAvailability(
    id: string,
    payload: {
      note?: string;
      items: Array<{ item_id: string; decision: 'FROM_STOCK' | 'PURCHASE' }>;
    },
  ) {
    return request(`/material-requests/${id}/availability-decision/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  issuePurchasedMaterialRequest(id: string) {
    return request(`/material-requests/${id}/issue-purchased/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  listMaterialRequests(options?: { status?: string }) {
    const params = new URLSearchParams();
    if (options?.status) params.set('status', options.status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Array<Record<string, unknown>>>(`/material-requests/${query}`);
  },

  listCentralStock(options?: {
    plant?: string;
    storageLocation?: string;
    search?: string;
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.plant) params.set('plant', options.plant);
    if (options?.storageLocation) params.set('storage_location', options.storageLocation);
    if (options?.search) params.set('search', options.search);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<CentralStockItem[] | Paginated<CentralStockItem>>(`/central-stock/${query}`);
  },

  addRepairPart(
    id: string,
    payload: { material_number: string; quantity: number },
  ) {
    return request(`/repair-orders/${id}/parts/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateRepairPart(
    id: string,
    partId: string,
    payload: { material_number: string; quantity: number },
  ) {
    return request(`/repair-orders/${id}/parts/${partId}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteRepairPart(id: string, partId: string) {
    return request(`/repair-orders/${id}/parts/${partId}/`, {
      method: 'DELETE',
    });
  },

  addRepairActivity(
    id: string,
    payload: { description: string; labor_hours: string | number; notes?: string },
  ) {
    return request(`/repair-orders/${id}/activities/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateRepairActivity(
    id: string,
    activityId: string,
    payload: { description: string; labor_hours: string | number; notes?: string },
  ) {
    return request(`/repair-orders/${id}/activities/${activityId}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteRepairActivity(id: string, activityId: string) {
    return request(`/repair-orders/${id}/activities/${activityId}/`, {
      method: 'DELETE',
    });
  },

  completeRepairOrder(
    id: string,
    payload: { completed_at: string; no_parts_consumed?: boolean },
  ) {
    return request(`/repair-orders/${id}/complete/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  registerInternalRepairCost(
    id: string,
    payload: {
      invoice_number?: string;
      labor_cost?: number;
      parts_cost?: number;
      service_cost?: number;
      currency?: string;
      notes?: string;
    },
  ) {
    return request(`/repair-orders/${id}/internal-cost/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  transportHandoverApprove(id: string) {
    return request(`/repair-orders/${id}/transport-handover-approve/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  transportHandoverReject(id: string, comment?: string) {
    return request(`/repair-orders/${id}/transport-handover-reject/`, {
      method: 'POST',
      body: JSON.stringify({ comment: comment ?? '' }),
    });
  },

  listVehicleComponentHistory(vehicleId: string) {
    return request<Array<Record<string, unknown>> | Paginated<Record<string, unknown>>>(
      `/vehicles/${vehicleId}/component-history/`,
    );
  },

  getRepairOrderTimeline(id: string) {
    return request<Array<{ event_type: string; description: string; created_at: string }>>(
      `/repair-orders/${id}/timeline/`,
    );
  },

  listVehicleHandovers() {
    return request<VehicleHandover[] | Paginated<VehicleHandover>>('/vehicle-handovers/');
  },

  confirmVehicleHandover(
    id: string,
    payload: { accepted: boolean; comment?: string },
  ) {
    return request<VehicleHandover>(`/vehicle-handovers/${id}/confirm/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listDrivers(options?: {
    status?: string;
    ordering?: string;
    search?: string;
    role?: 'DRIVER' | 'ASSISTANT' | '';
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.status) params.set('status', options.status);
    if (options?.ordering) params.set('ordering', options.ordering);
    if (options?.search?.trim()) params.set('search', options.search.trim());
    if (options?.role) params.set('role', options.role);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Driver>>(`/drivers/${query}`);
  },

  getDriver(id: string) {
    return request<Driver>(`/drivers/${id}/`);
  },

  getDriverSummary() {
    return request<DriverSummary>('/drivers/summary/');
  },

  driverExitCenter(driverId: string, payload: { vehicle_id: string; inspection_id: string }) {
    return request<Vehicle>(`/drivers/${driverId}/exit-center/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getDriverVehicleAssignmentHistory(
    driverId: string,
    options?: { fromDate?: string; toDate?: string },
  ) {
    const params = new URLSearchParams();
    if (options?.fromDate) params.set('from_date', options.fromDate);
    if (options?.toDate) params.set('to_date', options.toDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<DriverVehicleAssignmentHistoryItem[]>(
      `/drivers/${driverId}/vehicle-assignment-history/${query}`,
    );
  },

  listInspectionTemplates() {
    return request<Paginated<InspectionTemplate> | InspectionTemplate[]>(
      '/inspection-templates/',
    );
  },

  listVehicleChecklists(
    vehicleId: string,
    options?: { fromDate?: string; toDate?: string; page?: number; pageSize?: number },
  ) {
    const params = new URLSearchParams();
    if (options?.fromDate) params.set('from_date', options.fromDate);
    if (options?.toDate) params.set('to_date', options.toDate);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Inspection> | Inspection[]>(
      `/vehicles/${vehicleId}/checklists/${query}`,
    );
  },

  getVehicleChecklist(vehicleId: string, inspectionId: string) {
    return request<Inspection>(`/vehicles/${vehicleId}/checklists/${inspectionId}/`);
  },

  listInspections(options?: {
    vehicleId?: string;
    fromDate?: string;
    toDate?: string;
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.vehicleId) params.set('vehicle_id', options.vehicleId);
    if (options?.fromDate) params.set('from_date', options.fromDate);
    if (options?.toDate) params.set('to_date', options.toDate);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Inspection> | Inspection[]>(`/inspections/${query}`);
  },

  getInspection(id: string) {
    return request<Inspection>(`/inspections/${id}/`);
  },

  createInspection(payload: {
    vehicle_id: string;
    inspection_type: InspectionType;
    odometer_value: number;
    odometer_unit: 'KM' | 'MILES';
    inspected_at: string;
    driver_id?: string | null;
    items?: InspectionItemInput[];
  }) {
    return request<Inspection>('/inspections/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  submitInspection(id: string) {
    return request<Inspection>(`/inspections/${id}/submit/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  reportInspectionFault(id: string) {
    return request<Fault>(`/inspections/${id}/report-fault/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  },

  listSapTransactions(options?: {
    status?: string;
    objectType?: string;
    page?: number;
    pageSize?: number;
  }) {
    const params = new URLSearchParams();
    if (options?.status) params.set('status', options.status);
    if (options?.objectType) params.set('object_type', options.objectType);
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<SAPTransaction>>(`/sap-transactions/${query}`);
  },

  getSapTransaction(id: string) {
    return request<SAPTransaction>(`/sap-transactions/${id}/`);
  },

  getSapTransactionSummary() {
    return request<SAPTransactionSummary>('/sap-transactions/summary/');
  },

  listSapSyncHistory(options?: { page?: number; pageSize?: number }) {
    const params = new URLSearchParams();
    if (options?.page) params.set('page', String(options.page));
    if (options?.pageSize) params.set('page_size', String(options.pageSize));
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<SAPSyncRun>>(`/sap-sync/history/${query}`);
  },

  /** Trigger the global SAP OData read sync (ADMIN only). */
  runSapSync() {
    return request<SAPSyncRun>('/sap-sync/', { method: 'POST', body: '{}' });
  },

  setAccessToken,
  setRefreshToken,
  setAuthSession,
  getAccessToken,
  clearAuthTokens,
};
