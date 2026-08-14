import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Card,
  CardContent,
  Divider,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { CheckCircleOutline, DoNotDisturbAlt } from '@mui/icons-material';
import { DirectionsCar, FactCheck, Handshake } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type { Fault, Inspection, RepairOrder, Vehicle, VehicleHandover } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

const HANDOVER_STATUS_LABELS: Record<string, string> = {
  WAITING_DRIVER_CONFIRMATION: 'در انتظار تایید راننده',
  ACCEPTED: 'تایید شده توسط راننده',
  REJECTED: 'رد شده توسط راننده',
};

const WORKSHOP_LABELS: Record<string, string> = {
  INTERNAL: 'تعمیرگاه مرکزی',
  EXTERNAL: 'تعمیرگاه بیرونی',
};

type StatusFilter = '' | 'WAITING_DRIVER_CONFIRMATION' | 'ACCEPTED' | 'REJECTED';

type DetailState = {
  handover: VehicleHandover;
  order: RepairOrder | null;
  fault: Fault | null;
  vehicle: Vehicle | null;
  checklists: Inspection[];
};

function normalizeList<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function statusLabel(status: string): string {
  return HANDOVER_STATUS_LABELS[status] ?? status;
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'WAITING_DRIVER_CONFIRMATION') return 'warning';
  if (status === 'ACCEPTED') return 'success';
  if (status === 'REJECTED') return 'error';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | null | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Driver inbox for accepting or rejecting repaired vehicle handover.
 */
