import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Divider,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import {
  Add,
  AssignmentTurnedIn,
  AttachFile,
  CheckCircleOutline,
  DeleteOutline,
  ReceiptLong,
  Save,
} from '@mui/icons-material';
import { DirectionsCar, FactCheck } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { FeaturePage } from '../../components/FeaturePage';
import { PageHeader } from '../../components/PageHeader';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlTextField } from '../../components/RtlTextField';
import { ErrorState } from '../../components/States';
import { AppTabs } from '../../components/AppTabs';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type { ExternalWorkshopAssignment, RepairOrder, Vehicle } from '../../types/fmms';
import { formatDateTime } from '../../utils/format';

type TabKey = 'driver' | 'transport';
type DriverExternalFilter = '' | 'WAITING_DELIVERY' | 'IN_REPAIR' | 'COMPLETED';
type TransportInvoiceFilter = '' | 'WAITING_PICKUP' | 'WAITING_INVOICE' | 'DRAFT' | 'COMPLETED';
const DRIVER_STATUS_TABS: ReadonlyArray<StatusTabOption<Exclude<DriverExternalFilter, ''>>> = [
  { value: '', label: 'همه' },
  { value: 'WAITING_DELIVERY', label: 'در انتظار تحویل' },
  { value: 'IN_REPAIR', label: 'در تعمیرگاه / دریافت خودرو' },
  { value: 'COMPLETED', label: 'تکمیل‌شده' },
];
const TRANSPORT_INVOICE_TABS: ReadonlyArray<
  StatusTabOption<Exclude<TransportInvoiceFilter, ''>>
