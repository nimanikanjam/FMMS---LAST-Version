import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardActionArea,
  CardContent,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  CheckCircleOutline,
  Close,
  DoNotDisturbAlt,
  Search,
  WarningAmber,
} from '@mui/icons-material';
import { DirectionsCar, FactCheck, ReportProblem } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type { Fault, Inspection, Vehicle } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';
import {
  checklistOverallLabel,
  checklistOverallTone,
  sortChecklistItems,
} from '../inspections/checklistDisplay';

const CHECKLIST_RESULT_LABELS: Record<string, string> = {
  PASS: 'قبول',
  FAIL: 'مردود',
  NOT_APPLICABLE: 'نامرتبط',
  NA: 'نامرتبط',
};

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
  APPROVED: 'تاییدشده',
};

const PAGE_SIZE = 50;

const FAULT_STATUS_LABELS: Record<string, string> = {
  OPEN: 'در انتظار تصمیم توزیع',
  AWAITING_TRANSPORT: 'تاییدشده توسط توزیع — صف ترابری',
  ASSIGNED: 'تخصیص‌یافته به تکنسین',
  IN_REPAIR: 'در تعمیر',
  CLOSED: 'بسته شده',
};

const SEVERITY_LABELS: Record<string, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

type DetailState = {
  fault: Fault;
  vehicle: Vehicle | null;
  checklists: Inspection[];
  faults: Fault[];
};

type FaultStatusFilter =
  | ''
  | 'OPEN'
  | 'AWAITING_TRANSPORT'
  | 'ASSIGNED'
  | 'IN_REPAIR'
  | 'CLOSED';

const STATUS_TAB_OPTIONS: ReadonlyArray<StatusTabOption<Exclude<FaultStatusFilter, ''>>> = [
  { value: '', label: 'همه' },
  { value: 'OPEN', label: 'در انتظار تصمیم' },
  { value: 'AWAITING_TRANSPORT', label: 'صف ترابری' },
  { value: 'ASSIGNED', label: 'تخصیص‌یافته' },
  { value: 'IN_REPAIR', label: 'در تعمیر' },
  { value: 'CLOSED', label: 'بسته شده' },
];

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function faultStatusLabel(status: string): string {
  return FAULT_STATUS_LABELS[status] ?? status;
}

function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? severity;
}

function severityTone(severity: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (severity === 'CRITICAL' || severity === 'HIGH') return 'error';
  if (severity === 'MEDIUM') return 'warning';
  if (severity === 'LOW') return 'neutral';
  return 'neutral';
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'CLOSED') return 'success';
  if (status === 'OPEN') return 'warning';
  if (status === 'AWAITING_TRANSPORT') return 'warning';
  if (status === 'ASSIGNED' || status === 'IN_REPAIR') return 'error';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

function faultItemLines(fault: Fault): string[] {
  const items = fault.items ?? [];
  if (items.length === 0) {
    return fault.description ? [fault.description] : [];
  }
  return items.map((item) => {
    const title = item.description || item.component || 'خرابی';
    const component =
      item.component && item.component !== item.description ? ` (${item.component})` : '';
    return `${title}${component}`;
  });
}

function faultSummaryLabel(fault: Fault): string {
  const lines = faultItemLines(fault);
  if (lines.length === 0) return fault.description || '—';
  if (lines.length === 1) return lines[0];
  return `${toFaNumber(lines.length)} خرابی`;
}

/**
 * Distribution unit queue for reviewing reported vehicle faults.
 */
