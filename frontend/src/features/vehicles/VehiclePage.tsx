import { useEffect, useState, type ReactNode } from 'react';
import {
  Box,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  InputAdornment,
  Link,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Close,
  Error as ErrorIcon,
  Inbox,
  Speed,
  Search,
  TaskAlt,
} from '@mui/icons-material';
import { CarRepair, DirectionsCar, Sync } from '../../components/icons3d/Icons3D';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { JalaliDateRangeFilter } from '../../components/JalaliDateRangeFilter';
import { KpiCard } from '../../components/KpiCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { PageHeader } from '../../components/PageHeader';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlPagination } from '../../components/RtlPagination';
import { RtlTextField } from '../../components/RtlTextField';
import { FilterPanel } from '../../components/FilterPanel';
import { RtlSelectField } from '../../components/RtlSelectField';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type {
  AssignedVehicleDriver,
  Fault,
  Inspection,
  OdometerReading,
  RepairOrder,
  Vehicle,
  VehicleDriverAssignmentHistory,
  VehicleStatus,
  VehicleSummary,
} from '../../types/fmms';
import { isValidIsoDateRange } from '../../utils/dateRange';
import { formatDate, formatDateTime, toFaNumber } from '../../utils/format';
import {
  checklistOverallLabel,
  checklistOverallTone,
  sortChecklistItems,
} from '../inspections/checklistDisplay';

const statusOptions: Array<{ value: '' | VehicleStatus; label: string }> = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'ACTIVE', label: 'عملیاتی' },
  { value: 'UNDER_REPAIR', label: 'در تعمیر' },
  { value: 'WAITING_DRIVER_CONFIRMATION', label: 'منتظر تایید راننده' },
  { value: 'EXITED_CENTER', label: 'خارج شده از مرکز' },
  { value: 'OUT_OF_SERVICE', label: 'خارج از سرویس' },
  { value: 'SUSPENDED', label: 'تعلیق‌شده' },
  { value: 'INACTIVE', label: 'غیرفعال' },
  { value: 'DECOMMISSIONED', label: 'از رده خارج' },
];

const PAGE_SIZE = 20;

function useVehicleSummary() {
  const [summary, setSummary] = useState<VehicleSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await api.getVehicleSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت خلاصه خودروها');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  return { summary, loading, error, reload: load };
}

function useVehicles(
  status: '' | VehicleStatus,
  ordering: string,
  page: number,
  search: string,
) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listVehicles(status, ordering, {
        page,
        pageSize: PAGE_SIZE,
        search: search || undefined,
      });
      setVehicles(result.results);
      setTotal(result.count);
    } catch (err) {
      setVehicles([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : 'خطا در دریافت خودروها');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [status, ordering, page, search]);
  return { vehicles, total, loading, error, reload: load };
}

function driverName(driver: Vehicle['driver1']): string {
  if (!driver) return '—';
  return driver.name || driver.customer_number;
}

type DriverHistoryRow = {
  id: string;
  assigned_at: string;
  driver1Name: string;
  driver1Id: string | null;
  driver2Name: string;
  driver2Id: string | null;
};

type DriverHistorySortKey = 'assigned_at' | 'driver1Name' | 'driver2Name';

function historyDriverName(driver: AssignedVehicleDriver | null): string {
  if (!driver) return '—';
  return driver.name || driver.customer_number || '—';
}

/** Map assignment snapshots to one table row per date (driver + assistant). */
function mapDriverHistory(items: VehicleDriverAssignmentHistory[]): DriverHistoryRow[] {
  return items.map((item, index) => ({
    id: `${item.assigned_at}-${index}`,
    assigned_at: item.assigned_at,
    driver1Name: historyDriverName(item.driver1),
    driver1Id: item.driver1?.id ?? null,
    driver2Name: historyDriverName(item.driver2),
    driver2Id: item.driver2?.id ?? null,
  }));
}

const INSPECTION_TYPE_LABELS: Record<string, string> = {
  PRE_TRIP: 'پیش از حرکت',
  POST_TRIP: 'پس از حرکت',
  PERIODIC: 'دوره‌ای',
  UNSCHEDULED: 'خارج از برنامه',
};

const INSPECTION_STATUS_LABELS: Record<string, string> = {
  DRAFT: 'پیش‌نویس',
  SUBMITTED: 'ثبت‌شده',
  REVIEWED: 'بررسی‌شده',
};

const CHECKLIST_RESULT_LABELS: Record<string, string> = {
  PASS: 'قبول',
  FAIL: 'مردود',
  NOT_APPLICABLE: 'نامرتبط',
  NA: 'نامرتبط',
};

const SEVERITY_LABELS: Record<string, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

type ChecklistSortKey = 'inspected_at' | 'inspection_type' | 'odometer_value' | 'status' | 'overall_result';

