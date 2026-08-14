import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  MenuItem,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { CheckCircleOutline, ShoppingCart } from '@mui/icons-material';
import { Inventory2, LocalShipping } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import { formatDateTime, toFaNumber } from '../../utils/format';

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: 'در انتظار بررسی ترابری',
  APPROVED: 'تایید اولیه',
  WAITING_STOCK: 'منتظر موجودی/خرید',
  STOCK_ISSUED: 'ارسال‌شده به تعمیرگاه',
  PURCHASE_REQUIRED: 'نیاز به خرید',
  PARTIALLY_ISSUED: 'تخصیص جزئی — منتظر خرید',
  RECEIVED: 'دریافت‌شده در تعمیرگاه',
};

const DECISION_LABELS: Record<string, string> = {
  FROM_STOCK: 'تخصیص از انبار',
  PURCHASE: 'خرید از بیرون',
  PENDING: 'ثبت‌نشده',
};

type ItemDecision = 'FROM_STOCK' | 'PURCHASE';

type StatusFilter =
  | ''
  | 'REQUESTED'
  | 'PURCHASE_REQUIRED'
  | 'PARTIALLY_ISSUED'
  | 'STOCK_ISSUED'
  | 'RECEIVED';

const STATUS_TAB_OPTIONS: ReadonlyArray<StatusTabOption<Exclude<StatusFilter, ''>>> = [
  { value: '', label: 'همه' },
  { value: 'REQUESTED', label: 'در انتظار بررسی' },
  { value: 'PURCHASE_REQUIRED', label: 'نیاز به خرید' },
  { value: 'PARTIALLY_ISSUED', label: 'تخصیص جزئی' },
  { value: 'STOCK_ISSUED', label: 'ارسال‌شده' },
  { value: 'RECEIVED', label: 'دریافت‌شده' },
];

type MaterialRequestItem = {
  id: string;
  material_number: string;
  quantity: string | number;
  material_name?: string;
  available_quantity?: string | number;
  in_catalog?: boolean;
  from_catalog?: boolean;
  decision?: string;
  item_status?: string;
};

type MaterialRequestRow = {
  id: string;
  repair_order_id: string;
  status: string;
  created_at: string;
  items: MaterialRequestItem[];
};

type PurchaseFlowStep = {
  key: string;
  label: string;
  done: boolean;
  active: boolean;
};

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'STOCK_ISSUED' || status === 'RECEIVED') return 'success';
  if (
    status === 'REQUESTED' ||
    status === 'PURCHASE_REQUIRED' ||
    status === 'PARTIALLY_ISSUED'
  ) {
    return 'warning';
  }
  return 'neutral';
}

function canAllocateFromStock(item: MaterialRequestItem): boolean {
  if (item.in_catalog === false || item.from_catalog === false) return false;
  const available = Number(item.available_quantity ?? 0);
  const requested = Number(item.quantity ?? 0);
  return available >= requested && available > 0;
}

function needsPurchaseFollowUp(status: string): boolean {
  return status === 'PURCHASE_REQUIRED' || status === 'PARTIALLY_ISSUED';
}

function filterForStatus(nextStatus: string): StatusFilter {
  if (
    nextStatus === 'PURCHASE_REQUIRED' ||
    nextStatus === 'PARTIALLY_ISSUED' ||
    nextStatus === 'STOCK_ISSUED' ||
    nextStatus === 'RECEIVED' ||
    nextStatus === 'REQUESTED'
  ) {
    return nextStatus;
  }
  return '';
}

/** Purchase-path steps aligned with transport → warehouse → workshop flowchart. */
function buildPurchaseFlowSteps(status: string): PurchaseFlowStep[] {
  const purchaseRegistered = [
    'PURCHASE_REQUIRED',
    'PARTIALLY_ISSUED',
    'WAITING_STOCK',
    'STOCK_ISSUED',
    'RECEIVED',
  ].includes(status);
  const issued = status === 'STOCK_ISSUED' || status === 'RECEIVED';
  const received = status === 'RECEIVED';
  return [
    {
      key: 'po',
      label: 'ثبت سفارش خرید',
      done: purchaseRegistered,
      active: status === 'REQUESTED',
    },
    {
      key: 'gr_issue',
      label: 'رسید قطعه به انبار و تخصیص / ارسال به تعمیرگاه',
      done: issued,
      active: needsPurchaseFollowUp(status),
    },
    {
      key: 'recv',
      label: 'ثبت رسید دریافت فیزیکی در تعمیرگاه',
      done: received,
      active: status === 'STOCK_ISSUED',
    },
  ];
}