export function DistributionFaultsPage() {
  const canEdit = useCanEdit();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [faults, setFaults] = useState<Fault[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [statusTab, setStatusTab] = useState<FaultStatusFilter>('');
  const [statusFilter, setStatusFilter] = useState<FaultStatusFilter>('');
  const status = statusTab || statusFilter;
  const [selected, setSelected] = useState<Fault | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');
  const [decisionNote, setDecisionNote] = useState('');
  const [decisionLoading, setDecisionLoading] = useState<'usable' | 'unusable' | ''>('');
  const [selectedChecklistId, setSelectedChecklistId] = useState<string | null>(null);
  const [selectedChecklist, setSelectedChecklist] = useState<Inspection | null>(null);
  const [checklistDetailLoading, setChecklistDetailLoading] = useState(false);
  const [checklistDetailError, setChecklistDetailError] = useState('');

  const vehicleMap = useMemo(() => {
    const map = new Map<string, Vehicle>();
    vehicles.forEach((vehicle) => map.set(String(vehicle.id), vehicle));
    return map;
  }, [vehicles]);

  const loadFaults = async () => {
    setLoading(true);
    setError('');
    try {
      const faultPage = await api.listFaults(undefined, { page: 1, pageSize: PAGE_SIZE });
      const nextFaults = faultPage.results ?? [];
      setFaults(nextFaults);

      const vehicleIds = [...new Set(nextFaults.map((fault) => fault.vehicle_id).filter(Boolean))];
      const vehicleResults = await Promise.all(
        vehicleIds.map(async (id) => {
          try {
            return await api.getVehicle(id);
          } catch {
            return null;
          }
        }),
      );
      setVehicles(vehicleResults.filter((item): item is Vehicle => Boolean(item)));
    } catch (err) {
      setFaults([]);
      setVehicles([]);
      setError(err instanceof Error ? err.message : 'کارتابل توزیع بارگذاری نشد');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFaults();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const visibleFaults = useMemo(() => {
    const needle = search.toLowerCase();
    return faults.filter((fault) => {
      if (status && fault.status !== status) return false;
      if (!needle) return true;
      const vehicle = vehicleMap.get(String(fault.vehicle_id));
      const itemText = (fault.items ?? [])
        .map((item) => `${item.description} ${item.component}`)
        .join(' ');
      return [
        fault.code,
        fault.description,
        itemText,
        fault.status,
        fault.severity,
        fault.sap_notification_number ?? '',
        vehicle?.license_plate ?? '',
        vehicle?.vehicle_number ?? '',
      ]
        .join(' ')
        .toLowerCase()
        .includes(needle);
    });
  }, [faults, search, status, vehicleMap]);

  const kpi = useMemo(() => {
    const openCount = faults.filter((item) => item.status === 'OPEN').length;
    const closedCount = faults.filter((item) => item.status === 'CLOSED').length;
    const criticalCount = faults.filter(
      (item) => item.severity === 'CRITICAL' || item.severity === 'HIGH',
    ).length;
    return {
      total: faults.length,
      openCount,
      closedCount,
      criticalCount,
    };
  }, [faults]);

  const openDetail = async (fault: Fault) => {
    setSelected(fault);
    setDecisionNote('');
    setDetail(null);
    setDetailError('');
    setActionError('');
    setDetailLoading(true);
    try {
      const [freshFault, vehicle, checklists, vehicleFaults] = await Promise.all([
        api.getFault(fault.id),
        api.getVehicle(fault.vehicle_id),
        api.listVehicleChecklists(fault.vehicle_id, { page: 1, pageSize: 20 }),
        api.listFaults(fault.vehicle_id, { page: 1, pageSize: 20 }),
      ]);
      setDetail({
        fault: freshFault,
        vehicle,
        checklists: normalizePaginated(checklists),
        faults: vehicleFaults.results ?? [],
      });
      setVehicles((current) => {
        if (current.some((item) => item.id === vehicle.id)) return current;
        return [...current, vehicle];
      });
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات خرابی انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeChecklistDetail = () => {
    setSelectedChecklistId(null);
    setSelectedChecklist(null);
    setChecklistDetailError('');
  };

  const openChecklistDetail = async (inspectionId: string) => {
    setSelectedChecklistId(inspectionId);
    setSelectedChecklist(null);
    setChecklistDetailError('');
    setChecklistDetailLoading(true);
    try {
      setSelectedChecklist(await api.getInspection(inspectionId));
    } catch (err) {
      setChecklistDetailError(
        err instanceof Error ? err.message : 'دریافت جزئیات چک‌لیست انجام نشد',
      );
    } finally {
      setChecklistDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelected(null);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setDecisionNote('');
    closeChecklistDetail();
  };

  const decide = async (decision: 'usable' | 'unusable') => {
    const fault = detail?.fault ?? selected;
    if (!fault) return;
    setDecisionLoading(decision);
    setActionError('');
    setSuccess('');
    try {
      const updated =
        decision === 'usable'
          ? await api.markFaultVehicleUsable(fault.id, decisionNote)
          : await api.markFaultVehicleUnusable(fault.id, decisionNote);
      setFaults((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      closeDetail();
      setSuccess(
        decision === 'usable'
          ? 'خرابی بسته شد. راننده می‌تواند گرفتن خودرو و خروج از مرکز را تایید کند.'
          : 'خودرو خارج از سرویس شد و به صف ترابری ارسال شد.',
      );
      await loadFaults();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تصمیم توزیع انجام نشد');
    } finally {
      setDecisionLoading('');
    }
  };

  const resetFilters = () => {
    setSearchInput('');
    setSearch('');
    setStatusFilter('');
  };

  const hasActiveFilters = search !== '' || statusFilter !== '';
  const decisionDisabled = detail?.fault.status !== 'OPEN';

  const columns: Array<RtlDataTableColumn<Fault, string>> = [
    {
      key: 'plate',
      label: 'پلاک خودرو',
      minWidth: 140,
      render: (fault) => (
        <Typography fontWeight={800}>
          {vehiclePlate(vehicleMap.get(String(fault.vehicle_id)), fault.vehicle_id)}
        </Typography>
      ),
    },
    {
      key: 'description',
      label: 'شرح خرابی',
      minWidth: 260,
      render: (fault) => (
        <Stack spacing={0.35}>
          <Typography fontWeight={800}>{faultSummaryLabel(fault)}</Typography>
          <Typography variant="caption" color="text.secondary">
            {fault.code} · {formatDateTime(fault.reported_at || fault.created_at)}
          </Typography>
        </Stack>
      ),
    },
    {
      key: 'severity',
      label: 'شدت',
      render: (fault) => (
        <PlainStatusBadge
          label={severityLabel(fault.severity)}
          tone={severityTone(fault.severity)}
        />
      ),
    },
    {
      key: 'sap',
      label: 'SAP',
      render: (fault) => (
        <Typography variant="body2" color="text.secondary">
          {fault.sap_notification_number || 'در صف ارسال'}
        </Typography>
      ),
    },
    {
      key: 'status',
      label: 'وضعیت',
      render: (fault) => (
        <PlainStatusBadge
          label={faultStatusLabel(fault.status)}
          tone={statusTone(fault.status)}
        />
      ),
    },
    {
      key: 'actions',
      label: 'عملیات',
      align: 'center',
      render: (fault) => (
        <Button
          size="small"
          variant="outlined"
          onClick={() => void openDetail(fault)}
          sx={{ height: 36, minHeight: 36, px: 1.5, minWidth: 72 }}
        >
          بررسی
        </Button>
      ),
    },
  ];

  const checklistItemColumns: Array<
    RtlDataTableColumn<
      Inspection['items'][number],
      'category' | 'description' | 'result' | 'severity' | 'notes'
    >
  > = [
    { key: 'category', label: 'دسته', render: (row) => row.category || '—' },
    { key: 'description', label: 'شرح', render: (row) => row.description || '—' },
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

  const tabs = detail
    ? [
        {
          label: 'جزئیات خرابی',
          content: (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <DetailLine
                    label="پلاک"
                    value={vehiclePlate(detail.vehicle ?? undefined, detail.fault.vehicle_id)}
                  />
                  <DetailLine
                    label="خلاصه"
                    value={
                      (detail.fault.items?.length ?? 0) > 1
                        ? detail.fault.description
                        : detail.fault.description || '—'
                    }
                  />
                  <DetailLine label="کد خرابی" value={detail.fault.code} />
                  <DetailLine label="شدت کلی" value={severityLabel(detail.fault.severity)} />
                  <DetailLine label="وضعیت" value={faultStatusLabel(detail.fault.status)} />
                  <DetailLine
                    label="PM Notification"
                    value={detail.fault.sap_notification_number || 'در صف ارسال'}
                  />
                  <DetailLine
                    label="زمان ثبت"
                    value={formatDateTime(detail.fault.reported_at || detail.fault.created_at)}
                  />
                </CardContent>
              </Card>

              {(detail.fault.items?.length ?? 0) > 0 ? (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={800} mb={1.25}>
                      شرح خرابی‌ها ({toFaNumber(detail.fault.items!.length)})
                    </Typography>
                    <Stack spacing={1.25} divider={<Divider flexItem />}>
                      {detail.fault.items!.map((item, index) => (
                        <Stack key={item.id} spacing={0.5}>
                          <Typography fontWeight={800}>
                            {toFaNumber(index + 1)}. {item.description || item.component}
                          </Typography>
                          {item.component && item.component !== item.description ? (
                            <DetailLine label="قطعه / بخش" value={item.component} />
                          ) : null}
                          <DetailLine label="شدت" value={severityLabel(item.severity)} />
                        </Stack>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              ) : (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={800} mb={1}>
                      شرح خرابی
                    </Typography>
                    <Typography>{detail.fault.description || '—'}</Typography>
                  </CardContent>
                </Card>
              )}
              {actionError && <Alert severity="error">{actionError}</Alert>}
              {decisionDisabled ? (
                <Alert
                  severity="info"
                  icon={false}
                  sx={{
                    py: 2,
                    px: 2,
                    border: '1px solid',
                    borderColor: 'info.main',
                    bgcolor: (theme) =>
                      theme.palette.mode === 'dark'
                        ? 'rgba(2, 136, 209, 0.16)'
                        : 'rgba(2, 136, 209, 0.08)',
                    '& .MuiAlert-message': { width: '100%' },
                  }}
                >
                  <Typography
                    fontWeight={900}
                    fontSize={{ xs: '1rem', sm: '1.1rem' }}
                    color="info.dark"
                    textAlign="center"
                  >
                    تصمیم توزیع برای این خرابی قبلاً ثبت شده است.
                  </Typography>
                  {detail.fault.distribution_decision_note ? (
                    <Typography
                      mt={1}
                      textAlign="center"
                      color="text.secondary"
                      fontWeight={600}
                    >
                      یادداشت: {detail.fault.distribution_decision_note}
                    </Typography>
                  ) : null}
                  <Typography
                    mt={0.75}
                    textAlign="center"
                    variant="body2"
                    color="text.secondary"
                    fontWeight={700}
                  >
                    وضعیت فعلی: {faultStatusLabel(detail.fault.status)}
                  </Typography>
                </Alert>
              ) : !canEdit ? null : (
                <>
                  <RtlTextField
                    fullWidth
                    label="یادداشت/دلیل تصمیم توزیع"
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                  />
                  <Stack
                    direction={{ xs: 'column', sm: 'row' }}
                    spacing={1}
                    justifyContent="flex-end"
                    useFlexGap
                  >
                    <Button
                      color="success"
                      variant="contained"
                      size="small"
                      startIcon={<CheckCircleOutline />}
                      loading={decisionLoading === 'unusable'}
                      onClick={() => void decide('unusable')}
                      sx={{
                        height: 40,
                        minHeight: 40,
                        px: 1.75,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      بله — تایید خرابی
                    </Button>
                    <Button
                      color="error"
                      variant="contained"
                      size="small"
                      startIcon={<DoNotDisturbAlt />}
                      loading={decisionLoading === 'usable'}
                      disabled={!decisionNote.trim()}
                      onClick={() => void decide('usable')}
                      sx={{
                        height: 40,
                        minHeight: 40,
                        px: 1.75,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      خیر — رد خرابی
                    </Button>
                  </Stack>
                </>
              )}
            </Stack>
          ),
        },
        {
          label: 'اطلاعات خودرو',
          content: detail.vehicle ? (
            <Card variant="outlined">
              <CardContent>
                <DetailLine label="پلاک" value={detail.vehicle.license_plate} />
                <DetailLine label="شماره خودرو" value={detail.vehicle.vehicle_number} />
                <DetailLine
                  label="وضعیت"
                  value={<VehicleStatusBadge status={detail.vehicle.status} />}
                />
                <DetailLine
                  label="راننده اصلی"
                  value={detail.vehicle.driver1?.name || detail.vehicle.driver1?.customer_number || '—'}
                />
                <DetailLine
                  label="کمک راننده"
                  value={detail.vehicle.driver2?.name || detail.vehicle.driver2?.customer_number || '—'}
                />
              </CardContent>
            </Card>
          ) : (
            <EmptyState title="اطلاعات خودرو در دسترس نیست" />
          ),
        },
        {
          label: 'چک‌لیست‌های روزانه',
          content: detail.checklists.length ? (
            <Stack spacing={1}>
              {detail.checklists.map((inspection) => (
                <Card key={inspection.id} variant="outlined">
                  <CardActionArea
                    onClick={() => void openChecklistDetail(inspection.id)}
                    sx={{ alignItems: 'stretch' }}
                  >
                    <CardContent>
                      <Stack direction="row" justifyContent="space-between" gap={1} alignItems="center">
                        <Typography fontWeight={800}>
                          {formatDateTime(inspection.inspected_at)}
                        </Typography>
                        <PlainStatusBadge
                          tone={checklistOverallTone(
                            inspection.has_failures,
                            inspection.overall_result,
                          )}
                          label={checklistOverallLabel(
                            inspection.has_failures,
                            inspection.overall_result,
                            CHECKLIST_RESULT_LABELS,
                          )}
                        />
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        کیلومتر: {toFaNumber(inspection.odometer_value)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        موارد ناموفق:{' '}
                        {toFaNumber(
                          inspection.items.filter((item) => item.result === 'FAIL').length,
                        )}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="primary.main"
                        fontWeight={800}
                        mt={1}
                      >
                        مشاهده جزئیات
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              ))}
            </Stack>
          ) : (
            <EmptyState title="چک‌لیستی برای این خودرو ثبت نشده است" icon={FactCheck} />
          ),
        },
        {
          label: 'تاریخچه خرابی‌ها',
          content: (() => {
            const historyFaults = detail.faults.filter((fault) => fault.id !== detail.fault.id);
            if (!historyFaults.length) {
              return <EmptyState title="خرابی قبلی برای این خودرو ثبت نشده است" />;
            }
            return (
              <Stack spacing={1}>
                {historyFaults.map((fault) => (
                  <Card key={fault.id} variant="outlined">
                    <CardContent>
                      <Typography fontWeight={800}>{fault.description}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {fault.code} · {faultStatusLabel(fault.status)} ·{' '}
                        {formatDateTime(fault.reported_at || fault.created_at)}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            );
          })(),
        },
      ]
    : [];

  return (
    <FeaturePage>
      <PageHeader
        title="کارتابل توزیع"
        breadcrumbs={[{ label: 'توزیع خودرو' }, { label: 'کارتابل توزیع' }]}
      />

      <KpiGrid mdColumns={4}>
        <KpiCard
          label="کل خرابی‌ها"
          value={toFaNumber(kpi.total)}
          icon={ReportProblem}
        />
        <KpiCard
          label="در انتظار تصمیم"
          value={toFaNumber(kpi.openCount)}
          icon={WarningAmber}
          tone="warning"
        />
        <KpiCard
          label="شدت بالا / بحرانی"
          value={toFaNumber(kpi.criticalCount)}
          icon={ReportProblem}
          tone="error"
        />
        <KpiCard
          label="بسته شده"
          value={toFaNumber(kpi.closedCount)}
          icon={CheckCircleOutline}
          tone="success"
        />
      </KpiGrid>

      <StatusFilterTabs
        value={statusTab}
        options={STATUS_TAB_OPTIONS}
        onChange={(next) => {
          setStatusTab(next);
          if (next) {
            setStatusFilter('');
            setSearchInput('');
            setSearch('');
          }
        }}
        ariaLabel="وضعیت توزیع خودرو"
      />

      {statusTab === '' && (
        <FilterPanel>
          <RtlTextField
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            label="جستجو"
            placeholder="پلاک، شرح، کد یا SAP"
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search fontSize="small" />
                </InputAdornment>
              ),
            }}
            sx={{ width: { xs: '100%', md: 300 }, flexShrink: 0 }}
          />
          <RtlSelectField<FaultStatusFilter>
            value={statusFilter}
            label="وضعیت"
            size="small"
            fullWidth={false}
            displayEmpty
            onChange={(event) => setStatusFilter(event.target.value as FaultStatusFilter)}
            renderValue={(selected) => {
              if (!selected) return <PlainStatusBadge label="همه وضعیت‌ها" />;
              return (
                <PlainStatusBadge
                  label={faultStatusLabel(String(selected))}
                  tone={statusTone(String(selected))}
                />
              );
            }}
            sx={{ width: { xs: '100%', md: 240 }, flexShrink: 0 }}
          >
            <MenuItem value="">
              <PlainStatusBadge label="همه وضعیت‌ها" />
            </MenuItem>
            {(Object.keys(FAULT_STATUS_LABELS) as Array<Exclude<FaultStatusFilter, ''>>).map(
              (value) => (
                <MenuItem key={value} value={value}>
                  <PlainStatusBadge label={faultStatusLabel(value)} tone={statusTone(value)} />
                </MenuItem>
              ),
            )}
          </RtlSelectField>
          <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
        </FilterPanel>
      )}

      {success && <Alert severity="success">{success}</Alert>}
      {error && <ErrorState message={error} onRetry={() => void loadFaults()} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={visibleFaults}
          getRowKey={(fault) => fault.id}
          loading={loading}
          emptyMessage="خرابی یافت نشد"
          emptySubtitle="با تغییر فیلتر یا جستجو دوباره تلاش کنید"
          emptyIcon={ReportProblem}
          minWidth={980}
        />
      )}

      {!error && isMobile && (
        <Stack spacing={1.25}>
          {loading &&
            Array.from({ length: 4 }).map((_, index) => (
              <Card key={index}>
                <CardContent sx={{ p: 1.75 }}>
                  <Typography color="text.secondary">در حال بارگذاری...</Typography>
                </CardContent>
              </Card>
            ))}
          {!loading && visibleFaults.length === 0 && (
            <EmptyState
              title="خرابی یافت نشد"
              subtitle="با تغییر فیلتر یا جستجو دوباره تلاش کنید"
              icon={ReportProblem}
            />
          )}
          {!loading &&
            visibleFaults.map((fault) => (
              <Card
                key={fault.id}
                onClick={() => void openDetail(fault)}
                sx={{ cursor: 'pointer' }}
              >
                <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    gap={1.5}
                    alignItems="flex-start"
                  >
                    <Box minWidth={0}>
                      <Typography fontWeight={900} noWrap>
                        {vehiclePlate(vehicleMap.get(String(fault.vehicle_id)), fault.vehicle_id)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {fault.description}
                      </Typography>
                    </Box>
                    <PlainStatusBadge
                      label={faultStatusLabel(fault.status)}
                      tone={statusTone(fault.status)}
                    />
                  </Stack>
                  <Divider sx={{ my: 1.25 }} />
                  <Typography variant="body2" color="text.secondary">
                    شدت: {severityLabel(fault.severity)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    زمان: {formatDateTime(fault.reported_at || fault.created_at)}
                  </Typography>
                </CardContent>
              </Card>
            ))}
        </Stack>
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={closeDetail}
        title={detail?.fault.description || selected?.description || 'جزئیات خرابی'}
        icon={DirectionsCar}
        tabs={tabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />

      <Dialog
        open={Boolean(selectedChecklistId)}
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
          <Stack direction="row" alignItems="center" gap={1}>
            <FactCheck fontSize="small" color="primary" />
            جزئیات چک‌لیست
          </Stack>
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
                {selectedChecklist.driver?.name && (
                  <DetailLine label="راننده" value={selectedChecklist.driver.name} />
                )}
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
    </FeaturePage>
  );
}