export function HandoverPage() {
  const canEdit = useCanEdit();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [items, setItems] = useState<VehicleHandover[]>([]);
  const [vehicles, setVehicles] = useState<Map<string, Vehicle>>(new Map());
  const [orders, setOrders] = useState<Map<string, RepairOrder>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState<StatusFilter>('WAITING_DRIVER_CONFIRMATION');
  const [selected, setSelected] = useState<VehicleHandover | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [comment, setComment] = useState('');
  const [actionLoading, setActionLoading] = useState<'accept' | 'reject' | ''>('');
  const [success, setSuccess] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const list = normalizeList(await api.listVehicleHandovers());
      setItems(list);

      const vehicleIds = [...new Set(list.map((item) => item.vehicle_id))];
      const orderIds = [...new Set(list.map((item) => item.repair_order_id))];

      const [vehicleResults, orderResults] = await Promise.all([
        Promise.all(
          vehicleIds.map(async (id) => {
            try {
              return await api.getVehicle(id);
            } catch {
              return null;
            }
          }),
        ),
        Promise.all(
          orderIds.map(async (id) => {
            try {
              return await api.getRepairOrder(id);
            } catch {
              return null;
            }
          }),
        ),
      ]);

      const nextVehicles = new Map<string, Vehicle>();
      vehicleResults.forEach((vehicle) => {
        if (vehicle) nextVehicles.set(vehicle.id, vehicle);
      });
      setVehicles(nextVehicles);

      const nextOrders = new Map<string, RepairOrder>();
      orderResults.forEach((order) => {
        if (order) nextOrders.set(order.id, order);
      });
      setOrders(nextOrders);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : 'دریافت لیست تحویل انجام نشد');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => {
    if (!status) return items;
    return items.filter((item) => item.status === status);
  }, [items, status]);

  const kpi = useMemo(() => {
    const pending = items.filter(
      (item) => item.status === 'WAITING_DRIVER_CONFIRMATION',
    ).length;
    const accepted = items.filter((item) => item.status === 'ACCEPTED').length;
    const rejected = items.filter((item) => item.status === 'REJECTED').length;
    return { total: items.length, pending, accepted, rejected };
  }, [items]);

  const openDetail = async (handover: VehicleHandover) => {
    setSelected(handover);
    setComment('');
    setActionError('');
    setDetail(null);
    setDetailError('');
    setDetailLoading(true);
    try {
      const [freshOrder, vehicle, checklists] = await Promise.all([
        api.getRepairOrder(handover.repair_order_id).catch(() => null),
        api.getVehicle(handover.vehicle_id),
        api.listVehicleChecklists(handover.vehicle_id, { page: 1, pageSize: 10 }),
      ]);
      const fault = freshOrder?.fault_id
        ? await api.getFault(freshOrder.fault_id).catch(() => null)
        : null;
      setDetail({
        handover,
        order: freshOrder,
        fault,
        vehicle,
        checklists: normalizeList(checklists),
      });
      setVehicles((current) => {
        const next = new Map(current);
        next.set(vehicle.id, vehicle);
        return next;
      });
      if (freshOrder) {
        setOrders((current) => {
          const next = new Map(current);
          next.set(freshOrder.id, freshOrder);
          return next;
        });
      }
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات تحویل انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelected(null);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setComment('');
    setActionLoading('');
  };

  const confirm = async (accepted: boolean) => {
    const handover = detail?.handover ?? selected;
    if (!handover) return;
    setActionLoading(accepted ? 'accept' : 'reject');
    setActionError('');
    setSuccess('');
    try {
      await api.confirmVehicleHandover(handover.id, {
        accepted,
        comment: comment.trim() || undefined,
      });
      const acceptedMessage =
        detail?.order?.workshop_type === 'EXTERNAL'
          ? 'تحویل خودرو تایید شد و برای بارگذاری فاکتور و تایید نهایی ترابری ارسال شد.'
          : 'تحویل خودرو تایید شد و تعمیر تکمیل شد.';
      closeDetail();
      setSuccess(
        accepted
          ? acceptedMessage
          : 'تحویل رد شد و درخواست تعمیر جدید در صف ترابری ثبت شد.',
      );
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تصمیم تحویل انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const resetFilters = () => setStatus('WAITING_DRIVER_CONFIRMATION');
  const hasActiveFilters = status !== 'WAITING_DRIVER_CONFIRMATION';
  const canDecide = canEdit && detail?.handover.status === 'WAITING_DRIVER_CONFIRMATION';
  const workshopType = detail?.order?.workshop_type;

  const columns: Array<RtlDataTableColumn<VehicleHandover, string>> = [
    {
      key: 'plate',
      label: 'پلاک خودرو',
      minWidth: 140,
      render: (row) => (
        <Typography fontWeight={800}>
          {vehiclePlate(vehicles.get(row.vehicle_id), row.vehicle_id)}
        </Typography>
      ),
    },
    {
      key: 'workshop',
      label: 'نوع تعمیرگاه',
      render: (row) => {
        const type = orders.get(row.repair_order_id)?.workshop_type;
        return (
          <Typography variant="body2">
            {type ? WORKSHOP_LABELS[type] ?? type : '—'}
          </Typography>
        );
      },
    },
    {
      key: 'status',
      label: 'وضعیت',
      render: (row) => (
        <PlainStatusBadge label={statusLabel(row.status)} tone={statusTone(row.status)} />
      ),
    },
    {
      key: 'created',
      label: 'زمان ایجاد',
      render: (row) => formatDateTime(row.created_at),
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
          sx={{ height: 36, minHeight: 36, px: 1.5, minWidth: 72 }}
        >
          بررسی
        </Button>
      ),
    },
  ];

  const tabs = detail
    ? [
        {
          label: 'تصمیم تحویل',
          content: (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <DetailLine
                    label="پلاک"
                    value={vehiclePlate(detail.vehicle, detail.handover.vehicle_id)}
                  />
                  <DetailLine
                    label="شرح خرابی"
                    value={detail.fault?.description || '—'}
                  />
                  <DetailLine
                    label="نوع تعمیرگاه"
                    value={
                      workshopType
                        ? WORKSHOP_LABELS[workshopType] ?? workshopType
                        : '—'
                    }
                  />
                  <DetailLine
                    label="وضعیت تحویل"
                    value={statusLabel(detail.handover.status)}
                  />
                  <DetailLine
                    label="وضعیت سفارش تعمیر"
                    value={detail.order?.status || '—'}
                  />
                  <DetailLine
                    label="زمان ایجاد"
                    value={formatDateTime(detail.handover.created_at)}
                  />
                  {detail.handover.confirmed_at && (
                    <DetailLine
                      label="زمان تصمیم"
                      value={formatDateTime(detail.handover.confirmed_at)}
                    />
                  )}
                  {detail.handover.comment && (
                    <DetailLine label="یادداشت" value={detail.handover.comment} />
                  )}
                </CardContent>
              </Card>

              {!canDecide && (
                <Alert severity="info">تصمیم تحویل برای این مورد قبلا ثبت شده است.</Alert>
              )}
              {canDecide && workshopType === 'EXTERNAL' && (
                <Alert severity="info">
                  پس از تایید شما، واحد ترابری فاکتور تعمیرگاه بیرونی را ثبت می‌کند.
                </Alert>
              )}
              {actionError && <Alert severity="error">{actionError}</Alert>}

              {canDecide && (
                <Stack spacing={1.5}>
                  <Typography fontWeight={700}>آیا خودرو را تحویل می‌گیرید؟</Typography>
                  <RtlTextField
                    fullWidth
                    label="یادداشت (اختیاری)"
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    multiline
                    minRows={2}
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
                      loading={actionLoading === 'accept'}
                      disabled={actionLoading !== ''}
                      onClick={() => void confirm(true)}
                      sx={{ height: 40, minHeight: 40, px: 1.75, whiteSpace: 'nowrap' }}
                    >
                      بله — تایید تحویل
                    </Button>
                    <Button
                      color="error"
                      variant="contained"
                      size="small"
                      startIcon={<DoNotDisturbAlt />}
                      loading={actionLoading === 'reject'}
                      disabled={actionLoading !== ''}
                      onClick={() => void confirm(false)}
                      sx={{ height: 40, minHeight: 40, px: 1.75, whiteSpace: 'nowrap' }}
                    >
                      خیر — رد تحویل
                    </Button>
                  </Stack>
                </Stack>
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
                  value={
                    detail.vehicle.driver1?.name ||
                    detail.vehicle.driver1?.customer_number ||
                    '—'
                  }
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
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" gap={1}>
                      <Typography fontWeight={800}>
                        {formatDateTime(inspection.inspected_at)}
                      </Typography>
                      <PlainStatusBadge
                        label={
                          inspection.overall_result === 'PASS'
                            ? 'قبول'
                            : inspection.overall_result === 'FAIL'
                              ? 'مردود'
                              : inspection.overall_result
                        }
                        tone={inspection.overall_result === 'FAIL' ? 'error' : 'success'}
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      کیلومتر: {toFaNumber(inspection.odometer_value)}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          ) : (
            <EmptyState title="چک‌لیستی برای این خودرو ثبت نشده است" icon={FactCheck} />
          ),
        },
      ]
    : [];

  return (
    <FeaturePage>
      <PageHeader
        title="تحویل و تایید"
        breadcrumbs={[{ label: 'راننده' }, { label: 'تحویل و تایید' }]}
      />

      <KpiGrid mdColumns={4}>
        <KpiCard
          label="کل موارد"
          value={loading ? '...' : toFaNumber(kpi.total)}
          icon={Handshake}
        />
        <KpiCard
          label="در انتظار تایید"
          value={loading ? '...' : toFaNumber(kpi.pending)}
          icon={DirectionsCar}
          tone="warning"
        />
        <KpiCard
          label="تایید شده"
          value={loading ? '...' : toFaNumber(kpi.accepted)}
          icon={CheckCircleOutline}
          tone="success"
        />
        <KpiCard
          label="رد شده"
          value={loading ? '...' : toFaNumber(kpi.rejected)}
          icon={DoNotDisturbAlt}
          tone="error"
        />
      </KpiGrid>

      <FilterPanel>
        <RtlSelectField<StatusFilter>
          value={status}
          label="وضعیت"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => setStatus(event.target.value as StatusFilter)}
          sx={{ width: { xs: '100%', md: 280 }, flexShrink: 0 }}
        >
          <MenuItem value="">همه</MenuItem>
          <MenuItem value="WAITING_DRIVER_CONFIRMATION">در انتظار تایید</MenuItem>
          <MenuItem value="ACCEPTED">تایید شده</MenuItem>
          <MenuItem value="REJECTED">رد شده</MenuItem>
        </RtlSelectField>
        <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
      </FilterPanel>

      {success && <Alert severity="success">{success}</Alert>}
      {error && <ErrorState message={error} onRetry={() => void load()} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={visible}
          getRowKey={(row) => row.id}
          loading={loading}
          emptyMessage="موردی برای تایید تحویل نیست"
          emptyIcon={Handshake}
          minWidth={900}
        />
      )}

      {!error && isMobile && (
        <Stack spacing={1.25}>
          {!loading && visible.length === 0 && (
            <EmptyState title="موردی برای تایید تحویل نیست" icon={Handshake} />
          )}
          {!loading &&
            visible.map((row) => (
              <Card
                key={row.id}
                onClick={() => void openDetail(row)}
                sx={{ cursor: 'pointer' }}
              >
                <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Typography fontWeight={900}>
                      {vehiclePlate(vehicles.get(row.vehicle_id), row.vehicle_id)}
                    </Typography>
                    <PlainStatusBadge
                      label={statusLabel(row.status)}
                      tone={statusTone(row.status)}
                    />
                  </Stack>
                  <Divider sx={{ my: 1.25 }} />
                  <Typography variant="body2" color="text.secondary">
                    {formatDateTime(row.created_at)}
                  </Typography>
                </CardContent>
              </Card>
            ))}
        </Stack>
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={closeDetail}
        title={
          detail
            ? `تحویل خودرو — ${vehiclePlate(detail.vehicle, detail.handover.vehicle_id)}`
            : 'تحویل خودرو'
        }
        icon={DirectionsCar}
        tabs={tabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />
    </FeaturePage>
  );
}