> = [
  { value: '', label: 'همه' },
  { value: 'WAITING_PICKUP', label: 'در انتظار دریافت خودرو' },
  { value: 'WAITING_INVOICE', label: 'در انتظار ثبت فاکتور' },
  { value: 'DRAFT', label: 'پیش‌نویس فاکتور' },
  { value: 'COMPLETED', label: 'تکمیل‌شده' },
];
const API_ORIGIN = (() => {
  try {
    return new URL(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').origin;
  } catch {
    return '';
  }
})();

function normalizeList<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function statusLabel(item: ExternalWorkshopAssignment): string {
  if (item.status === 'CANCELLED') return 'لغو شده';
  if (item.status === 'COMPLETED') return 'تکمیل شده';
  if (!item.delivery) return 'در انتظار تحویل به تعمیرگاه';
  if (!item.pickup) return 'در تعمیرگاه بیرونی';
  if (!item.review || item.review.status === 'DRAFT') return 'در انتظار ثبت فاکتور';
  return 'آماده بستن';
}

function invoiceStateFor(item: ExternalWorkshopAssignment): Exclude<TransportInvoiceFilter, ''> {
  if (item.status === 'COMPLETED' || item.review?.status === 'COMPLETED') return 'COMPLETED';
  if (!item.pickup) return 'WAITING_PICKUP';
  if (!item.review) return 'WAITING_INVOICE';
  return 'DRAFT';
}

function driverStateFor(item: ExternalWorkshopAssignment): Exclude<DriverExternalFilter, ''> {
  if (item.status === 'COMPLETED') return 'COMPLETED';
  if (!item.delivery) return 'WAITING_DELIVERY';
  return 'IN_REPAIR';
}

function driverStateLabel(item: ExternalWorkshopAssignment): string {
  const state = driverStateFor(item);
  if (state === 'WAITING_DELIVERY') return 'در انتظار تحویل به تعمیرگاه';
  if (state === 'IN_REPAIR') return item.pickup ? 'خودرو دریافت شده' : 'در تعمیرگاه بیرونی';
  return 'تکمیل‌شده';
}

function driverStateTone(item: ExternalWorkshopAssignment): 'neutral' | 'warning' | 'success' {
  const state = driverStateFor(item);
  if (state === 'COMPLETED') return 'success';
  if (state === 'WAITING_DELIVERY') return 'warning';
  return item.pickup ? 'success' : 'neutral';
}

function invoiceStateLabel(item: ExternalWorkshopAssignment): string {
  const state = invoiceStateFor(item);
  if (state === 'WAITING_PICKUP') return 'در انتظار دریافت خودرو';
  if (state === 'WAITING_INVOICE') return 'در انتظار ثبت فاکتور';
  if (state === 'DRAFT') return 'پیش‌نویس فاکتور';
  return 'تکمیل‌شده';
}

function invoiceStateTone(item: ExternalWorkshopAssignment): 'neutral' | 'warning' | 'success' {
  const state = invoiceStateFor(item);
  if (state === 'COMPLETED') return 'success';
  if (state === 'WAITING_PICKUP') return 'neutral';
  return 'warning';
}

function cleanAttachmentPath(value: string): string {
  return value.trim().replace(/^"+|"+$/g, '');
}

function attachmentFileName(value: string): string {
  const cleanValue = cleanAttachmentPath(value);
  if (!cleanValue) return '';
  const path = cleanValue.split(/[?#]/)[0];
  const fileName = path.split('/').filter(Boolean).pop() ?? cleanValue;
  try {
    return decodeURIComponent(fileName);
  } catch {
    return fileName;
  }
}

function attachmentHref(value: string): string {
  const cleanValue = cleanAttachmentPath(value);
  if (!cleanValue) return '';
  if (/^https?:\/\//i.test(cleanValue)) return cleanValue;
  if (cleanValue.startsWith('/media/') && API_ORIGIN) return `${API_ORIGIN}${cleanValue}`;
  if (cleanValue.startsWith('/')) return cleanValue;
  return '';
}

const emptyDelivery = {
  workshop_name: '',
  workshop_address: '',
  workshop_phone: '',
  vehicle_odometer: '',
  notes: '',
};

const emptyPickup = {
  vehicle_odometer: '',
  notes: '',
};

const emptyReview = {
  invoice_attachment: '',
  repair_cost: '',
  additional_notes: '',
};

type ServiceLine = { description: string; labor_hours: string; cost: string; notes: string };
type PartLine = { name: string; quantity: string; cost: string };

const blankService = (): ServiceLine => ({ description: '', labor_hours: '', cost: '', notes: '' });
const blankPart = (): PartLine => ({ name: '', quantity: '1', cost: '' });

export function ExternalWorkshopPage({ mode }: { mode?: TabKey }) {
  const canEdit = useCanEdit();
  const [tab, setTab] = useState<TabKey>(mode ?? 'driver');
  const activeTab = mode ?? tab;
  const [items, setItems] = useState<ExternalWorkshopAssignment[]>([]);
  const [vehicles, setVehicles] = useState<Map<string, Vehicle>>(new Map());
  const [orders, setOrders] = useState<Map<string, RepairOrder>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<ExternalWorkshopAssignment | null>(null);
  const [delivery, setDelivery] = useState(emptyDelivery);
  const [pickup, setPickup] = useState(emptyPickup);
  const [review, setReview] = useState(emptyReview);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [serviceLines, setServiceLines] = useState<ServiceLine[]>([]);
  const [partLines, setPartLines] = useState<PartLine[]>([]);
  const [draftService, setDraftService] = useState<ServiceLine>(blankService());
  const [draftPart, setDraftPart] = useState<PartLine>(blankPart());
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [driverFilter, setDriverFilter] = useState<DriverExternalFilter>('');
  const [invoiceFilter, setInvoiceFilter] = useState<TransportInvoiceFilter>('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const list = normalizeList(
        await api.listExternalWorkshopAssignments({
          page: 1,
          pageSize: 100,
        }),
      );
      setItems(list);
      const [vehicleResults, orderResults] = await Promise.all([
        Promise.all(list.map((item) => api.getVehicle(item.vehicle_id).catch(() => null))),
        Promise.all(list.map((item) => api.getRepairOrder(item.repair_order_id).catch(() => null))),
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
      setError(err instanceof Error ? err.message : 'دریافت لیست تعمیرگاه بیرونی انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => {
    if (activeTab === 'driver') {
      return items.filter((item) => {
        if (item.status === 'CANCELLED') return false;
        return driverFilter === '' || driverStateFor(item) === driverFilter;
      });
    }
    return items.filter((item) => {
      if (item.status === 'CANCELLED' || !item.delivery) return false;
      return invoiceFilter === '' || invoiceStateFor(item) === invoiceFilter;
    });
  }, [items, activeTab, driverFilter, invoiceFilter]);

  const openDetail = async (item: ExternalWorkshopAssignment) => {
    setActionError('');
    setSuccess('');
    const fresh = await api.getExternalWorkshopAssignment(item.id).catch(() => item);
    setSelected(fresh);
    setDelivery({
      workshop_name: fresh.delivery?.workshop_name ?? fresh.workshop_name ?? '',
      workshop_address: fresh.delivery?.workshop_address ?? fresh.workshop_address ?? '',
      workshop_phone: fresh.delivery?.workshop_phone ?? '',
      vehicle_odometer: fresh.delivery ? String(fresh.delivery.vehicle_odometer) : '',
      notes: fresh.delivery?.notes ?? '',
    });
    setPickup({
      vehicle_odometer: fresh.pickup ? String(fresh.pickup.vehicle_odometer) : '',
      notes: fresh.pickup?.notes ?? '',
    });
    setReview({
      invoice_attachment: fresh.review?.invoice_attachment ?? '',
      repair_cost: fresh.review?.repair_cost ? String(fresh.review.repair_cost) : '',
      additional_notes: fresh.review?.additional_notes ?? '',
    });
    setInvoiceFile(null);
    setServiceLines(
      fresh.review?.repair_services?.length
        ? fresh.review.repair_services.map((item) => ({
            description: String(item.description ?? ''),
            labor_hours: String(item.labor_hours ?? ''),
            cost: String(item.cost ?? ''),
            notes: String(item.notes ?? ''),
          }))
        : [],
    );
    setPartLines(
      fresh.review?.replaced_parts?.length
        ? fresh.review.replaced_parts.map((item) => ({
            name: String(item.material_number ?? item.name ?? ''),
            quantity: String(item.quantity ?? '1'),
            cost: String(item.cost ?? ''),
          }))
        : [],
    );
    setDraftService(blankService());
    setDraftPart(blankPart());
  };

  const selectedVehicle = selected ? vehicles.get(selected.vehicle_id) : null;
  const selectedOrder = selected ? orders.get(selected.repair_order_id) : null;
  const selectedReviewCompleted = selected?.status === 'COMPLETED';
  const canEditSelectedReview =
    canEdit && Boolean(selected?.pickup && selected.status !== 'COMPLETED');

  const submitDelivery = async () => {
    if (!selected) return;
    setActionLoading('delivery');
    setActionError('');
    try {
      const updated = await api.confirmExternalWorkshopDelivery(selected.id, {
        delivery_datetime: new Date().toISOString(),
        workshop_name: delivery.workshop_name,
        workshop_address: delivery.workshop_address,
        workshop_phone: delivery.workshop_phone,
        vehicle_odometer: Number(delivery.vehicle_odometer),
        notes: delivery.notes,
      });
      setSelected(updated);
      setSuccess('تحویل خودرو ثبت شد و تعمیر خارجی شروع شد.');
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تحویل انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const submitPickup = async () => {
    if (!selected) return;
    setActionLoading('pickup');
    setActionError('');
    try {
      const updated = await api.confirmExternalWorkshopPickup(selected.id, {
        pickup_datetime: new Date().toISOString(),
        vehicle_odometer: Number(pickup.vehicle_odometer),
        notes: pickup.notes,
      });
      setSelected(updated);
      setSuccess('دریافت خودرو ثبت شد و خودرو در ناوگان فعال شد.');
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت دریافت انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const buildReviewPayload = () => ({
    repair_services: serviceLines
      .map((line) => ({
        description: line.description.trim(),
        labor_hours: line.labor_hours || null,
        cost: line.cost || null,
        notes: line.notes.trim(),
      }))
      .filter((line) => line.description),
    replaced_parts: partLines
      .map((line) => ({
        name: line.name.trim(),
        quantity: line.quantity || '1',
        cost: line.cost || null,
        unit_of_measure: '-',
      }))
      .filter((line) => line.name),
    repair_cost: review.repair_cost || null,
    additional_notes: review.additional_notes,
    invoice_file: invoiceFile,
  });

  const saveReview = async () => {
    if (!selected) return;
    setActionLoading('review');
    setActionError('');
    try {
      const updated = await api.reviewExternalRepair(selected.id, buildReviewPayload());
      setSelected(updated);
      setInvoiceFile(null);
      setReview({
        invoice_attachment: updated.review?.invoice_attachment ?? '',
        repair_cost: updated.review?.repair_cost ? String(updated.review.repair_cost) : '',
        additional_notes: updated.review?.additional_notes ?? '',
      });
      setSuccess('پیش‌نویس اطلاعات ترابری ذخیره شد.');
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ذخیره فاکتور انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const closeWorkflow = async () => {
    if (!selected) return;
    const reviewPayload = buildReviewPayload();
    const missing: string[] = [];
    if (!reviewPayload.repair_services.length) missing.push('حداقل یک خدمت انجام‌شده');
    if (!reviewPayload.repair_cost) missing.push('هزینه تعمیر');
    if (missing.length) {
      setActionError(`برای بستن درخواست، این موارد را کامل کنید: ${missing.join('، ')}.`);
      return;
    }
    setActionLoading('close');
    setActionError('');
    try {
      await api.reviewExternalRepair(selected.id, reviewPayload);
      await api.closeExternalRepair(selected.id);
      setSelected(null);
      setSuccess('درخواست تعمیر خارجی بسته شد.');
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'بستن workflow انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const columns: Array<RtlDataTableColumn<ExternalWorkshopAssignment, string>> = [
    {
      key: 'vehicle',
      label: 'خودرو',
      render: (row) => {
        const vehicle = vehicles.get(row.vehicle_id);
        return <Typography fontWeight={800}>{vehicle?.license_plate || row.vehicle_id.slice(0, 8)}</Typography>;
      },
    },
    {
      key: 'workshop',
      label: 'تعمیرگاه',
      render: (row) => row.delivery?.workshop_name || row.workshop_name || 'ثبت توسط راننده',
    },
    {
      key: 'status',
      label: activeTab === 'transport' ? 'وضعیت فاکتور' : 'مرحله',
      render: (row) => (
        <PlainStatusBadge
          label={activeTab === 'transport' ? invoiceStateLabel(row) : driverStateLabel(row)}
          tone={activeTab === 'transport' ? invoiceStateTone(row) : driverStateTone(row)}
        />
      ),
    },
    ...(activeTab === 'transport' ? [{
      key: 'cost',
      label: 'هزینه تعمیر',
      render: (row: ExternalWorkshopAssignment) => row.review?.repair_cost || '—',
    }] : []),
    {
      key: 'date',
      label: 'تاریخ ارجاع',
      render: (row) => formatDateTime(row.assignment_date),
    },
    {
      key: 'actions',
      label: 'عملیات',
      align: 'center',
      render: (row) => (
        <Button size="small" variant="outlined" onClick={() => void openDetail(row)}>
          {row.status === 'COMPLETED' ? 'مشاهده' : 'بررسی'}
        </Button>
      ),
    },
  ];

  return (
    <FeaturePage>
      <PageHeader
        title={activeTab === 'transport' ? 'ثبت فاکتور تعمیرگاه بیرونی' : 'تعمیرگاه بیرونی'}
        description={
          activeTab === 'transport'
            ? 'ثبت فاکتور، خدمات انجام‌شده، قطعات تعویضی و هزینه تعمیر بیرونی'
            : 'ثبت تحویل خودرو به تعمیرگاه و دریافت خودرو پس از تعمیر'
        }
        breadcrumbs={[
          {
            label: activeTab === 'transport' ? 'ترابری' : 'راننده',
          },
          {
            label:
              activeTab === 'transport'
                ? 'ثبت فاکتور تعمیرگاه بیرونی'
                : 'تحویل تعمیرگاه بیرونی',
          },
        ]}
      />
      {!mode && (
        <AppTabs
          value={tab}
          onChange={(value) => setTab(value)}
          ariaLabel="حالت تعمیرگاه بیرونی"
          items={[
            { value: 'driver', label: 'کارتابل راننده', icon: <DirectionsCar fontSize="small" /> },
            { value: 'transport', label: 'ثبت فاکتور', icon: <FactCheck fontSize="small" /> },
          ]}
          sx={{ mb: 2 }}
        />
      )}
      {activeTab === 'driver' && (
        <StatusFilterTabs
          value={driverFilter}
          options={DRIVER_STATUS_TABS}
          onChange={(next) => setDriverFilter(next as DriverExternalFilter)}
          ariaLabel="وضعیت تحویل تعمیرگاه بیرونی"
        />
      )}
      {activeTab === 'transport' && (
        <StatusFilterTabs
          value={invoiceFilter}
          options={TRANSPORT_INVOICE_TABS}
          onChange={(next) => setInvoiceFilter(next as TransportInvoiceFilter)}
          ariaLabel="وضعیت فاکتور تعمیرگاه بیرونی"
        />
      )}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
      {error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : (
        <RtlDataTable
          columns={columns}
          rows={visible}
          getRowKey={(row) => row.id}
          loading={loading}
          emptyMessage={
            activeTab === 'transport'
              ? 'فاکتوری برای ثبت تعمیرگاه بیرونی نیست'
              : 'درخواستی برای تحویل تعمیرگاه بیرونی نیست'
          }
          emptyIcon={activeTab === 'transport' ? ReceiptLong : DirectionsCar}
          minWidth={900}
        />
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        title="جزئیات تعمیرگاه بیرونی"
        onClose={() => setSelected(null)}
        maxWidth="lg"
        tabs={selected ? [
          {
            label: 'اطلاعات',
            content: (
              <Stack spacing={1.75}>
                <SummaryPanel
                  selected={selected}
                  vehicle={selectedVehicle}
                  order={selectedOrder}
                />
                <Workflow item={selected} />
              </Stack>
            ),
          },
          ...(canEdit && activeTab === 'driver' ? [{
            label: 'اقدام راننده',
            content: (
              <Stack spacing={1.75}>
                {selected.delivery && <Alert severity="info">تحویل خودرو قبلا ثبت شده و قابل ویرایش نیست.</Alert>}
                {!selected.delivery && (
                  <FormPanel title="ثبت تحویل خودرو به تعمیرگاه">
                    <ResponsiveFields>
                      <RtlTextField label="نام تعمیرگاه" value={delivery.workshop_name} onChange={(e) => setDelivery({ ...delivery, workshop_name: e.target.value })} fullWidth />
                      <RtlTextField label="تلفن تعمیرگاه" value={delivery.workshop_phone} onChange={(e) => setDelivery({ ...delivery, workshop_phone: e.target.value })} fullWidth />
                      <RtlTextField label="آدرس تعمیرگاه" value={delivery.workshop_address} onChange={(e) => setDelivery({ ...delivery, workshop_address: e.target.value })} fullWidth />
                      <RtlTextField label="کیلومتر خودرو" value={delivery.vehicle_odometer} onChange={(e) => setDelivery({ ...delivery, vehicle_odometer: e.target.value })} fullWidth />
                    </ResponsiveFields>
                    <RtlTextField label="یادداشت" value={delivery.notes} onChange={(e) => setDelivery({ ...delivery, notes: e.target.value })} fullWidth multiline minRows={2} />
                    <Button variant="contained" startIcon={<AssignmentTurnedIn />} loading={actionLoading === 'delivery'} disabled={!delivery.workshop_name.trim() || !delivery.workshop_address.trim() || !delivery.workshop_phone.trim() || !delivery.vehicle_odometer} onClick={() => void submitDelivery()} sx={{ alignSelf: 'stretch', minHeight: 44 }}>
                      ثبت تحویل به تعمیرگاه
                    </Button>
                  </FormPanel>
                )}
                {selected.delivery && !selected.pickup && (
                  <FormPanel title="ثبت دریافت خودرو از تعمیرگاه">
                    <ResponsiveFields>
                      <RtlTextField label="کیلومتر خودرو هنگام دریافت" value={pickup.vehicle_odometer} onChange={(e) => setPickup({ ...pickup, vehicle_odometer: e.target.value })} fullWidth />
                    </ResponsiveFields>
                    <RtlTextField label="یادداشت دریافت" value={pickup.notes} onChange={(e) => setPickup({ ...pickup, notes: e.target.value })} fullWidth multiline minRows={2} />
                    <Button variant="contained" color="success" startIcon={<CheckCircleOutline />} loading={actionLoading === 'pickup'} disabled={!pickup.vehicle_odometer} onClick={() => void submitPickup()} sx={{ alignSelf: 'stretch', minHeight: 44 }}>
                      ثبت دریافت خودرو
                    </Button>
                  </FormPanel>
                )}
                {selected.pickup && <Alert severity="success">دریافت خودرو ثبت شده و خودرو فعال است. این اطلاعات قابل ویرایش نیست.</Alert>}
                {actionError && <Alert severity="error">{actionError}</Alert>}
              </Stack>
            ),
          }] : []),
          ...(activeTab === 'transport' ? [{
            label: 'ثبت فاکتور',
            content: (
              <Stack spacing={1.75}>
                {!selected.pickup && <Alert severity="info">ثبت فاکتور بعد از دریافت خودرو توسط راننده فعال می‌شود.</Alert>}
                {selectedReviewCompleted && <Alert severity="success">این فاکتور قبلا تکمیل شده و فقط به صورت گزارش نمایش داده می‌شود.</Alert>}
                <FormPanel title="اطلاعات فاکتور" icon={<ReceiptLong fontSize="small" />}>
                  {selectedReviewCompleted ? (
                    <ResponsiveFields>
                      <AttachmentTile value={review.invoice_attachment} />
                      <InfoTile label="هزینه تعمیر" value={review.repair_cost || '—'} />
                      <InfoTile label="یادداشت تکمیلی" value={review.additional_notes || '—'} />
                    </ResponsiveFields>
                  ) : (
                    <>
                      <ResponsiveFields>
                        <RtlTextField label="هزینه تعمیر" value={review.repair_cost} disabled={!canEditSelectedReview} onChange={(e) => setReview({ ...review, repair_cost: e.target.value })} fullWidth />
                        <InvoiceFilePicker
                          disabled={!canEditSelectedReview}
                          fileName={invoiceFile?.name ?? ''}
                          savedPath={review.invoice_attachment}
                          onChange={setInvoiceFile}
                        />
                      </ResponsiveFields>
                      <RtlTextField label="یادداشت تکمیلی" value={review.additional_notes} disabled={!canEditSelectedReview} onChange={(e) => setReview({ ...review, additional_notes: e.target.value })} fullWidth multiline minRows={2} />
                    </>
                  )}
                </FormPanel>
                <RecordSection title="خدمات انجام‌شده">
                  {!selectedReviewCompleted && (
                    <RecordRow>
                      <RtlTextField label="شرح خدمت" value={draftService.description} disabled={!canEditSelectedReview} onChange={(e) => setDraftService({ ...draftService, description: e.target.value })} fullWidth />
                      <RtlTextField label="ساعت کار" value={draftService.labor_hours} disabled={!canEditSelectedReview} onChange={(e) => setDraftService({ ...draftService, labor_hours: e.target.value })} sx={{ minWidth: 110 }} />
                      <RtlTextField label="هزینه خدمت" value={draftService.cost} disabled={!canEditSelectedReview} onChange={(e) => setDraftService({ ...draftService, cost: e.target.value })} sx={{ minWidth: 130 }} />
                      <RtlTextField label="یادداشت" value={draftService.notes} disabled={!canEditSelectedReview} onChange={(e) => setDraftService({ ...draftService, notes: e.target.value })} fullWidth />
                      <Button variant="contained" startIcon={<Add />} disabled={!canEditSelectedReview || !draftService.description.trim()} onClick={() => {
                        setServiceLines([{
                          description: draftService.description.trim(),
                          labor_hours: draftService.labor_hours.trim(),
                          cost: draftService.cost.trim(),
                          notes: draftService.notes.trim(),
                        }, ...serviceLines]);
                        setDraftService(blankService());
                      }} sx={{ minHeight: 40 }}>
                        افزودن
                      </Button>
                    </RecordRow>
                  )}
                  {serviceLines.map((line, index) => (
                    <RecordRow key={index}>
                      <ReadonlyValue label="شرح خدمت" value={line.description} />
                      <ReadonlyValue label="ساعت کار" value={line.labor_hours || '—'} />
                      <ReadonlyValue label="هزینه خدمت" value={line.cost || '—'} />
                      <ReadonlyValue label="یادداشت" value={line.notes || '—'} />
                      {!selectedReviewCompleted && (
                        <Button variant="outlined" color="error" startIcon={<DeleteOutline />} disabled={!canEditSelectedReview} onClick={() => setServiceLines(serviceLines.filter((_, i) => i !== index))} sx={{ minHeight: 40 }}>
                          حذف
                        </Button>
                      )}
                    </RecordRow>
                  ))}
                </RecordSection>
                <RecordSection title="قطعات تعویضی">
                  {!selectedReviewCompleted && (
                    <RecordRow variant="part">
                      <RtlTextField label="نام یا کد قطعه" value={draftPart.name} disabled={!canEditSelectedReview} onChange={(e) => setDraftPart({ ...draftPart, name: e.target.value })} fullWidth />
                      <RtlTextField label="تعداد" value={draftPart.quantity} disabled={!canEditSelectedReview} onChange={(e) => setDraftPart({ ...draftPart, quantity: e.target.value })} sx={{ minWidth: 100 }} />
                      <RtlTextField label="هزینه قطعه" value={draftPart.cost} disabled={!canEditSelectedReview} onChange={(e) => setDraftPart({ ...draftPart, cost: e.target.value })} sx={{ minWidth: 130 }} />
                      <Button variant="contained" startIcon={<Add />} disabled={!canEditSelectedReview || !draftPart.name.trim()} onClick={() => {
                        setPartLines([{
                          name: draftPart.name.trim(),
                          quantity: draftPart.quantity.trim() || '1',
                          cost: draftPart.cost.trim(),
                        }, ...partLines]);
                        setDraftPart(blankPart());
                      }} sx={{ minHeight: 40 }}>
                        افزودن
                      </Button>
                    </RecordRow>
                  )}
                  {partLines.map((line, index) => (
                    <RecordRow key={index} variant="part">
                      <ReadonlyValue label="نام یا کد قطعه" value={line.name} />
                      <ReadonlyValue label="تعداد" value={line.quantity || '1'} />
                      <ReadonlyValue label="هزینه قطعه" value={line.cost || '—'} />
                      {!selectedReviewCompleted && (
                        <Button variant="outlined" color="error" startIcon={<DeleteOutline />} disabled={!canEditSelectedReview} onClick={() => setPartLines(partLines.filter((_, i) => i !== index))} sx={{ minHeight: 40 }}>
                          حذف
                        </Button>
                      )}
                    </RecordRow>
                  ))}
                  {selectedReviewCompleted && partLines.length === 0 && (
                    <EmptyRecordMessage text="هیچ قطعه‌ای ثبت نشده" />
                  )}
                </RecordSection>
                {!selectedReviewCompleted && (
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))' },
                      gap: 1.5,
                      pt: 0.5,
                    }}
                  >
                    <Button variant="outlined" startIcon={<Save />} disabled={!canEditSelectedReview} loading={actionLoading === 'review'} onClick={() => void saveReview()} sx={{ flex: 1, minHeight: 44 }}>
                      ذخیره پیش‌نویس
                    </Button>
                    <Button variant="contained" color="success" startIcon={<CheckCircleOutline />} disabled={!canEditSelectedReview} loading={actionLoading === 'close'} onClick={() => void closeWorkflow()} sx={{ flex: 1, minHeight: 44 }}>
                      بستن درخواست تعمیر
                    </Button>
                  </Box>
                )}
                {actionError && <Alert severity="error">{actionError}</Alert>}
              </Stack>
            ),
          }] : []),
        ] : []}
      />
    </FeaturePage>
  );
}

function Workflow({ item }: { item: ExternalWorkshopAssignment }) {
  const steps = [
    ['ارجاع به تعمیرگاه بیرونی', true],
    ['تحویل خودرو به تعمیرگاه', Boolean(item.delivery)],
    ['تعمیر بیرونی در حال انجام', Boolean(item.delivery)],
    ['دریافت خودرو از تعمیرگاه', Boolean(item.pickup)],
    ['ثبت فاکتور و اطلاعات تعمیر', Boolean(item.review)],
    ['تکمیل فرایند تعمیر بیرونی', item.status === 'COMPLETED'],
  ] as const;
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography fontWeight={800} mb={1.5}>خط زمانی فرایند</Typography>
        <Stack spacing={1}>
          {steps.map(([label, done], index) => (
            <Stack
              key={label}
              direction="row"
              alignItems="center"
              sx={{
                p: 1,
                borderRadius: 1,
                gap: 2,
                bgcolor: done ? 'rgba(21, 95, 61, 0.06)' : 'rgba(100, 112, 103, 0.06)',
                border: '1px solid',
                borderColor: done ? 'rgba(21, 95, 61, 0.18)' : 'rgba(100, 112, 103, 0.16)',
              }}
            >
              <Box
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  display: 'grid',
                  placeItems: 'center',
                  bgcolor: done ? 'success.main' : 'grey.300',
                  color: done ? 'common.white' : 'text.secondary',
                  fontWeight: 900,
                  flexShrink: 0,
                }}
              >
                {done ? '✓' : index + 1}
              </Box>
              <Typography fontWeight={done ? 800 : 600}>{label}</Typography>
              <Box sx={{ flex: 1 }} />
              <PlainStatusBadge label={done ? 'ثبت شده' : 'در انتظار'} tone={done ? 'success' : 'neutral'} />
            </Stack>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}

function SummaryPanel({
  selected,
  vehicle,
  order,
}: {
  selected: ExternalWorkshopAssignment;
  vehicle: Vehicle | null | undefined;
  order: RepairOrder | null | undefined;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.75}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            justifyContent="space-between"
            alignItems={{ md: 'center' }}
            gap={1.5}
          >
            <Box>
              <Typography fontWeight={900} fontSize="1.1rem">
                {vehicle?.license_plate || 'پلاک نامشخص'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                شماره خودرو: {vehicle?.vehicle_number || '—'}
              </Typography>
            </Box>
            <PlainStatusBadge label={statusLabel(selected)} tone="warning" />
          </Stack>
          <Divider />
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
              gap: 1.25,
            }}
          >
            <InfoTile label="وضعیت سفارش" value={order?.status || '—'} />
            <InfoTile
              label="تعمیرگاه"
              value={
                selected.delivery?.workshop_name ||
                selected.workshop_name ||
                'ثبت توسط راننده'
              }
            />
            <InfoTile
              label="آدرس"
              value={
                selected.delivery?.workshop_address ||
                selected.workshop_address ||
                'ثبت توسط راننده'
              }
            />
            <InfoTile label="علت ارجاع" value={selected.repair_reason || '—'} />
          </Box>
          {selected.description && (
            <>
              <Divider />
              <InfoTile label="توضیحات" value={selected.description} />
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function InvoiceFilePicker({
  disabled,
  fileName,
  savedPath,
  onChange,
}: {
  disabled: boolean;
  fileName: string;
  savedPath: string;
  onChange: (file: File | null) => void;
}) {
  const displayValue = fileName || attachmentFileName(savedPath) || 'فایلی انتخاب نشده';
  const href = attachmentHref(savedPath);
  return (
    <Box
      sx={{
        minHeight: 64,
        p: 1.25,
        borderRadius: 1,
        bgcolor: 'rgba(15, 23, 42, 0.035)',
        border: '1px solid',
        borderColor: 'rgba(15, 23, 42, 0.08)',
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: 'auto minmax(0, 1fr)' },
        gap: 1,
        alignItems: 'center',
      }}
    >
      <Button
        variant="outlined"
        component="label"
        startIcon={<AttachFile />}
        disabled={disabled}
        sx={{ minHeight: 40 }}
      >
        انتخاب فایل
        <input
          hidden
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx"
          onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        />
      </Button>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="caption" color="text.secondary" display="block" mb={0.2}>
          پیوست فاکتور
        </Typography>
        <Typography fontWeight={800} sx={{ overflowWrap: 'anywhere', lineHeight: 1.7 }}>
          {href && !fileName ? (
            <Link href={href} target="_blank" rel="noreferrer" underline="hover">
              {displayValue}
            </Link>
          ) : displayValue}
        </Typography>
      </Box>
    </Box>
  );
}

function AttachmentTile({ value }: { value: string }) {
  const fileName = attachmentFileName(value);
  const href = attachmentHref(value);
  return (
    <Box
      sx={{
        minHeight: 64,
        p: 1.25,
        borderRadius: 1,
        bgcolor: 'rgba(15, 23, 42, 0.035)',
        border: '1px solid',
        borderColor: 'rgba(15, 23, 42, 0.08)',
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block" mb={0.4}>
        پیوست فاکتور
      </Typography>
      <Typography fontWeight={800} sx={{ overflowWrap: 'anywhere', lineHeight: 1.8 }}>
        {href && fileName ? (
          <Link href={href} target="_blank" rel="noreferrer" underline="hover">
            {fileName}
          </Link>
        ) : fileName || '—'}
      </Typography>
    </Box>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <Box
      sx={{
        minHeight: 64,
        p: 1.25,
        borderRadius: 1,
        bgcolor: 'rgba(15, 23, 42, 0.035)',
        border: '1px solid',
        borderColor: 'rgba(15, 23, 42, 0.08)',
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block" mb={0.4}>
        {label}
      </Typography>
      <Typography fontWeight={800} sx={{ overflowWrap: 'anywhere', lineHeight: 1.8 }}>
        {value}
      </Typography>
    </Box>
  );
}

function FormPanel({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" alignItems="center" spacing={1}>
            {icon}
            <Typography fontWeight={900}>{title}</Typography>
          </Stack>
          {children}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ResponsiveFields({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
        gap: 1.25,
      }}
    >
      {children}
    </Box>
  );
}

function RecordRow({
  children,
  variant = 'service',
}: {
  children: ReactNode;
  variant?: 'service' | 'part';
}) {
  const columns =
    variant === 'part'
      ? 'minmax(200px, 1fr) minmax(88px, 110px) minmax(120px, 150px) auto'
      : 'minmax(200px, 1fr) minmax(88px, 120px) minmax(120px, 150px) minmax(150px, 1fr) auto';
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          md: columns,
        },
        gap: 1,
        p: 1,
        borderRadius: 1,
        bgcolor: 'rgba(20, 26, 33, 0.025)',
        border: '1px solid',
        borderColor: 'divider',
        alignItems: 'center',
      }}
    >
      {children}
    </Box>
  );
}

function RecordSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Typography fontWeight={800}>{title}</Typography>
          {children}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ReadonlyValue({ label, value }: { label: string; value: string }) {
  return (
    <Box
      sx={{
        minHeight: 44,
        px: 1.25,
        py: 0.8,
        borderRadius: 1,
        bgcolor: 'rgba(15, 23, 42, 0.04)',
        border: '1px solid',
        borderColor: 'rgba(15, 23, 42, 0.08)',
      }}
    >
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography fontWeight={800} sx={{ overflowWrap: 'anywhere' }}>
        {value}
      </Typography>
    </Box>
  );
}

function EmptyRecordMessage({ text }: { text: string }) {
  return (
    <Box
      sx={{
        p: 1.5,
        borderRadius: 1,
        bgcolor: 'rgba(15, 23, 42, 0.035)',
        border: '1px dashed',
        borderColor: 'rgba(15, 23, 42, 0.16)',
      }}
    >
      <Typography variant="body2" color="text.secondary" fontWeight={700}>
        {text}
      </Typography>
    </Box>
  );
}