function normalizeInspections(payload: { results?: Inspection[] } | Inspection[]): Inspection[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

function VehicleCard({ vehicle, onOpen }: { vehicle: Vehicle; onOpen: (vehicle: Vehicle) => void }) {
  return (
    <Card onClick={() => onOpen(vehicle)} sx={{ cursor: 'pointer' }}>
      <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
        <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
          <Box minWidth={0}>
            <Typography fontWeight={900} noWrap>
              {vehicle.license_plate}
            </Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              شناسه خودرو: {vehicle.vehicle_number}
            </Typography>
          </Box>
          <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />
        </Stack>
        <Divider sx={{ my: 1.25 }} />
        <Grid container spacing={1}>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">راننده</Typography>
            <Typography variant="body2" noWrap>{driverName(vehicle.driver1)}</Typography>
          </Grid>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">کمک راننده</Typography>
            <Typography variant="body2" noWrap>{driverName(vehicle.driver2)}</Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

type VehicleSortKey = 'license_plate' | 'vehicle_number' | 'status';
type VehicleColumnKey = VehicleSortKey | 'driver1' | 'driver2' | 'actions';

function VehicleTable({
  vehicles,
  onOpen,
  orderBy,
  order,
  onSort,
  loading = false,
}: {
  vehicles: Vehicle[];
  onOpen: (vehicle: Vehicle) => void;
  orderBy: VehicleSortKey;
  order: 'asc' | 'desc';
  onSort: (key: VehicleSortKey) => void;
  loading?: boolean;
}) {
  const columns: Array<RtlDataTableColumn<Vehicle, VehicleColumnKey>> = [
    { key: 'vehicle_number', label: 'شناسه خودرو', sortable: true, skeleton: 'text', render: (vehicle) => vehicle.vehicle_number },
    {
      key: 'license_plate',
      label: 'پلاک',
      sortable: true,
      skeleton: 'text',
      render: (vehicle) => <Typography fontWeight={800}>{vehicle.license_plate}</Typography>,
    },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      skeleton: 'badge',
      render: (vehicle) => <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />,
    },
    { key: 'driver1', label: 'راننده', skeleton: 'text', render: (vehicle) => driverName(vehicle.driver1) },
    { key: 'driver2', label: 'کمک راننده', skeleton: 'text', render: (vehicle) => driverName(vehicle.driver2) },
    {
      key: 'actions',
      label: 'جزئیات',
      align: 'center',
      skeleton: 'button',
      render: (vehicle) => (
        <Button size="small" variant="outlined" onClick={() => onOpen(vehicle)}>
          مشاهده
        </Button>
      ),
    },
  ];

  return (
    <RtlDataTable
      columns={columns}
      rows={vehicles}
      getRowKey={(vehicle) => vehicle.id}
      minWidth={880}
      orderBy={orderBy}
      order={order}
      loading={loading}
      skeletonRows={6}
      emptyMessage="خودرویی یافت نشد"
      emptySubtitle="با تغییر فیلتر یا جستجو دوباره تلاش کنید"
      emptyIcon={Inbox}
      onSort={(key) => {
        if (key !== 'actions' && key !== 'driver1' && key !== 'driver2') onSort(key);
      }}
    />
  );
}

function HistoryCard({
  title,
  meta,
  badge,
}: {
  title: ReactNode;
  meta?: ReactNode;
  badge?: ReactNode;
}) {
  return (
    <Box
      sx={{
        p: 1.5,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'background.paper',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
        '&:hover': {
          borderColor: 'rgba(15, 107, 76, 0.35)',
          boxShadow: '0 6px 18px rgba(15, 107, 76, 0.06)',
        },
      }}
    >
      <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
        <Box minWidth={0}>
          <Typography fontWeight={800} noWrap>{title}</Typography>
          {meta && (
            <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
              {meta}
            </Typography>
          )}
        </Box>
        {badge}
      </Stack>
    </Box>
  );
}

function settledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
  return result.status === 'fulfilled' ? result.value : fallback;
}

function VehicleDetailModal({
  vehicle,
  open,
  onClose,
}: {
  vehicle: Vehicle | null;
  open: boolean;
  onClose: () => void;
}) {
  const [tab, setTab] = useState(0);
  const [detail, setDetail] = useState<Vehicle | null>(null);
  const [odometer, setOdometer] = useState<OdometerReading[]>([]);
  const [odometerFromDate, setOdometerFromDate] = useState('');
  const [odometerToDate, setOdometerToDate] = useState('');
  const [odometerLoading, setOdometerLoading] = useState(false);
  const [driverHistory, setDriverHistory] = useState<VehicleDriverAssignmentHistory[]>([]);
  const [driverHistoryFromDate, setDriverHistoryFromDate] = useState('');
  const [driverHistoryToDate, setDriverHistoryToDate] = useState('');
  const [driverHistoryLoading, setDriverHistoryLoading] = useState(false);
  const [driverHistoryOrderBy, setDriverHistoryOrderBy] = useState<DriverHistorySortKey>('assigned_at');
  const [driverHistoryOrder, setDriverHistoryOrder] = useState<'asc' | 'desc'>('desc');
  const [odometerOrderBy, setOdometerOrderBy] = useState<'reading_date' | 'odometer_km' | 'source'>('reading_date');
  const [odometerOrder, setOdometerOrder] = useState<'asc' | 'desc'>('desc');
  const [checklists, setChecklists] = useState<Inspection[]>([]);
  const [checklistFromDate, setChecklistFromDate] = useState('');
  const [checklistToDate, setChecklistToDate] = useState('');
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [checklistOrderBy, setChecklistOrderBy] = useState<ChecklistSortKey>('inspected_at');
  const [checklistOrder, setChecklistOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedChecklistId, setSelectedChecklistId] = useState<string | null>(null);
  const [selectedChecklist, setSelectedChecklist] = useState<Inspection | null>(null);
  const [checklistDetailLoading, setChecklistDetailLoading] = useState(false);
  const [checklistDetailError, setChecklistDetailError] = useState('');
  const [faults, setFaults] = useState<Fault[]>([]);
  const [repairs, setRepairs] = useState<RepairOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadOdometerHistory = async (
    fromDate = odometerFromDate,
    toDate = odometerToDate,
  ) => {
    if (!vehicle || !isValidIsoDateRange(fromDate, toDate)) return;
    setOdometerLoading(true);
    try {
      setOdometer(
        await api.getOdometerHistory(vehicle.id, {
          fromDate: fromDate || undefined,
          toDate: toDate || undefined,
        }),
      );
    } catch {
      setOdometer([]);
    } finally {
      setOdometerLoading(false);
    }
  };

  const loadDriverHistory = async (
    fromDate = driverHistoryFromDate,
    toDate = driverHistoryToDate,
  ) => {
    if (!vehicle || !isValidIsoDateRange(fromDate, toDate)) return;
    setDriverHistoryLoading(true);
    try {
      const drivers = await api.getDriverAssignmentHistory(vehicle.id, {
        fromDate: fromDate || undefined,
        toDate: toDate || undefined,
      });
      setDriverHistory(drivers);
    } catch {
      setDriverHistory([]);
    } finally {
      setDriverHistoryLoading(false);
    }
  };

  const loadChecklists = async (
    fromDate = checklistFromDate,
    toDate = checklistToDate,
  ) => {
    if (!vehicle || !isValidIsoDateRange(fromDate, toDate)) return;
    setChecklistLoading(true);
    try {
      const payload = await api.listVehicleChecklists(vehicle.id, {
        fromDate: fromDate || undefined,
        toDate: toDate || undefined,
      });
      setChecklists(normalizeInspections(payload));
    } catch {
      setChecklists([]);
    } finally {
      setChecklistLoading(false);
    }
  };

  const openChecklistDetail = async (inspectionId: string) => {
    if (!vehicle) return;
    setSelectedChecklistId(inspectionId);
    setChecklistDetailLoading(true);
    setChecklistDetailError('');
    setSelectedChecklist(null);
    try {
      const detail = await api.getVehicleChecklist(vehicle.id, inspectionId);
      setSelectedChecklist(detail);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'خطا در دریافت جزئیات چک‌لیست';
      setChecklistDetailError(
        message === 'Failed to fetch' ? 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.' : message,
      );
    } finally {
      setChecklistDetailLoading(false);
    }
  };

  const closeChecklistDetail = () => {
    setSelectedChecklistId(null);
    setSelectedChecklist(null);
    setChecklistDetailError('');
  };

  const loadDetail = async (
    fromDate = driverHistoryFromDate,
    toDate = driverHistoryToDate,
    odoFromDate = odometerFromDate,
    odoToDate = odometerToDate,
  ) => {
    if (!vehicle) return;
    setLoading(true);
    setError('');
    try {
      const [vehicleResult, odoResult, driversResult, faultsResult, repairsResult] = await Promise.allSettled([
        api.getVehicle(vehicle.id),
        api.getOdometerHistory(vehicle.id, {
          fromDate: odoFromDate || undefined,
          toDate: odoToDate || undefined,
        }),
        api.getDriverAssignmentHistory(vehicle.id, {
          fromDate: fromDate || undefined,
          toDate: toDate || undefined,
        }),
        api.listFaults(vehicle.id),
        api.listRepairOrders({ vehicleId: vehicle.id }),
      ]);

      if (vehicleResult.status === 'rejected') {
        throw vehicleResult.reason instanceof Error
          ? vehicleResult.reason
          : new Error('خطا در دریافت جزئیات خودرو');
      }

      setDetail(vehicleResult.value);
      setOdometer(settledValue(odoResult, []));
      setDriverHistory(settledValue(driversResult, []));
      setFaults(settledValue(faultsResult, { results: [] as Fault[], count: 0, next: null, previous: null }).results ?? []);
      setRepairs(settledValue(repairsResult, { results: [] as RepairOrder[], count: 0, next: null, previous: null }).results ?? []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'خطا در دریافت جزئیات خودرو';
      setError(message === 'Failed to fetch' ? 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.' : message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setDetail(null);
    setOdometer([]);
    setOdometerFromDate('');
    setOdometerToDate('');
    setDriverHistory([]);
    setDriverHistoryFromDate('');
    setDriverHistoryToDate('');
    setChecklists([]);
    setChecklistFromDate('');
    setChecklistToDate('');
    setSelectedChecklistId(null);
    setSelectedChecklist(null);
    setChecklistDetailError('');
    setFaults([]);
    setRepairs([]);
    setTab(0);
    if (open) {
      void loadDetail('', '', '', '');
      void loadChecklists('', '');
    }
  }, [open, vehicle?.id]);

  const displayVehicle = detail ?? vehicle;
  const latestOdometer = odometer[0];
  const usedParts = repairs.flatMap((repair) => repair.parts ?? []);
  const driverHistoryRows = mapDriverHistory(driverHistory);
  const sortedDriverHistory = [...driverHistoryRows].sort((a, b) => {
    const dir = driverHistoryOrder === 'asc' ? 1 : -1;
    const left = String(a[driverHistoryOrderBy] ?? '');
    const right = String(b[driverHistoryOrderBy] ?? '');
    return left.localeCompare(right, 'fa') * dir;
  });

  const sortedOdometer = [...odometer].sort((a, b) => {
    const dir = odometerOrder === 'asc' ? 1 : -1;
    if (odometerOrderBy === 'odometer_km') {
      return (a.odometer_km - b.odometer_km) * dir;
    }
    const left = String(a[odometerOrderBy] ?? '');
    const right = String(b[odometerOrderBy] ?? '');
    return left.localeCompare(right, 'fa') * dir;
  });

  const sortedChecklists = [...checklists].sort((a, b) => {
    const dir = checklistOrder === 'asc' ? 1 : -1;
    if (checklistOrderBy === 'odometer_value') {
      return ((a.odometer_value ?? 0) - (b.odometer_value ?? 0)) * dir;
    }
    const left = String(a[checklistOrderBy] ?? '');
    const right = String(b[checklistOrderBy] ?? '');
    return left.localeCompare(right, 'fa') * dir;
  });

  type OdometerSortKey = 'reading_date' | 'odometer_km' | 'source';

  const ODOMETER_SOURCE_LABELS: Record<string, string> = {
    DRIVER: 'راننده',
    SAP: 'SAP',
    SYSTEM: 'سیستم',
    MANUAL: 'دستی',
  };

  const odometerColumns: Array<RtlDataTableColumn<OdometerReading, OdometerSortKey>> = [
    {
      key: 'reading_date',
      label: 'تاریخ ثبت',
      sortable: true,
      render: (row) => formatDate(row.reading_date),
    },
    {
      key: 'odometer_km',
      label: 'کیلومتر',
      sortable: true,
      render: (row) => toFaNumber(row.odometer_km),
    },
    {
      key: 'source',
      label: 'منبع',
      sortable: true,
      render: (row) => ODOMETER_SOURCE_LABELS[row.source] ?? row.source ?? '—',
    },
  ];

  const driverHistoryColumns: Array<RtlDataTableColumn<DriverHistoryRow, DriverHistorySortKey>> = [
    {
      key: 'assigned_at',
      label: 'تاریخ تخصیص',
      sortable: true,
      render: (row) => formatDateTime(row.assigned_at),
    },
    {
      key: 'driver1Name',
      label: 'راننده اصلی',
      sortable: true,
      render: (row) =>
        row.driver1Id ? (
          <Link
            component={RouterLink}
            to={`/drivers/${row.driver1Id}`}
            underline="hover"
            fontWeight={800}
            onClick={onClose}
          >
            {row.driver1Name}
          </Link>
        ) : (
          row.driver1Name
        ),
    },
    {
      key: 'driver2Name',
      label: 'کمک راننده',
      sortable: true,
      render: (row) =>
        row.driver2Id ? (
          <Link
            component={RouterLink}
            to={`/drivers/${row.driver2Id}`}
            underline="hover"
            fontWeight={800}
            onClick={onClose}
          >
            {row.driver2Name}
          </Link>
        ) : (
          row.driver2Name
        ),
    },
  ];

  const checklistColumns: Array<RtlDataTableColumn<Inspection, ChecklistSortKey | 'actions'>> = [
    {
      key: 'inspected_at',
      label: 'تاریخ بازرسی',
      sortable: true,
      render: (row) => formatDateTime(row.inspected_at),
    },
    {
      key: 'inspection_type',
      label: 'نوع',
      sortable: true,
      render: (row) => INSPECTION_TYPE_LABELS[row.inspection_type] ?? row.inspection_type,
    },
    {
      key: 'odometer_value',
      label: 'کیلومتر',
      sortable: true,
      render: (row) =>
        row.odometer_value != null ? toFaNumber(row.odometer_value) : '—',
    },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      render: (row) => (
        <PlainStatusBadge label={INSPECTION_STATUS_LABELS[row.status] ?? row.status} />
      ),
    },
    {
      key: 'overall_result',
      label: 'نتیجه',
      sortable: true,
      render: (row) => (
        <PlainStatusBadge
          tone={checklistOverallTone(row.has_failures, row.overall_result)}
          label={checklistOverallLabel(row.has_failures, row.overall_result, CHECKLIST_RESULT_LABELS)}
        />
      ),
    },
    {
      key: 'actions',
      label: 'عملیات',
      align: 'center',
      render: (row) => (
        <Button size="small" variant="outlined" onClick={() => void openChecklistDetail(row.id)}>
          جزئیات
        </Button>
      ),
    },
  ];

  const checklistItemColumns: Array<
    RtlDataTableColumn<Inspection['items'][number], 'category' | 'description' | 'result' | 'severity' | 'notes'>
  > = [
    {
      key: 'category',
      label: 'دسته',
      render: (row) => row.category || '—',
    },
    {
      key: 'description',
      label: 'شرح',
      render: (row) => row.description || '—',
    },
    {
      key: 'result',
      label: 'نتیجه',
      render: (row) => (
        <PlainStatusBadge
          tone={row.result === 'FAIL' ? 'error' : row.result === 'PASS' ? 'success' : 'neutral'}
          label={CHECKLIST_RESULT_LABELS[row.result] ?? row.result}
        />
      ),
    },
    {
      key: 'severity',
      label: 'شدت',
      render: (row) =>
        row.severity ? (
          <Typography
            fontWeight={row.result === 'FAIL' ? 800 : 500}
            color={row.result === 'FAIL' ? 'error.main' : 'inherit'}
          >
            {SEVERITY_LABELS[row.severity] ?? row.severity}
          </Typography>
        ) : (
          '—'
        ),
    },
    {
      key: 'notes',
      label: 'یادداشت',
      render: (row) =>
        row.notes ? (
          <Typography fontWeight={row.result === 'FAIL' ? 700 : 400}>{row.notes}</Typography>
        ) : (
          '—'
        ),
    },
  ];

  const tabs = displayVehicle
    ? [
        {
          label: 'اطلاعات پایه',
          content: (
            <Card
              variant="outlined"
              sx={{
                borderColor: 'divider',
                borderRadius: (t) => t.radius('md'),
                boxShadow: '0 8px 22px rgba(15, 107, 76, 0.07)',
              }}
            >
              <CardContent sx={{ p: { xs: 1.75, sm: 2.25 }, '&:last-child': { pb: { xs: 1.75, sm: 2.25 } } }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
                  <Typography variant="h3">اطلاعات پایه</Typography>
                  <VehicleStatusBadge status={displayVehicle.status} label={displayVehicle.status_label} />
                </Stack>
                <DetailLine label="پلاک" value={<Typography fontWeight={800}>{displayVehicle.license_plate}</Typography>} />
                <DetailLine label="شناسه خودرو" value={<Typography variant="body2">{displayVehicle.vehicle_number}</Typography>} />
                <DetailLine label="راننده" value={<Typography variant="body2">{driverName(displayVehicle.driver1)}</Typography>} />
                <DetailLine label="کمک راننده" value={<Typography variant="body2">{driverName(displayVehicle.driver2)}</Typography>} />
                <DetailLine label="تاریخ بهره‌برداری" value={displayVehicle.commissioning_date || '—'} />
                <DetailLine label="آخرین کیلومتر" value={latestOdometer ? `${toFaNumber(latestOdometer.odometer_km)} km` : '—'} />
              </CardContent>
            </Card>
          ),
        },
        {
          label: 'تاریخچه کیلومتر',
          content: odometerLoading ? (
            <LoadingState label="در حال دریافت تاریخچه کیلومتر" />
          ) : sortedOdometer.length === 0 && !odometerFromDate && !odometerToDate ? (
            <EmptyState title="رکورد کیلومتری ثبت نشده است" />
          ) : (
            <Stack spacing={1.5}>
              <JalaliDateRangeFilter
                fromDate={odometerFromDate}
                toDate={odometerToDate}
                disabled={odometerLoading}
                onChange={({ fromDate, toDate }) => {
                  setOdometerFromDate(fromDate);
                  setOdometerToDate(toDate);
                  void loadOdometerHistory(fromDate, toDate);
                }}
                onClear={() => {
                  setOdometerFromDate('');
                  setOdometerToDate('');
                  void loadOdometerHistory('', '');
                }}
              />
              <RtlDataTable
                columns={odometerColumns}
                rows={sortedOdometer}
                getRowKey={(row) => row.id}
                orderBy={odometerOrderBy}
                order={odometerOrder}
                onSort={(key) => {
                  if (odometerOrderBy === key) {
                    setOdometerOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
                    return;
                  }
                  setOdometerOrderBy(key);
                  setOdometerOrder('asc');
                }}
                emptyMessage="رکورد کیلومتری ثبت نشده است"
                emptySubtitle={
                  odometerFromDate || odometerToDate
                    ? 'با تغییر بازه تاریخ دوباره تلاش کنید'
                    : undefined
                }
                standaloneEmpty
                minWidth={480}
              />
            </Stack>
          ),
        },
        {
          label: 'تاریخچه راننده',
          content: driverHistoryLoading ? (
            <LoadingState label="در حال دریافت تاریخچه راننده" />
          ) : sortedDriverHistory.length === 0 &&
            !driverHistoryFromDate &&
            !driverHistoryToDate ? (
            <EmptyState title="تاریخچه راننده ثبت نشده است" />
          ) : (
            <Stack spacing={1.5}>
              <JalaliDateRangeFilter
                fromDate={driverHistoryFromDate}
                toDate={driverHistoryToDate}
                disabled={driverHistoryLoading}
                onChange={({ fromDate, toDate }) => {
                  setDriverHistoryFromDate(fromDate);
                  setDriverHistoryToDate(toDate);
                  void loadDriverHistory(fromDate, toDate);
                }}
                onClear={() => {
                  setDriverHistoryFromDate('');
                  setDriverHistoryToDate('');
                  void loadDriverHistory('', '');
                }}
              />
              <RtlDataTable
                columns={driverHistoryColumns}
                rows={sortedDriverHistory}
                getRowKey={(row) => row.id}
                orderBy={driverHistoryOrderBy}
                order={driverHistoryOrder}
                onSort={(key) => {
                  if (driverHistoryOrderBy === key) {
                    setDriverHistoryOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
                    return;
                  }
                  setDriverHistoryOrderBy(key);
                  setDriverHistoryOrder('asc');
                }}
                emptyMessage="تاریخچه راننده ثبت نشده است"
                emptySubtitle={
                  driverHistoryFromDate || driverHistoryToDate
                    ? 'با تغییر بازه تاریخ دوباره تلاش کنید'
                    : undefined
                }
                standaloneEmpty
                minWidth={480}
              />
            </Stack>
          ),
        },
        {
          label: 'تاریخچه چک‌لیست',
          content: checklistLoading ? (
            <LoadingState label="در حال دریافت تاریخچه چک‌لیست" />
          ) : sortedChecklists.length === 0 && !checklistFromDate && !checklistToDate ? (
            <EmptyState title="چک‌لیستی ثبت نشده است" />
          ) : (
            <Stack spacing={1.5}>
              <JalaliDateRangeFilter
                fromDate={checklistFromDate}
                toDate={checklistToDate}
                disabled={checklistLoading}
                onChange={({ fromDate, toDate }) => {
                  setChecklistFromDate(fromDate);
                  setChecklistToDate(toDate);
                  void loadChecklists(fromDate, toDate);
                }}
                onClear={() => {
                  setChecklistFromDate('');
                  setChecklistToDate('');
                  void loadChecklists('', '');
                }}
              />
              <RtlDataTable
                columns={checklistColumns}
                rows={sortedChecklists}
                getRowKey={(row) => row.id}
                orderBy={checklistOrderBy}
                order={checklistOrder}
                onSort={(key) => {
                  if (key === 'actions') return;
                  if (checklistOrderBy === key) {
                    setChecklistOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
                    return;
                  }
                  setChecklistOrderBy(key);
                  setChecklistOrder('asc');
                }}
                emptyMessage="چک‌لیستی ثبت نشده است"
                emptySubtitle={
                  checklistFromDate || checklistToDate
                    ? 'با تغییر بازه تاریخ دوباره تلاش کنید'
                    : undefined
                }
                standaloneEmpty
                minWidth={720}
              />
            </Stack>
          ),
        },
        {
          label: 'تاریخچه خرابی‌ها',
          content: faults.length ? (
            <Stack spacing={1}>
              {faults.map((fault) => (
                <HistoryCard
                  key={fault.id}
                  title={fault.description}
                  meta={`${fault.code} · SAP: ${fault.sap_notification_number || 'در صف ارسال'} · ${formatDateTime(fault.reported_at || fault.created_at)}`}
                  badge={<PlainStatusBadge label={fault.status} />}
                />
              ))}
            </Stack>
          ) : (
            <EmptyState title="خرابی ثبت نشده است" />
          ),
        },
        {
          label: 'تعمیرات و قطعات',
          content: repairs.length ? (
            <Stack spacing={1.25}>
              {repairs.map((repair) => (
                <HistoryCard
                  key={repair.id}
                  title={`دستور تعمیر ${repair.id.slice(0, 8)}`}
                  meta={`تعمیرگاه: ${repair.workshop_type || '—'} · ${formatDateTime(repair.updated_at)}`}
                  badge={<PlainStatusBadge label={repair.status} />}
                />
              ))}
              <Box
                sx={{
                  mt: 0.5,
                  px: 1.5,
                  py: 1.25,
                  borderRadius: (t) => t.radius('md'),
                  bgcolor: 'rgba(15, 107, 76, 0.06)',
                  border: '1px solid rgba(15, 107, 76, 0.16)',
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  قطعات مصرف‌شده: {usedParts.length ? `${toFaNumber(usedParts.length)} قلم` : '—'}
                </Typography>
              </Box>
            </Stack>
          ) : (
            <EmptyState title="سابقه تعمیر ثبت نشده است" />
          ),
        },
      ]
    : [];

  const checklistDetailOpen = Boolean(selectedChecklistId);

  return (
    <>
      <TabbedDetailModal
        open={open && Boolean(displayVehicle)}
        onClose={onClose}
        title="جزئیات خودرو"
        icon={DirectionsCar}
        loading={loading}
        loadingLabel="در حال دریافت جزئیات خودرو"
        error={error}
        onRetry={() =>
          void loadDetail(
            driverHistoryFromDate,
            driverHistoryToDate,
            odometerFromDate,
            odometerToDate,
          )
        }
        activeTab={tab}
        onTabChange={setTab}
        tabs={tabs}
      />

      <Dialog
        open={checklistDetailOpen}
        onClose={closeChecklistDetail}
        fullWidth
        maxWidth="md"
        disableScrollLock
        dir="rtl"
        PaperProps={{
          sx: {
            borderRadius: (t) => t.radius('md'),
            height: { sm: 640, md: 680 },
            maxHeight: { sm: 640, md: 680 },
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 24px 64px rgba(23, 35, 29, 0.18)',
          },
        }}
      >
        <DialogTitle sx={{ pr: 6, position: 'relative', flexShrink: 0 }}>
          جزئیات چک‌لیست
          <IconButton
            size="small"
            onClick={closeChecklistDetail}
            aria-label="بستن"
            sx={{ position: 'absolute', top: 12, left: 12 }}
          >
            <Close fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {checklistDetailLoading ? (
            <LoadingState label="در حال دریافت جزئیات چک‌لیست" />
          ) : checklistDetailError ? (
            <ErrorState
              message={checklistDetailError}
              onRetry={() => {
                if (selectedChecklistId) void openChecklistDetail(selectedChecklistId);
              }}
            />
          ) : selectedChecklist ? (
            <Stack spacing={2}>
              <Box>
                <DetailLine
                  label="تاریخ بازرسی"
                  value={formatDateTime(selectedChecklist.inspected_at)}
                />
                <DetailLine
                  label="نوع"
                  value={
                    INSPECTION_TYPE_LABELS[selectedChecklist.inspection_type] ??
                    selectedChecklist.inspection_type
                  }
                />
                <DetailLine
                  label="کیلومتر"
                  value={
                    selectedChecklist.odometer_value != null
                      ? `${toFaNumber(selectedChecklist.odometer_value)} ${
                          selectedChecklist.odometer_unit === 'MILES' ? 'mi' : 'km'
                        }`
                      : '—'
                  }
                />
                <DetailLine
                  label="وضعیت"
                  value={
                    <PlainStatusBadge
                      label={
                        INSPECTION_STATUS_LABELS[selectedChecklist.status] ??
                        selectedChecklist.status
                      }
                    />
                  }
                />
                <DetailLine
                  label="نتیجه کلی"
                  value={
                    <PlainStatusBadge
                      tone={checklistOverallTone(
                        selectedChecklist.has_failures,
                        selectedChecklist.overall_result,
                      )}
                      label={checklistOverallLabel(
                        selectedChecklist.has_failures,
                        selectedChecklist.overall_result,
                        CHECKLIST_RESULT_LABELS,
                      )}
                    />
                  }
                />
              </Box>
              <RtlDataTable
                columns={checklistItemColumns}
                rows={sortChecklistItems(selectedChecklist.items)}
                getRowKey={(row) => row.id}
                emptyMessage="آیتمی برای این چک‌لیست ثبت نشده است"
                standaloneEmpty
                minWidth={640}
              />
            </Stack>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}


export function VehiclePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<'' | VehicleStatus>('');
  const [orderBy, setOrderBy] = useState<VehicleSortKey>('vehicle_number');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Vehicle | null>(null);
  const ordering = `${order === 'desc' ? '-' : ''}${orderBy}`;
  const { summary, loading: summaryLoading, error: summaryError, reload: reloadSummary } = useVehicleSummary();
  const { vehicles, total, loading, error, reload } = useVehicles(status, ordering, page, search);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [status, ordering]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = searchInput.trim();
      setSearch((prev) => {
        if (prev === next) return prev;
        setPage(1);
        return next;
      });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    const vehicleId = searchParams.get('vehicleId');
    if (!vehicleId) {
      if (selected) setSelected(null);
      return;
    }

    if (selected?.id === vehicleId) return;

    const removeInvalidParam = () => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        next.delete('vehicleId');
        return next;
      }, { replace: true });
    };

    const fromList = vehicles.find((item) => item.id === vehicleId);
    if (fromList) {
      setSelected(fromList);
      return;
    }

    if (loading) return;

    let cancelled = false;
    void api
      .getVehicle(vehicleId)
      .then((vehicle) => {
        if (!cancelled) {
          setSelected(vehicle);
        }
      })
      .catch(() => {
        if (!cancelled) removeInvalidParam();
      });

    return () => {
      cancelled = true;
    };
  }, [loading, searchParams, selected, setSearchParams, vehicles]);

  const openVehicleDetail = (vehicle: Vehicle) => {
    setSelected(vehicle);
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set('vehicleId', vehicle.id);
      return next;
    });
  };

  const closeVehicleDetail = () => {
    setSelected(null);
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete('vehicleId');
      return next;
    });
  };

  const changeSort = (key: VehicleSortKey) => {
    setPage(1);
    if (orderBy === key) {
      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setOrderBy(key);
    setOrder('asc');
  };

  const resetFilters = () => {
    setSearchInput('');
    setSearch('');
    setStatus('');
    setOrderBy('vehicle_number');
    setOrder('asc');
    setPage(1);
  };

  const hasActiveFilters =
    search !== '' || status !== '' || orderBy !== 'vehicle_number' || order !== 'asc' || page !== 1;

  return (
    <FeaturePage>
      <PageHeader
        title="خودروها"
        breadcrumbs={[
          { label: 'خودرو' },
          { label: 'لیست خودروها' },
        ]}
      />

      <KpiGrid mdColumns={3} xlColumns={6}>
        <KpiCard label="کل ناوگان فعال" value={summaryLoading ? '...' : toFaNumber(summary?.active_fleet_count)} icon={DirectionsCar} tone="primary" />
        <KpiCard label="عملیاتی" value={summaryLoading ? '...' : toFaNumber(summary?.operational_fleet_count)} icon={TaskAlt} tone="success" />
        <KpiCard label="در تعمیر" value={summaryLoading ? '...' : toFaNumber(summary?.under_repair_fleet_count)} icon={CarRepair} tone="warning" />
        <KpiCard label="میانگین کیلومتر" value={summaryLoading ? '...' : toFaNumber(summary?.average_odometer_km)} icon={Speed} tone="info" />
        <KpiCard label="میانگین خرابی ماه" value={summaryLoading ? '...' : toFaNumber(summary?.average_faults_last_30_days)} icon={ErrorIcon} tone="error" />
        <KpiCard
          label="آخرین همگام‌سازی SAP"
          value={summaryLoading ? '...' : formatDateTime(summary?.last_sap_sync_at)}
          icon={Sync}
          tone="secondary"
        />
      </KpiGrid>
      {summaryError && <ErrorState message={summaryError} onRetry={reloadSummary} />}

      <FilterPanel>
        <RtlTextField
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          label="جستجو"
          placeholder="پلاک یا شناسه خودرو"
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ width: { xs: '100%', md: 280 }, flexShrink: 0 }}
        />
        <RtlSelectField<'' | VehicleStatus>
          value={status}
          label="وضعیت خودرو"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value as '' | VehicleStatus);
          }}
          renderValue={(selected) => {
            if (!selected) return <PlainStatusBadge label="همه وضعیت‌ها" />;
            return <VehicleStatusBadge status={selected} />;
          }}
          sx={{ width: { xs: '100%', md: 220 }, flexShrink: 0 }}
        >
          <MenuItem value="">
            <PlainStatusBadge label="همه وضعیت‌ها" />
          </MenuItem>
          {statusOptions
            .filter((item) => item.value !== '')
            .map((item) => (
              <MenuItem key={item.value} value={item.value}>
                <VehicleStatusBadge status={item.value as VehicleStatus} label={item.label} />
              </MenuItem>
            ))}
        </RtlSelectField>
        <ClearFiltersButton
          onClick={resetFilters}
          disabled={!hasActiveFilters}
        />
      </FilterPanel>

      {error && <ErrorState message={error} onRetry={reload} />}
      {!error && isMobile && loading && <LoadingState />}
      {!error && isMobile && !loading && vehicles.length === 0 && <EmptyState title="خودرویی یافت نشد" icon={Inbox} />}
      {!error && isMobile && !loading && vehicles.length > 0 && (
        <Stack spacing={1}>
          {vehicles.map((vehicle) => (
            <VehicleCard
              key={vehicle.id}
              vehicle={vehicle}
              onOpen={openVehicleDetail}
            />
          ))}
        </Stack>
      )}
      {!error && !isMobile && (
        <VehicleTable
          vehicles={vehicles}
          onOpen={openVehicleDetail}
          orderBy={orderBy}
          order={order}
          onSort={changeSort}
          loading={loading}
        />
      )}

      {!error && (
        <RtlPagination
          page={page}
          count={pageCount}
          onChange={setPage}
          totalItems={total}
          pageSize={PAGE_SIZE}
          disabled={loading}
        />
      )}

      <VehicleDetailModal
        vehicle={selected}
        open={Boolean(selected)}
        onClose={closeVehicleDetail}
      />
    </FeaturePage>
  );
}
