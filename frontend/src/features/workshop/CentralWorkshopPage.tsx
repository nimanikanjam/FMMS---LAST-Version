import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Cancel,
  CheckCircleOutline,
  DeleteOutline,
  DoNotDisturbAlt,
  Edit,
} from '@mui/icons-material';
import { Build, Inventory2 } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { JalaliDateTimeField } from '../../components/JalaliDateTimeField';
import { KpiCard } from '../../components/KpiCard';
import {
  EMPTY_MATERIAL_PICK,
  MaterialStockPicker,
  type MaterialPickValue,
} from '../../components/MaterialStockPicker';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlAutocomplete } from '../../components/RtlAutocomplete';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type {
  Fault,
  RepairActivityOption,
  RepairOrder,
  Vehicle,
} from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

type PartLineDraft = {
  key: string;
  materialNumber: string;
  quantity: number;
  fromCatalog: boolean;
  materialName: string;
  availableQuantity: string;
};

function draftFromPick(part: MaterialPickValue, quantity: number): PartLineDraft {
  return {
    key: `${part.materialNumber}-${Date.now()}`,
    materialNumber: part.materialNumber.trim(),
    quantity,
    fromCatalog: part.fromCatalog,
    materialName: part.materialName,
    availableQuantity: part.availableQuantity || '0',
  };
}

function lineChipLabel(line: PartLineDraft): string {
  const name = line.materialName ? ` · ${line.materialName}` : '';
  const stock = line.fromCatalog
    ? ` · موجودی ${toFaNumber(line.availableQuantity || '0')}`
    : ' · خارج از انبار';
  return `${line.materialNumber}${name}${stock} · تعداد ${toFaNumber(line.quantity)}`;
}

const REPAIR_STATUS_LABELS: Record<string, string> = {
  WORKSHOP_ASSIGNED: 'صف تعمیرگاه مرکزی',
  WAITING_WORKSHOP_CONFIRMATION: 'در انتظار تصمیم فنی',
  IN_PROGRESS: 'در حال تعمیر',
  WAITING_PARTS: 'در انتظار قطعات',
  NO_REPAIR_NEEDED: 'عدم نیاز به تعمیر',
  WAITING_DRIVER_CONFIRMATION: 'منتظر تایید راننده',
  COMPLETED: 'تکمیل شده',
};

const MATERIAL_REQUEST_STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'در انتظار بررسی ترابری',
  WAITING_STOCK: 'منتظر موجودی/خرید',
  PURCHASE_REQUIRED: 'نیاز به خرید',
  PARTIALLY_ISSUED: 'تخصیص جزئی — منتظر خرید',
  STOCK_ISSUED: 'ارسال‌شده به تعمیرگاه',
  RECEIVED: 'دریافت‌شده در تعمیرگاه',
};

const MATERIAL_DECISION_LABELS: Record<string, string> = {
  FROM_STOCK: 'از انبار مرکزی',
  PURCHASE: 'خرید از بیرون',
  PENDING: 'ثبت‌نشده',
};

const MATERIAL_ITEM_STATUS_LABELS: Record<string, string> = {
  PENDING: 'در انتظار تصمیم',
  STOCK_ISSUED: 'ارسال‌شده از انبار',
  PURCHASE_REQUIRED: 'نیاز به خرید',
  RECEIVED: 'دریافت‌شده',
};

type StatusFilter =
  | ''
  | 'WORKSHOP_ASSIGNED'
  | 'IN_PROGRESS'
  | 'WAITING_PARTS'
  | 'NO_REPAIR_NEEDED';

const STATUS_TAB_OPTIONS: ReadonlyArray<StatusTabOption<Exclude<StatusFilter, ''>>> = [
  { value: '', label: 'همه' },
  { value: 'WORKSHOP_ASSIGNED', label: 'صف تصمیم فنی' },
  { value: 'IN_PROGRESS', label: 'در حال تعمیر' },
  { value: 'WAITING_PARTS', label: 'در انتظار قطعات' },
  { value: 'NO_REPAIR_NEEDED', label: 'عدم نیاز به تعمیر' },
];

type DetailState = {
  order: RepairOrder;
  fault: Fault | null;
  vehicle: Vehicle | null;
  history: RepairOrder[];
  timeline: Array<{ event_type: string; description: string; created_at: string }>;
  materialRequests: MaterialRequestSummary[];
};

type MaterialRequestItemSummary = {
  id: string;
  material_number: string;
  quantity: string | number;
  from_catalog?: boolean;
  decision?: string;
  item_status?: string;
  material_name?: string;
  available_quantity?: string | number;
  in_catalog?: boolean;
};