function PurchaseFlowStepper({ status }: { status: string }) {
  const steps = buildPurchaseFlowSteps(status);
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1 }}>
          مراحل خرید از بیرون
        </Typography>
        <Stack spacing={1}>
          {steps.map((step, index) => (
            <Box
              key={step.key}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                opacity: step.done || step.active ? 1 : 0.55,
              }}
            >
              <Box
                sx={{
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  flexShrink: 0,
                  display: 'grid',
                  placeItems: 'center',
                  fontSize: 12,
                  fontWeight: 800,
                  bgcolor: step.done
                    ? 'success.main'
                    : step.active
                      ? 'warning.main'
                      : 'action.disabledBackground',
                  color: step.done || step.active ? 'common.white' : 'text.secondary',
                }}
              >
                {step.done ? '✓' : toFaNumber(String(index + 1))}
              </Box>
              <Typography
                variant="body2"
                fontWeight={step.active ? 800 : 500}
                color={step.active ? 'warning.dark' : 'text.primary'}
              >
                {step.label}
              </Typography>
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}

/**
 * Transportation inbox for reviewing workshop parts requests.
 */
export function TransportPartsPage() {
  const canEdit = useCanEdit();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [items, setItems] = useState<MaterialRequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusTab, setStatusTab] = useState<StatusFilter>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const status = statusTab || statusFilter;
  const [selected, setSelected] = useState<MaterialRequestRow | null>(null);
  const [note, setNote] = useState('');
  const [itemDecisions, setItemDecisions] = useState<Record<string, ItemDecision>>({});
  const [actionLoading, setActionLoading] = useState('');
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');
  const [kpis, setKpis] = useState({ requested: 0, purchase: 0, issued: 0 });

  const computeKpis = (rows: MaterialRequestRow[]) => ({
    requested: rows.filter((item) => item.status === 'REQUESTED').length,
    purchase: rows.filter(
      (item) =>
        item.status === 'PURCHASE_REQUIRED' || item.status === 'PARTIALLY_ISSUED',
    ).length,
    issued: rows.filter((item) => item.status === 'STOCK_ISSUED').length,
  });

  const refreshKpis = useCallback(async () => {
    try {
      const rows = (await api.listMaterialRequests(undefined)) as MaterialRequestRow[];
      setKpis(computeKpis(Array.isArray(rows) ? rows : []));
    } catch {
      // Keep last KPI snapshot; list error is handled separately.
    }
  }, []);

  const load = useCallback(async (statusOverride?: StatusFilter) => {
    const filter = statusOverride ?? status;
    setLoading(true);
    setError('');
    try {
      const rows = (await api.listMaterialRequests(
        filter ? { status: filter } : undefined,
      )) as MaterialRequestRow[];
      setItems(Array.isArray(rows) ? rows : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در بارگذاری درخواست قطعات');
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void refreshKpis();
  }, [refreshKpis]);

  const itemKey = (item: MaterialRequestItem) => String(item.id);

  const openSelected = useCallback((row: MaterialRequestRow) => {
    setItemDecisions({});
    setNote('');
    setActionError('');
    setSuccess('');
    setSelected(row);
  }, []);

  const columns = useMemo<Array<RtlDataTableColumn<MaterialRequestRow, string>>>(
    () => [
      {
        key: 'status',
        label: 'وضعیت',
        minWidth: 160,
        render: (row) => (
          <PlainStatusBadge
            label={STATUS_LABELS[row.status] ?? row.status}
            tone={statusTone(row.status)}
          />
        ),
      },
      {
        key: 'items',
        label: 'اقلام',
        minWidth: 80,
        render: (row) => toFaNumber(String(row.items?.length ?? 0)),
      },
      {
        key: 'created_at',
        label: 'تاریخ',
        minWidth: 140,
        render: (row) => formatDateTime(row.created_at),
      },
      {
        key: 'repair_order_id',
        label: 'سفارش تعمیر',
        minWidth: 120,
        render: (row) => row.repair_order_id.slice(0, 8),
      },
      {
        key: 'actions',
        label: 'عملیات',
        align: 'center',
        minWidth: 120,
        render: (row) => (
          <Button
            size="small"
            variant="outlined"
            onClick={() => openSelected(row)}
            sx={{ height: 36, minHeight: 36, px: 1.5 }}
          >
            بررسی
          </Button>
        ),
      },
    ],
    [openSelected],
  );

  const allItemsDecided = useMemo(() => {
    if (!selected?.items?.length) return false;
    return selected.items.every((item) => Boolean(itemDecisions[itemKey(item)]));
  }, [selected, itemDecisions]);

  const applyDecisionResult = async (result: MaterialRequestRow) => {
    const nextFilter = filterForStatus(result.status);
    if (nextFilter !== status) {
      setStatusTab(nextFilter);
      setStatusFilter('');
    }
    setSelected(result);
    setItemDecisions({});
    setNote('');
    await Promise.all([load(nextFilter), refreshKpis()]);

    if (needsPurchaseFollowUp(result.status)) {
      setSuccess(
        'سفارش خرید ثبت شد. مرحله بعد: پس از رسید کالا به انبار، ارسال به تعمیرگاه را تایید کنید.',
      );
      return;
    }
    if (result.status === 'STOCK_ISSUED') {
      setSuccess(
        'قطعات تخصیص و به تعمیرگاه ارسال شد. مرحله بعد: دریافت فیزیکی در تعمیرگاه.',
      );
      return;
    }
    setSuccess('تصمیم اقلام ثبت شد.');
  };

  async function runDecide(decisions: Record<string, ItemDecision>) {
    if (!selected?.items?.length) return;
    const payload = selected.items.map((item) => ({
      item_id: itemKey(item),
      decision: decisions[itemKey(item)],
    }));
    if (payload.some((row) => !row.decision)) return;

    setActionLoading('decide');
    setActionError('');
    setSuccess('');
    try {
      const result = (await api.decideMaterialAvailability(selected.id, {
        note,
        items: payload,
      })) as MaterialRequestRow;
      await applyDecisionResult(result);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'عملیات ناموفق بود');
    } finally {
      setActionLoading('');
    }
  }

  async function runIssuePurchased() {
    if (!selected) return;
    setActionLoading('issue');
    setActionError('');
    setSuccess('');
    try {
      const result = (await api.issuePurchasedMaterialRequest(
        selected.id,
      )) as MaterialRequestRow;
      const nextFilter = filterForStatus(result.status);
      if (nextFilter !== status) {
        setStatusTab(nextFilter);
        setStatusFilter('');
      }
      setSelected(result);
      await Promise.all([load(nextFilter), refreshKpis()]);
      setSuccess(
        'رسید خرید ثبت و قطعات به تعمیرگاه ارسال شد. منتظر دریافت فیزیکی در تعمیرگاه باشید.',
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'عملیات ناموفق بود');
    } finally {
      setActionLoading('');
    }
  }

  const submitDecisions = (decisions: Record<string, ItemDecision> = itemDecisions) => {
    void runDecide(decisions);
  };

  const chooseDecision = (itemId: string, decision: ItemDecision) => {
    if (!selected) return;
    const next: Record<string, ItemDecision> = {
      ...itemDecisions,
      [String(itemId)]: decision,
    };
    setItemDecisions(next);
  };

  return (
    <FeaturePage>
      <PageHeader
        title="بررسی درخواست قطعات"
        description="تصمیم موجودی انبار مرکزی یا خرید از بیرون برای هر قلم قطعه"
        breadcrumbs={[{ label: 'ترابری' }, { label: 'درخواست قطعات' }]}
      />

      <KpiGrid>
        <KpiCard
          label="در انتظار تصمیم"
          value={toFaNumber(kpis.requested)}
          icon={Inventory2}
          tone="warning"
        />
        <KpiCard
          label="نیاز به خرید / جزئی"
          value={toFaNumber(kpis.purchase)}
          icon={ShoppingCart}
          tone="error"
        />
        <KpiCard
          label="ارسال‌شده"
          value={toFaNumber(kpis.issued)}
          icon={CheckCircleOutline}
          tone="success"
        />
      </KpiGrid>

      <StatusFilterTabs
        value={statusTab}
        options={STATUS_TAB_OPTIONS}
        onChange={(next) => {
          setStatusTab(next);
          if (next) setStatusFilter('');
        }}
        ariaLabel="وضعیت درخواست قطعات"
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
            <MenuItem value="REQUESTED">در انتظار بررسی</MenuItem>
            <MenuItem value="PURCHASE_REQUIRED">نیاز به خرید</MenuItem>
            <MenuItem value="PARTIALLY_ISSUED">تخصیص جزئی</MenuItem>
            <MenuItem value="STOCK_ISSUED">ارسال‌شده</MenuItem>
            <MenuItem value="RECEIVED">دریافت‌شده</MenuItem>
          </RtlSelectField>
          <ClearFiltersButton
            onClick={() => setStatusFilter('')}
            disabled={statusFilter === ''}
          />
        </FilterPanel>
      )}

      {success ? <Alert severity="success">{success}</Alert> : null}
      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!error ? (
        <RtlDataTable
          columns={columns}
          rows={items}
          getRowKey={(row) => row.id}
          loading={loading}
          emptyMessage="درخواست قطعه‌ای یافت نشد"
          emptySubtitle="فعلاً درخواست قطعه‌ای در این وضعیت وجود ندارد."
          emptyIcon={LocalShipping}
          minWidth={isMobile ? 640 : 900}
        />
      ) : null}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="جزئیات درخواست قطعه"
        icon={Inventory2}
        tabs={[
          {
            label: 'اقلام و تصمیم',
            content: selected ? (
              <Stack spacing={2}>
                <Card variant="outlined">
                  <CardContent>
                    <DetailLine
                      label="وضعیت"
                      value={STATUS_LABELS[selected.status] ?? selected.status}
                    />
                    <DetailLine label="سفارش تعمیر" value={selected.repair_order_id} />
                    <DetailLine label="تاریخ" value={formatDateTime(selected.created_at)} />
                  </CardContent>
                </Card>

                {selected.status !== 'REQUESTED' ||
                selected.items.some(
                  (item) =>
                    item.decision === 'PURCHASE' ||
                    itemDecisions[itemKey(item)] === 'PURCHASE' ||
                    !canAllocateFromStock(item),
                ) ? (
                  <PurchaseFlowStepper status={selected.status} />
                ) : null}

                <Typography variant="subtitle2" fontWeight={800}>
                  اقلام درخواستی
                </Typography>

                {(selected.items ?? []).map((item) => {
                  const stockOk = canAllocateFromStock(item);
                  const key = itemKey(item);
                  const decision = itemDecisions[key];
                  return (
                    <Card key={key} variant="outlined">
                      <CardContent>
                        <Stack spacing={1.25}>
                          <Typography fontWeight={800}>
                            {item.material_number}
                            {item.material_name ? ` · ${item.material_name}` : ''}
                          </Typography>
                          <DetailLine
                            label="تعداد درخواستی"
                            value={toFaNumber(String(item.quantity))}
                          />
                          <DetailLine
                            label="موجودی انبار"
                            value={
                              item.in_catalog === false || item.from_catalog === false
                                ? 'در لیست انبار نیست'
                                : toFaNumber(String(item.available_quantity ?? 0))
                            }
                          />
                          {canEdit && selected.status === 'REQUESTED' ? (
                            <Stack spacing={1.25}>
                              <Typography variant="caption" fontWeight={800}>
                                روش تامین این قلم
                              </Typography>
                              <ToggleButtonGroup
                                exclusive
                                fullWidth
                                value={decision || null}
                                onChange={(_event, next: ItemDecision | null) => {
                                  if (next) chooseDecision(key, next);
                                }}
                                sx={{
                                  gap: 1,
                                  '& .MuiToggleButtonGroup-grouped': {
                                    border: '1px solid',
                                    borderColor: 'divider',
                                    borderRadius: (t) => `${t.radius('sm')} !important`,
                                    minHeight: 44,
                                    px: 1.5,
                                    py: 0.75,
                                    flex: 1,
                                    fontWeight: 800,
                                    textTransform: 'none',
                                    justifyContent: 'center',
                                    gap: 0.75,
                                    '&:not(:first-of-type)': {
                                      ml: 0,
                                      borderRadius: (t) => `${t.radius('sm')} !important`,
                                    },
                                    '&:first-of-type': {
                                      borderRadius: (t) => `${t.radius('sm')} !important`,
                                    },
                                  },
                                }}
                              >
                                <ToggleButton
                                  value="FROM_STOCK"
                                  disabled={!stockOk || actionLoading === 'decide'}
                                  sx={{
                                    color: 'text.secondary',
                                    bgcolor: 'background.paper',
                                    '&.Mui-selected, &.Mui-selected:hover': {
                                      bgcolor: 'success.main',
                                      borderColor: 'success.main',
                                      color: 'success.contrastText',
                                    },
                                  }}
                                >
                                  <Inventory2 fontSize="small" />
                                  از انبار مرکزی
                                </ToggleButton>
                                <ToggleButton
                                  value="PURCHASE"
                                  disabled={actionLoading === 'decide'}
                                  sx={{
                                    color: 'text.secondary',
                                    bgcolor: 'background.paper',
                                    '&.Mui-selected, &.Mui-selected:hover': {
                                      bgcolor: 'warning.main',
                                      borderColor: 'warning.main',
                                      color: 'warning.contrastText',
                                    },
                                  }}
                                >
                                  <ShoppingCart fontSize="small" />
                                  خرید از بیرون
                                </ToggleButton>
                              </ToggleButtonGroup>
                              {!stockOk ? (
                                <Typography variant="caption" color="text.secondary">
                                  موجودی کافی برای تامین از انبار مرکزی وجود ندارد.
                                </Typography>
                              ) : null}
                              {decision ? (
                                <Typography variant="caption" color="text.secondary">
                                  روش انتخاب‌شده: {DECISION_LABELS[decision]}
                                </Typography>
                              ) : null}
                            </Stack>
                          ) : (
                            <DetailLine
                              label="تصمیم"
                              value={
                                DECISION_LABELS[item.decision ?? ''] ||
                                item.decision ||
                                '—'
                              }
                            />
                          )}
                        </Stack>
                      </CardContent>
                    </Card>
                  );
                })}

                {actionError ? <Alert severity="error">{actionError}</Alert> : null}
                {success && selected ? <Alert severity="success">{success}</Alert> : null}

                {canEdit && selected.status === 'REQUESTED' ? (
                  <Stack spacing={1.5}>
                    <RtlTextField
                      label="یادداشت تصمیم"
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      multiline
                      minRows={2}
                      fullWidth
                    />
                    <Button
                      type="button"
                      color="success"
                      variant="contained"
                      startIcon={<CheckCircleOutline />}
                      loading={actionLoading === 'decide'}
                      disabled={!allItemsDecided || actionLoading === 'decide'}
                      onClick={() => submitDecisions()}
                    >
                      ثبت روش تامین قطعات
                    </Button>
                  </Stack>
                ) : null}

                {canEdit && needsPurchaseFollowUp(selected.status) ? (
                  <Stack spacing={1}>
                    <Alert severity="warning">
                      سفارش خرید ثبت شده است. پس از رسید قطعه به انبار، مرحله بعد را
                      تایید کنید تا قطعه به تعمیرگاه ارسال شود.
                    </Alert>
                    <Button
                      type="button"
                      color="warning"
                      variant="contained"
                      startIcon={<LocalShipping />}
                      loading={actionLoading === 'issue'}
                      disabled={actionLoading === 'issue'}
                      onClick={() => void runIssuePurchased()}
                    >
                      تایید رسید خرید و ارسال به تعمیرگاه
                    </Button>
                  </Stack>
                ) : null}

                {selected.status === 'STOCK_ISSUED' ? (
                  <Alert severity="info">
                    قطعات به تعمیرگاه ارسال شده‌اند. مرحله آخر (دریافت فیزیکی) در
                    صفحه تعمیرگاه مرکزی ثبت می‌شود.
                  </Alert>
                ) : null}
              </Stack>
            ) : null,
          },
        ]}
      />
    </FeaturePage>
  );
}