type MaterialRequestSummary = {
  id: string;
  repair_order_id: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  items?: MaterialRequestItemSummary[];
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function statusLabel(status: string): string {
  return REPAIR_STATUS_LABELS[status] ?? status;
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'IN_PROGRESS' || status === 'COMPLETED') return 'success';
  if (status === 'WAITING_PARTS' || status === 'WORKSHOP_ASSIGNED') return 'warning';
  if (status === 'NO_REPAIR_NEEDED') return 'neutral';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | null | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Central workshop inbox for technical inspection and parts handling.
 */
export function CentralWorkshopPage() {
  const canEdit = useCanEdit();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [items, setItems] = useState<RepairOrder[]>([]);
  const [vehicles, setVehicles] = useState<Map<string, Vehicle>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusTab, setStatusTab] = useState<StatusFilter>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const status = statusTab || statusFilter;
  const [kpiCounts, setKpiCounts] = useState({
    queue: 0,
    inProgress: 0,
    waitingParts: 0,
  });
  const [selected, setSelected] = useState<RepairOrder | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [decisionNote, setDecisionNote] = useState('');
  const [estimatedDeliveryAt, setEstimatedDeliveryAt] = useState('');
  const [requestPart, setRequestPart] = useState<MaterialPickValue>(EMPTY_MATERIAL_PICK);
  const [requestQty, setRequestQty] = useState('1');
  const [requestLines, setRequestLines] = useState<PartLineDraft[]>([]);
  const [consumedPart, setConsumedPart] = useState<MaterialPickValue>(EMPTY_MATERIAL_PICK);
  const [consumedQty, setConsumedQty] = useState('1');
  const [consumedLines, setConsumedLines] = useState<PartLineDraft[]>([]);
  const [activityOption, setActivityOption] = useState<RepairActivityOption | null>(
    null,
  );
  const [activityOptions, setActivityOptions] = useState<RepairActivityOption[]>([]);
  const [activityOptionsLoading, setActivityOptionsLoading] = useState(false);
  const [activityHours, setActivityHours] = useState('');
  const [activityNotes, setActivityNotes] = useState('');
  const [editingActivityId, setEditingActivityId] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const statuses: string[] = status
        ? [status]
        : ['WORKSHOP_ASSIGNED', 'IN_PROGRESS', 'WAITING_PARTS', 'NO_REPAIR_NEEDED'];
      const pages = await Promise.all(
        statuses.map((itemStatus) =>
          api.listRepairOrders({
            status: itemStatus,
            workshopType: 'INTERNAL',
            page: 1,
            pageSize: 100,
          }),
        ),
      );
      const list = pages.flatMap((page) => normalizePaginated(page));
      list.sort((a, b) => String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? '')));
      setItems(list);

      const vehicleIds = [...new Set(list.map((item) => item.vehicle_id))];
      const vehicleResults = await Promise.all(
        vehicleIds.map(async (id) => {
          try {
            return await api.getVehicle(id);
          } catch {
            return null;
          }
        }),
      );
      const nextVehicles = new Map<string, Vehicle>();
      vehicleResults.forEach((vehicle) => {
        if (vehicle) nextVehicles.set(vehicle.id, vehicle);
      });
      setVehicles(nextVehicles);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : 'دریافت کارتابل تعمیرگاه انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  // SAP's activity catalog is small and order-independent, so it is fetched
  // once for the page rather than per repair order.
  useEffect(() => {
    let cancelled = false;
    setActivityOptionsLoading(true);
    api
      .listRepairActivityOptions()
      .then((page) => {
        if (cancelled) return;
        setActivityOptions(Array.isArray(page) ? page : (page.results ?? []));
      })
      .catch(() => {
        if (!cancelled) setActivityOptions([]);
      })
      .finally(() => {
        if (!cancelled) setActivityOptionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshKpis = useCallback(async () => {
    try {
      const statuses = [
        'WORKSHOP_ASSIGNED',
        'IN_PROGRESS',
        'WAITING_PARTS',
        'NO_REPAIR_NEEDED',
      ] as const;
      const pages = await Promise.all(
        statuses.map((itemStatus) =>
          api.listRepairOrders({
            status: itemStatus,
            workshopType: 'INTERNAL',
            page: 1,
            pageSize: 100,
          }),
        ),
      );
      const list = pages.flatMap((page) => normalizePaginated(page));
      setKpiCounts({
        queue: list.filter((item) => item.status === 'WORKSHOP_ASSIGNED').length,
        inProgress: list.filter((item) => item.status === 'IN_PROGRESS').length,
        waitingParts: list.filter((item) => item.status === 'WAITING_PARTS').length,
      });
    } catch {
      // Keep last KPI snapshot; list error is handled separately.
    }
  }, []);

  useEffect(() => {
    void refreshKpis();
  }, [refreshKpis]);

  const openDetail = async (row: RepairOrder) => {
    setSelected(row);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setSuccess('');
    setDecisionNote('');
    setEstimatedDeliveryAt('');
    setActivityOption(null);
    setActivityHours('');
    setActivityNotes('');
    setEditingActivityId('');
    setDetailLoading(true);
    try {
      const [order, fault, vehicle, history, timeline, materials] = await Promise.all([
        api.getRepairOrder(row.id),
        api.getFault(row.fault_id).catch(() => null),
        api.getVehicle(row.vehicle_id).catch(() => null),
        api
          .listRepairOrders({ vehicleId: row.vehicle_id, page: 1, pageSize: 20 })
          .then(normalizePaginated)
          .catch(() => [] as RepairOrder[]),
        api.getRepairOrderTimeline(row.id).catch(() => []),
        api
          .listMaterialRequests()
          .then((payload) => payload as MaterialRequestSummary[])
          .catch(() => [] as MaterialRequestSummary[]),
      ]);
      setDetail({
        order,
        fault,
        vehicle,
        history: history.filter((item) => item.id !== order.id),
        timeline,
        materialRequests: materials.filter(
          (item) => String(item.repair_order_id) === order.id,
        ),
      });
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const decide = async (repairable: boolean) => {
    if (!selected) return;
    if (repairable && !estimatedDeliveryAt) {
      setActionError('تاریخ تحویل تخمینی الزامی است.');
      return;
    }
    setActionLoading(repairable ? 'repairable' : 'no-repair');
    setActionError('');
    try {
      const result = await api.workshopTechnicalDecision(selected.id, {
        repairable,
        note: decisionNote,
        estimated_delivery_at: repairable
          ? new Date(estimatedDeliveryAt).toISOString()
          : undefined,
      });
      setSuccess(result.message);
      await Promise.all([load(), refreshKpis()]);
      await openDetail({ ...selected, status: result.status });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تصمیم انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const addRequestLine = () => {
    if (!requestPart.materialNumber.trim()) return;
    const quantity = Math.max(1, Number(requestQty) || 1);
    setRequestLines((prev) => [...prev, draftFromPick(requestPart, quantity)]);
    setRequestPart(EMPTY_MATERIAL_PICK);
    setRequestQty('1');
  };

  const requestParts = async () => {
    if (!selected) return;
    if (requestLines.length === 0) return;
    setActionLoading('parts');
    setActionError('');
    try {
      await api.createRepairMaterialRequest(
        selected.id,
        requestLines.map((line) => ({
          material_number: line.materialNumber,
          quantity: line.quantity,
          from_catalog: line.fromCatalog,
        })),
      );
      setSuccess('درخواست قطعه ثبت شد و سفارش در انتظار قطعات قرار گرفت.');
      setRequestPart(EMPTY_MATERIAL_PICK);
      setRequestQty('1');
      setRequestLines([]);
      await Promise.all([load(), refreshKpis()]);
      await openDetail(selected);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت درخواست قطعه انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const receiveParts = async (materialRequestId: string) => {
    if (!selected) return;
    setActionLoading(`receive-${materialRequestId}`);
    setActionError('');
    try {
      await api.receiveMaterialRequest(materialRequestId);
      setSuccess('دریافت قطعات ثبت شد؛ تعمیر ادامه می‌یابد.');
      await Promise.all([load(), refreshKpis()]);
      await openDetail(selected);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت دریافت قطعات انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const addConsumedLine = () => {
    if (!consumedPart.materialNumber.trim()) return;
    const quantity = Math.max(1, Number(consumedQty) || 1);
    setConsumedLines((prev) => [...prev, draftFromPick(consumedPart, quantity)]);
    setConsumedPart(EMPTY_MATERIAL_PICK);
    setConsumedQty('1');
  };

  const recordConsumedPart = async () => {
    if (!selected) return;
    if (consumedLines.length === 0) return;
    setActionLoading('consumed');
    setActionError('');
    try {
      for (const line of consumedLines) {
        await api.addRepairPart(selected.id, {
          material_number: line.materialNumber,
          quantity: line.quantity,
        });
      }
      setConsumedPart(EMPTY_MATERIAL_PICK);
      setConsumedQty('1');
      setConsumedLines([]);
      await openDetail(selected);
      setSuccess('قطعه مصرفی ثبت شد (جدا از درخواست قطعه).');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت قطعه مصرفی انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const recordActivity = async () => {
    if (!selected) return;
    const hours = Number(activityHours);
    if (!activityOption || !Number.isFinite(hours) || hours <= 0) return;
    setActionLoading('activity');
    setActionError('');
    try {
      const payload = {
        activity_code: activityOption.code,
        activity_code_group: activityOption.code_group,
        labor_hours: activityHours,
        notes: activityNotes.trim() || undefined,
      };
      if (editingActivityId) {
        await api.updateRepairActivity(selected.id, editingActivityId, payload);
      } else {
        await api.addRepairActivity(selected.id, payload);
      }
      setActivityOption(null);
      setActivityHours('');
      setActivityNotes('');
      setEditingActivityId('');
      await openDetail(selected);
      setSuccess(
        editingActivityId ? 'فعالیت تعمیرگاه ویرایش شد.' : 'فعالیت تعمیرگاه ثبت شد.',
      );
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'ثبت/ویرایش فعالیت تعمیرگاه انجام نشد',
      );
    } finally {
      setActionLoading('');
    }
  };

  const startEditActivity = (activity: NonNullable<RepairOrder['activities']>[number]) => {
    setEditingActivityId(activity.id);
    setActivityOption(
      activityOptions.find((option) => option.code === activity.activity_code) ?? null,
    );
    setActivityHours(String(activity.labor_hours));
    setActivityNotes(activity.notes || '');
    setActionError('');
  };

  const cancelEditActivity = () => {
    setEditingActivityId('');
    setActivityOption(null);
    setActivityHours('');
    setActivityNotes('');
  };

  const deleteActivity = async (activityId: string) => {
    if (!selected) return;
    if (!window.confirm('این فعالیت حذف شود؟')) return;
    setActionLoading(`delete-activity-${activityId}`);
    setActionError('');
    try {
      await api.deleteRepairActivity(selected.id, activityId);
      if (editingActivityId === activityId) cancelEditActivity();
      await openDetail(selected);
      setSuccess('فعالیت تعمیرگاه حذف شد.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'حذف فعالیت تعمیرگاه انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const completeRepair = async (noPartsConsumed = false) => {
    if (!selected) return;
    setActionLoading(noPartsConsumed ? 'complete-empty' : 'complete');
    setActionError('');
    try {
      await api.completeRepairOrder(selected.id, {
        completed_at: new Date().toISOString(),
        no_parts_consumed: noPartsConsumed,
      });
      setSuccess('تعمیر تکمیل شد و برای تایید راننده ارسال شد.');
      setSelected(null);
      await Promise.all([load(), refreshKpis()]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'تکمیل تعمیر انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const queueCount = kpiCounts.queue;
  const inProgressCount = kpiCounts.inProgress;
  const waitingPartsCount = kpiCounts.waitingParts;

  const columns: Array<RtlDataTableColumn<RepairOrder, string>> = useMemo(
    () => [
      {
        key: 'plate',
        label: 'پلاک',
        render: (row) => (
          <Typography fontWeight={800}>
            {vehiclePlate(vehicles.get(row.vehicle_id), row.vehicle_id)}
          </Typography>
        ),
      },
      {
        key: 'status',
        label: 'وضعیت',
        render: (row) => (
          <PlainStatusBadge label={statusLabel(row.status)} tone={statusTone(row.status)} />
        ),
      },
      {
        key: 'sap',
        label: 'PM Order',
        render: (row) => row.sap_order_number || '—',
      },
      {
        key: 'updated',
        label: 'به‌روزرسانی',
        render: (row) => formatDateTime(row.updated_at),
      },
      {
        key: 'actions',
        label: 'عملیات',
        align: 'center',
        render: (row) => (
          <Button
            size="small"
            variant="outlined"
            onClick={() => void openDetail(row)}
            sx={{ height: 36, minHeight: 36, px: 1.5 }}
          >
            بررسی
          </Button>
        ),
      },
    ],
    [vehicles],
  );

  const canDecide =
    canEdit &&
    (detail?.order.status === 'WORKSHOP_ASSIGNED' ||
      detail?.order.status === 'WAITING_WORKSHOP_CONFIRMATION');
  const canRequestParts = canEdit && detail?.order.status === 'IN_PROGRESS';
  const canReceiveParts = canEdit && detail?.order.status === 'WAITING_PARTS';
  const canCompleteRepair = canEdit && detail?.order.status === 'IN_PROGRESS';
  const canRecordConsumed = canEdit && detail?.order.status === 'IN_PROGRESS';
  const canRecordActivity = canEdit && detail?.order.status === 'IN_PROGRESS';
  const canSubmitConsumed = consumedLines.length > 0;
  const canSubmitActivity =
    activityOption !== null &&
    Number.isFinite(Number(activityHours)) &&
    Number(activityHours) > 0;

  const tabs = detail
    ? [
        {
          label: 'تصمیم فنی',
          content: (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <DetailLine
                    label="پلاک"
                    value={vehiclePlate(detail.vehicle, detail.order.vehicle_id)}
                  />
                  <DetailLine
                    label="وضعیت خودرو"
                    value={
                      detail.vehicle ? (
                        <VehicleStatusBadge status={detail.vehicle.status} />
                      ) : (
                        '—'
                      )
                    }
                  />
                  <DetailLine label="علت خرابی" value={detail.fault?.description || '—'} />
                  <DetailLine
                    label="شرح راننده"
                    value={detail.fault?.description || '—'}
                  />
                  <DetailLine
                    label="یادداشت تعمیرگاه"
                    value={detail.order.workshop_decision_note || '—'}
                  />
                  <DetailLine
                    label="تاریخ تحویل تخمینی"
                    value={
                      detail.order.estimated_delivery_at
                        ? new Date(detail.order.estimated_delivery_at).toLocaleString('fa-IR')
                        : '—'
                    }
                  />
                  <DetailLine
                    label="PM Order"
                    value={detail.order.sap_order_number || 'هنوز ایجاد نشده'}
                  />
                  <DetailLine
                    label="وضعیت سفارش"
                    value={statusLabel(detail.order.status)}
                  />
                </CardContent>
              </Card>

              {success && <Alert severity="success">{success}</Alert>}
              {actionError && <Alert severity="error">{actionError}</Alert>}

              {canDecide && (
                <>
                  <RtlTextField
                    fullWidth
                    label="یادداشت تصمیم فنی"
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                  />
                  <JalaliDateTimeField
                    fullWidth
                    label="تاریخ تحویل تخمینی"
                    value={estimatedDeliveryAt}
                    onChange={setEstimatedDeliveryAt}
                  />
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap>
                    <Button
                      color="success"
                      variant="contained"
                      startIcon={<CheckCircleOutline />}
                      loading={actionLoading === 'repairable'}
                      disabled={!estimatedDeliveryAt}
                      onClick={() => void decide(true)}
                    >
                      نیاز به تعمیر دارد
                    </Button>
                    <Button
                      color="inherit"
                      variant="outlined"
                      startIcon={<DoNotDisturbAlt />}
                      loading={actionLoading === 'no-repair'}
                      onClick={() => void decide(false)}
                    >
                      عدم نیاز به تعمیر
                    </Button>
                  </Stack>
                </>
              )}

              {canCompleteRepair && (
                <Button
                  fullWidth
                  size="large"
                  color="success"
                  variant="contained"
                  loading={actionLoading === 'complete'}
                  onClick={() => void completeRepair(false)}
                  sx={{ minHeight: 52, fontWeight: 900 }}
                >
                  تکمیل تعمیر
                </Button>
              )}
            </Stack>
          ),
        },
        {
          label: 'فعالیت‌ها',
          content: (
            <Stack spacing={2}>
              {canRecordActivity ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={700} mb={1.5}>
                      {editingActivityId ? 'ویرایش فعالیت' : 'ثبت فعالیت'}
                    </Typography>
                    <Stack spacing={1.5}>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1}
                        useFlexGap
                        alignItems="flex-start"
                      >
                        <RtlAutocomplete
                          label="شرح فعالیت"
                          options={activityOptions}
                          loading={activityOptionsLoading}
                          value={activityOption}
                          onChange={(_, next) => setActivityOption(next)}
                          getOptionLabel={(option) => option.code_text}
                          isOptionEqualToValue={(option, val) => option.id === val.id}
                          noOptionsText="موردی یافت نشد"
                          size="small"
                          sx={{ flex: 1, minWidth: { xs: '100%', sm: 280 } }}
                        />
                        <RtlTextField
                          label="ساعت"
                          value={activityHours}
                          onChange={(event) => setActivityHours(event.target.value)}
                          size="small"
                          type="number"
                          inputProps={{ min: 0.25, step: 0.25 }}
                          sx={{ width: { xs: '100%', sm: 110 } }}
                        />
                        <Button
                          variant="contained"
                          loading={actionLoading === 'activity'}
                          disabled={!canSubmitActivity}
                          onClick={() => void recordActivity()}
                          sx={{ mt: { sm: 0.5 }, whiteSpace: 'nowrap' }}
                        >
                          {editingActivityId ? 'ثبت ویرایش' : 'ثبت فعالیت'}
                        </Button>
                        {editingActivityId ? (
                          <Button
                            variant="outlined"
                            color="inherit"
                            startIcon={<Cancel />}
                            onClick={cancelEditActivity}
                            sx={{ mt: { sm: 0.5 }, whiteSpace: 'nowrap' }}
                          >
                            انصراف
                          </Button>
                        ) : null}
                      </Stack>
                      <RtlTextField
                        fullWidth
                        label="یادداشت"
                        value={activityNotes}
                        onChange={(event) => setActivityNotes(event.target.value)}
                        size="small"
                        multiline
                        minRows={2}
                      />
                    </Stack>
                  </CardContent>
                </Card>
              ) : null}

              {detail.order.activities && detail.order.activities.length > 0 ? (
                <Stack spacing={1}>
                  {detail.order.activities.map((activity) => {
                    const editing = editingActivityId === activity.id;
                    return (
                      <Box
                        key={activity.id}
                        sx={{
                          border: '1px solid',
                          borderColor: editing ? 'primary.main' : 'divider',
                          borderRadius: 1,
                          px: 1.5,
                          py: 1,
                          bgcolor: editing
                            ? 'rgba(25, 118, 210, 0.06)'
                            : 'background.paper',
                        }}
                      >
                        <Stack
                          direction={{ xs: 'column', sm: 'row' }}
                          justifyContent="space-between"
                          gap={1}
                        >
                          <Box>
                            <Typography fontWeight={800}>
                              {activity.description}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {toFaNumber(activity.labor_hours)} ساعت ·{' '}
                              {formatDateTime(activity.performed_at)}
                            </Typography>
                            {activity.notes ? (
                              <Typography variant="body2" color="text.secondary" mt={0.5}>
                                {activity.notes}
                              </Typography>
                            ) : null}
                          </Box>
                          {canRecordActivity ? (
                            <Stack
                              direction={{ xs: 'column', sm: 'row' }}
                              spacing={1}
                              sx={{ alignSelf: { xs: 'stretch', sm: 'flex-start' } }}
                            >
                              <Button
                                size="small"
                                variant={editing ? 'contained' : 'outlined'}
                                startIcon={<Edit />}
                                onClick={() => startEditActivity(activity)}
                              >
                                ویرایش
                              </Button>
                              <Button
                                size="small"
                                variant="outlined"
                                color="error"
                                startIcon={<DeleteOutline />}
                                loading={actionLoading === `delete-activity-${activity.id}`}
                                onClick={() => void deleteActivity(activity.id)}
                              >
                                حذف
                              </Button>
                            </Stack>
                          ) : null}
                        </Stack>
                      </Box>
                    );
                  })}
                </Stack>
              ) : canRecordActivity ? null : (
                <EmptyState title="فعالیتی ثبت نشده است" />
              )}
            </Stack>
          ),
        },
        {
          label: 'درخواست و دریافت قطعات',
          content: (
            <Stack spacing={2}>
              {canRequestParts ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={700} mb={1.5}>
                      درخواست قطعه
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={1.5}>
                      برای هر قطعه تعداد جداگانه وارد کنید؛ سپس به لیست اضافه کرده و درخواست را ثبت کنید.
                    </Typography>
                    <Stack spacing={1.5}>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1}
                        useFlexGap
                        alignItems="flex-start"
                      >
                        <MaterialStockPicker
                          label="قطعه درخواستی"
                          value={requestPart}
                          onChange={setRequestPart}
                          showSelectedChip={false}
                        />
                        <RtlTextField
                          label="تعداد"
                          value={requestQty}
                          onChange={(event) => setRequestQty(event.target.value)}
                          size="small"
                          type="number"
                          inputProps={{ min: 1 }}
                          sx={{ width: { xs: '100%', sm: 110 } }}
                        />
                        <Button
                          variant="outlined"
                          disabled={!requestPart.materialNumber.trim()}
                          onClick={addRequestLine}
                          sx={{ mt: { sm: 0.5 } }}
                        >
                          افزودن به لیست
                        </Button>
                      </Stack>
                      {requestLines.length > 0 ? (
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                          {requestLines.map((line) => (
                            <Chip
                              key={line.key}
                              color={line.fromCatalog ? 'default' : 'warning'}
                              variant="outlined"
                              label={lineChipLabel(line)}
                              onDelete={() =>
                                setRequestLines((prev) =>
                                  prev.filter((item) => item.key !== line.key),
                                )
                              }
                            />
                          ))}
                        </Stack>
                      ) : null}
                      <Stack
                        direction="row"
                        justifyContent="flex-end"
                        sx={{
                          pt: 1,
                          borderTop: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Button
                          variant="contained"
                          startIcon={<Inventory2 />}
                          loading={actionLoading === 'parts'}
                          disabled={requestLines.length === 0}
                          onClick={() => void requestParts()}
                        >
                          ثبت درخواست
                        </Button>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              ) : null}

              {detail.materialRequests.length === 0 ? (
                canRequestParts ? null : (
                  <EmptyState title="درخواست قطعه‌ای برای این تعمیر ثبت نشده است" />
                )
              ) : (
                <Stack spacing={1}>
                  {detail.materialRequests.map((request) => {
                const readyToReceive =
                  canReceiveParts && request.status === 'STOCK_ISSUED';
                const received = request.status === 'RECEIVED';
                return (
                  <Card
                    key={String(request.id)}
                    variant="outlined"
                    sx={{
                      borderRight: '4px solid',
                      borderRightColor: readyToReceive
                        ? 'warning.main'
                        : received
                          ? 'success.main'
                          : 'divider',
                      borderColor: readyToReceive
                        ? 'warning.main'
                        : received
                          ? 'success.light'
                          : 'divider',
                      bgcolor: readyToReceive
                        ? 'rgba(237, 108, 2, 0.08)'
                        : received
                          ? 'rgba(46, 125, 50, 0.06)'
                          : 'background.paper',
                      boxShadow: readyToReceive
                        ? '0 6px 18px rgba(160, 104, 0, 0.12)'
                        : 'none',
                    }}
                  >
                    <CardContent>
                      <Stack spacing={1.5}>
                        <Stack
                          direction={{ xs: 'column', sm: 'row' }}
                          justifyContent="space-between"
                          alignItems={{ xs: 'stretch', sm: 'center' }}
                          gap={1}
                        >
                          <Stack direction="row" spacing={1} alignItems="flex-start">
                            {received ? (
                              <CheckCircleOutline color="success" sx={{ mt: 0.25 }} />
                            ) : null}
                            <Box>
                              <Typography fontWeight={800}>
                                درخواست {String(request.id).slice(0, 8)}
                              </Typography>
                              <Typography
                                variant="body2"
                                color={readyToReceive ? 'warning.dark' : 'text.secondary'}
                                fontWeight={readyToReceive ? 800 : 500}
                              >
                                {readyToReceive
                                  ? 'آماده ثبت دریافت فیزیکی'
                                  : `وضعیت: ${
                                      MATERIAL_REQUEST_STATUS_LABELS[request.status] ??
                                      request.status
                                    }`}
                              </Typography>
                              {request.updated_at ? (
                                <Typography variant="body2" color="text.secondary">
                                  آخرین به‌روزرسانی:{' '}
                                  {formatDateTime(request.updated_at)}
                                </Typography>
                              ) : null}
                            </Box>
                          </Stack>
                          {readyToReceive ? (
                            <Button
                              size="small"
                              variant="contained"
                              color="warning"
                              loading={actionLoading === `receive-${String(request.id)}`}
                              onClick={() => void receiveParts(String(request.id))}
                            >
                              ثبت دریافت فیزیکی
                            </Button>
                          ) : (
                            <Chip
                              size="small"
                              variant={received ? 'filled' : 'outlined'}
                              color={received ? 'success' : 'default'}
                              label={
                                received
                                  ? 'دریافت فیزیکی ثبت شده'
                                  : MATERIAL_REQUEST_STATUS_LABELS[request.status] ??
                                    request.status
                              }
                            />
                          )}
                        </Stack>

                        <Stack spacing={1}>
                          {(request.items ?? []).length === 0 ? (
                            <Alert severity="info" sx={{ py: 0.5 }}>
                              جزئیات اقلام این درخواست در دسترس نیست.
                            </Alert>
                          ) : (
                            (request.items ?? []).map((line) => (
                              <Box
                                key={String(line.id)}
                                sx={{
                                  p: 1,
                                  border: '1px solid',
                                  borderColor: received ? 'success.light' : 'divider',
                                  borderRadius: (t) => t.radius('sm'),
                                  bgcolor: received
                                    ? 'rgba(46, 125, 50, 0.04)'
                                    : 'background.default',
                                }}
                              >
                                <Stack spacing={0.5}>
                                  <Typography fontWeight={800}>
                                    {line.material_number}
                                    {line.material_name
                                      ? ` · ${line.material_name}`
                                      : ''}
                                  </Typography>
                                  <Stack
                                    direction={{ xs: 'column', sm: 'row' }}
                                    spacing={{ xs: 0.25, sm: 2 }}
                                    useFlexGap
                                  >
                                    <Typography variant="body2" color="text.secondary">
                                      تعداد: {toFaNumber(String(line.quantity))}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                      تامین:{' '}
                                      {MATERIAL_DECISION_LABELS[line.decision ?? ''] ||
                                        line.decision ||
                                        '—'}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                      وضعیت قلم:{' '}
                                      {MATERIAL_ITEM_STATUS_LABELS[
                                        line.item_status ?? ''
                                      ] ||
                                        line.item_status ||
                                        '—'}
                                    </Typography>
                                  </Stack>
                                </Stack>
                              </Box>
                            ))
                          )}
                        </Stack>
                      </Stack>
                    </CardContent>
                  </Card>
                );
                  })}
                </Stack>
              )}
            </Stack>
          ),
        },
        {
          label: 'قطعات مصرفی',
          content: (
            <Stack spacing={2}>
              {canRecordConsumed ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={700} mb={1.5}>
                      ثبت قطعه مصرفی
                    </Typography>
                    <Stack spacing={1.5}>
                      <Typography variant="body2" color="text.secondary">
                        برای هر قطعه مصرفی تعداد جداگانه ثبت کنید (متفاوت از درخواست قطعه).
                      </Typography>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1}
                        useFlexGap
                        alignItems="flex-start"
                      >
                        <MaterialStockPicker
                          label="قطعه مصرفی"
                          value={consumedPart}
                          onChange={setConsumedPart}
                          showSelectedChip={false}
                        />
                        <RtlTextField
                          label="تعداد"
                          value={consumedQty}
                          onChange={(event) => setConsumedQty(event.target.value)}
                          size="small"
                          type="number"
                          inputProps={{ min: 1 }}
                          sx={{ width: { xs: '100%', sm: 110 } }}
                        />
                        <Button
                          variant="outlined"
                          disabled={!consumedPart.materialNumber.trim()}
                          onClick={addConsumedLine}
                          sx={{ mt: { sm: 0.5 } }}
                        >
                          افزودن به لیست
                        </Button>
                      </Stack>
                      {consumedLines.length > 0 ? (
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                          {consumedLines.map((line) => (
                            <Chip
                              key={line.key}
                              color={line.fromCatalog ? 'success' : 'warning'}
                              variant="outlined"
                              label={lineChipLabel(line)}
                              onDelete={() =>
                                setConsumedLines((prev) =>
                                  prev.filter((item) => item.key !== line.key),
                                )
                              }
                            />
                          ))}
                        </Stack>
                      ) : null}
                      <Stack
                        direction="row"
                        justifyContent="flex-end"
                        sx={{
                          pt: 1,
                          borderTop: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Button
                          variant="contained"
                          color="success"
                          loading={actionLoading === 'consumed'}
                          disabled={!canSubmitConsumed}
                          onClick={() => void recordConsumedPart()}
                        >
                          ثبت قطعه مصرفی
                        </Button>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              ) : null}

              {detail.order.parts && detail.order.parts.length > 0 ? (
                <Stack spacing={1}>
                  {detail.order.parts.map((part) => {
                    return (
                      <Box
                        key={part.id}
                        sx={{
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 1,
                          px: 1.5,
                          py: 1,
                          bgcolor: 'background.paper',
                        }}
                      >
                        <Stack
                          direction={{ xs: 'column', sm: 'row' }}
                          justifyContent="space-between"
                          gap={1}
                        >
                          <Box>
                            <Typography fontWeight={800}>
                              {part.material_number}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              تعداد {toFaNumber(part.quantity)}
                              {part.unit_of_measure && part.unit_of_measure !== '-'
                                ? ` ${part.unit_of_measure}`
                                : ''}
                              {part.posted_at
                                ? ` · ثبت انبار ${formatDateTime(part.posted_at)}`
                                : ''}
                            </Typography>
                          </Box>
                        </Stack>
                      </Box>
                    );
                  })}
                </Stack>
              ) : canRecordConsumed ? null : (
                <EmptyState title="قطعه مصرفی ثبت نشده است" />
              )}
            </Stack>
          ),
        },
        {
          label: 'سوابق تعمیرات',
          content:
            detail.history.length === 0 ? (
              <EmptyState title="سابقه تعمیر دیگری نیست" />
            ) : (
              <Stack spacing={1}>
                {detail.history.map((item) => (
                  <Card key={item.id} variant="outlined">
                    <CardContent>
                      <DetailLine label="وضعیت" value={statusLabel(item.status)} />
                      <DetailLine
                        label="PM Order"
                        value={item.sap_order_number || '—'}
                      />
                      <DetailLine label="زمان" value={formatDateTime(item.updated_at)} />
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ),
        },
        {
          label: 'تاریخچه',
          content:
            detail.timeline.length === 0 ? (
              <EmptyState title="رویدادی ثبت نشده" />
            ) : (
              <Stack spacing={1}>
                {detail.timeline.map((event, index) => (
                  <Card key={`${event.event_type}-${index}`} variant="outlined">
                    <CardContent>
                      <Typography fontWeight={700}>{event.description}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {event.event_type} · {formatDateTime(event.created_at)}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ),
        },
      ]
    : [];

  return (
    <FeaturePage>
      <PageHeader
        title="کارتابل تعمیرگاه مرکزی"
        breadcrumbs={[{ label: 'تعمیرات' }, { label: 'تعمیرگاه مرکزی' }]}
      />

      <KpiGrid>
        <KpiCard label="صف تصمیم فنی" value={toFaNumber(queueCount)} icon={Build} tone="warning" />
        <KpiCard label="در حال تعمیر" value={toFaNumber(inProgressCount)} icon={Build} tone="success" />
        <KpiCard
          label="در انتظار قطعات"
          value={toFaNumber(waitingPartsCount)}
          icon={Inventory2}
          tone="error"
        />
      </KpiGrid>

      <StatusFilterTabs
        value={statusTab}
        options={STATUS_TAB_OPTIONS}
        onChange={(next) => {
          setStatusTab(next);
          if (next) setStatusFilter('');
        }}
        ariaLabel="وضعیت تعمیرگاه مرکزی"
      />

      {statusTab === '' && (
        <FilterPanel>
          <RtlSelectField
            label="وضعیت"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            size="small"
          >
            <MenuItem value="">همه</MenuItem>
            <MenuItem value="WORKSHOP_ASSIGNED">صف تصمیم فنی</MenuItem>
            <MenuItem value="IN_PROGRESS">در حال تعمیر</MenuItem>
            <MenuItem value="WAITING_PARTS">در انتظار قطعات</MenuItem>
            <MenuItem value="NO_REPAIR_NEEDED">عدم نیاز به تعمیر</MenuItem>
          </RtlSelectField>
          <ClearFiltersButton
            onClick={() => setStatusFilter('')}
            disabled={statusFilter === ''}
          />
        </FilterPanel>
      )}

      {error && <ErrorState message={error} onRetry={() => void load()} />}
      {!loading && !error && (
        <RtlDataTable
          rows={items}
          columns={columns}
          getRowKey={(row) => row.id}
          emptyMessage="موردی در کارتابل تعمیرگاه نیست"
          emptySubtitle="پس از ارجاع ترابری به تعمیرگاه مرکزی، اینجا نمایش داده می‌شود."
          loading={loading}
        />
      )}
      {loading && !error && (
        <RtlDataTable rows={[]} columns={columns} loading emptyMessage="در حال بارگذاری" />
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={() => {
          setSelected(null);
          setDetail(null);
        }}
        title="جزئیات درخواست تعمیرگاه مرکزی"
        icon={Build}
        tabs={tabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />

      {isMobile && null}
    </FeaturePage>
  );
}
