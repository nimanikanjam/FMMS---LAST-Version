import { useEffect, useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  InputAdornment,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import {
  CheckCircle,
  CheckCircleOutline,
  ExpandMore,
  Search,
} from '@mui/icons-material';
import { DirectionsCar, ReportProblem } from '../../components/icons3d/Icons3D';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../../api/client';
import { useCanEdit, useCurrentUser } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { FailureSeverity, Fault, FaultCatalog, Vehicle } from '../../types/fmms';
import { toFaNumber } from '../../utils/format';
import { severityFromDefectClass } from '../../utils/severity';

const VEHICLE_PAGE_SIZE = 100;
const CATALOG_PAGE_SIZE = 500;

const SEVERITY_LABELS: Record<FailureSeverity, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

const SEVERITY_RANK: Record<FailureSeverity, number> = {
  LOW: 0,
  MEDIUM: 1,
  HIGH: 2,
  CRITICAL: 3,
};

type FlowStep = 'vehicle' | 'fault' | 'details';

type CatalogGroup = {
  category: string;
  items: FaultCatalog[];
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function maxSeverity(values: FailureSeverity[]): FailureSeverity {
  return values.reduce((best, current) =>
    SEVERITY_RANK[current] > SEVERITY_RANK[best] ? current : best,
  );
}

function vehicleAssignedToDriver(vehicle: Vehicle, customerNumber: string): boolean {
  return (
    vehicle.driver1?.customer_number === customerNumber ||
    vehicle.driver2?.customer_number === customerNumber
  );
}

function parentFaultCode(items: FaultCatalog[]): string {
  if (items.length === 1) {
    const cleaned = items[0].code
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9-]/g, '')
      .slice(0, 20);
    return cleaned.length >= 3 ? cleaned : 'MANUAL';
  }
  return 'MULTI';
}

/**
 * Compact manual fault form styled like the daily inspection wizard.
 */
export function ManualFaultPage() {
  const canEdit = useCanEdit();
  const { user, loading: userLoading } = useCurrentUser();
  const isDriver = user?.role === 'DRIVER';
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [catalogs, setCatalogs] = useState<FaultCatalog[]>([]);
  const [vehicleId, setVehicleId] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [expandedCategory, setExpandedCategory] = useState<string | false>(false);
  const [description, setDescription] = useState('');
  const [bootLoading, setBootLoading] = useState(true);
  const [bootError, setBootError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [completedCount, setCompletedCount] = useState(0);
  const [completedFault, setCompletedFault] = useState<Fault | null>(null);

  useEffect(() => {
    if (userLoading) return;
    let cancelled = false;
    const boot = async () => {
      setBootLoading(true);
      setBootError('');
      try {
        const catalogPage = await api.listFaultCatalogs({ page: 1, pageSize: CATALOG_PAGE_SIZE });
        if (cancelled) return;
        setCatalogs(normalizePaginated(catalogPage).filter((item) => item.is_active));

        if (isDriver) {
          if (user?.assigned_vehicle_id) {
            const vehicle = await api.getVehicle(user.assigned_vehicle_id);
            if (cancelled) return;
            setVehicles([vehicle]);
            setVehicleId(vehicle.id);
            return;
          }
          const customerNumber = user?.linked_driver?.customer_number || '';
          if (!customerNumber) {
            setBootError(
              'حساب کاربری شما به کد پرسنلی SAP یا راننده فعال متصل نیست. با مدیر سیستم هماهنگ کنید.',
            );
            return;
          }
          let page = 1;
          let loaded: Vehicle[] = [];
          let total = Infinity;
          while (loaded.length < total) {
            const result = await api.listVehicles('', 'license_plate', {
              page,
              pageSize: VEHICLE_PAGE_SIZE,
            });
            if (cancelled) return;
            loaded = [...loaded, ...result.results];
            total = result.count;
            page += 1;
            if (result.results.length === 0) break;
          }
          const assigned = loaded.filter(
            (item) => item.status === 'ACTIVE' && vehicleAssignedToDriver(item, customerNumber),
          );
          setVehicles(assigned);
          if (assigned.length === 1) {
            setVehicleId(assigned[0].id);
          } else if (assigned.length === 0) {
            setBootError('خودروی عملیاتی اساین‌شده به شما یافت نشد.');
          }
          return;
        }

        const vehiclePage = await api.listVehicles('', 'license_plate', {
          page: 1,
          pageSize: VEHICLE_PAGE_SIZE,
        });
        if (cancelled) return;
        setVehicles(vehiclePage.results);
      } catch (err) {
        if (!cancelled) {
          setBootError(err instanceof Error ? err.message : 'آماده‌سازی فرم ثبت خرابی انجام نشد');
        }
      } finally {
        if (!cancelled) setBootLoading(false);
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, [userLoading, isDriver, user]);

  const selectedVehicle = useMemo(
    () => vehicles.find((item) => item.id === vehicleId) ?? null,
    [vehicleId, vehicles],
  );

  const selectedCatalogs = useMemo(() => {
    const byId = new Map(catalogs.map((item) => [item.id, item]));
    return selectedIds
      .map((id) => byId.get(id))
      .filter((item): item is FaultCatalog => Boolean(item));
  }, [catalogs, selectedIds]);

  const groups = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const map = new Map<string, FaultCatalog[]>();

    catalogs.forEach((item) => {
      if (needle) {
        const haystack = [item.group_text, item.code, item.code_text, item.defect_class_text]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        if (!haystack.includes(needle)) return;
      }
      const category = item.group_text?.trim() || 'سایر';
      const current = map.get(category) ?? [];
      current.push(item);
      map.set(category, current);
    });

    const next: CatalogGroup[] = [...map.entries()]
      .map(([category, items]) => ({
        category,
        items: [...items].sort((a, b) => a.code.localeCompare(b.code, 'fa')),
      }))
      .sort((a, b) => a.category.localeCompare(b.category, 'fa'));

    return next;
  }, [catalogs, search]);

  useEffect(() => {
    if (!search.trim()) return;
    if (groups.length === 1) {
      setExpandedCategory(groups[0].category);
      return;
    }
    if (groups.length > 0 && expandedCategory && !groups.some((g) => g.category === expandedCategory)) {
      setExpandedCategory(groups[0].category);
    }
  }, [expandedCategory, groups, search]);

  const selectedSeverities = selectedCatalogs.map((item) =>
    severityFromDefectClass(item.defect_class),
  );
  const severity = selectedSeverities.length ? maxSeverity(selectedSeverities) : null;
  const flowStep: FlowStep = !vehicleId ? 'vehicle' : selectedCatalogs.length === 0 ? 'fault' : 'details';

  const stepLabels: Array<{ key: FlowStep; label: string }> = [
    { key: 'vehicle', label: 'خودرو' },
    { key: 'fault', label: 'خرابی' },
    { key: 'details', label: 'ثبت' },
  ];

  const toggleCatalog = (item: FaultCatalog) => {
    setSubmitError('');
    setSelectedIds((prev) =>
      prev.includes(item.id) ? prev.filter((id) => id !== item.id) : [...prev, item.id],
    );
  };

  const removeCatalog = (id: string) => {
    setSelectedIds((prev) => prev.filter((itemId) => itemId !== id));
  };

  const submit = async () => {
    if (!vehicleId || selectedCatalogs.length === 0 || !severity) {
      setSubmitError('انتخاب خودرو و حداقل یک خرابی الزامی است.');
      return;
    }
    setSubmitting(true);
    setSubmitError('');
    try {
      const items = selectedCatalogs.map((item) => {
        const itemSeverity = severityFromDefectClass(item.defect_class);
        return {
          code: item.code,
          description: item.code_text || item.code,
          severity: itemSeverity,
          component: (item.code_text || item.code).slice(0, 100),
        };
      });
      const summary =
        description.trim() ||
        (items.length === 1
          ? items[0].description
          : `${toFaNumber(items.length)} خرابی ثبت‌شده`);

      const created = await api.reportFault({
        vehicle_id: vehicleId,
        code: parentFaultCode(selectedCatalogs),
        description: summary,
        severity,
        items,
      });
      setCompletedFault(created);
      setCompletedCount(selectedCatalogs.length);
      setCompleted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'ثبت خرابی انجام نشد');
    } finally {
      setSubmitting(false);
    }
  };

  if (bootLoading) return <LoadingState label="در حال آماده‌سازی فرم ثبت خرابی" />;
  if (bootError) return <ErrorState message={bootError} onRetry={() => window.location.reload()} />;

  if (completed) {
    return (
      <Stack spacing={{ xs: 1.5, md: 2 }} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="ثبت خرابی موردی"
          breadcrumbs={[
            { label: 'راننده' },
            { label: 'ثبت خرابی موردی' },
          ]}
        />

        <Card
          variant="outlined"
          sx={{
            width: '100%',
            borderColor: 'divider',
            borderRadius: (t) => t.radius('md'),
            boxShadow: '0 8px 22px rgba(15, 107, 76, 0.07)',
            bgcolor: 'background.paper',
            overflow: 'hidden',
            position: 'relative',
            '&::before': {
              content: '""',
              position: 'absolute',
              insetInlineStart: 0,
              top: 0,
              bottom: 0,
              width: 4,
              bgcolor: 'secondary.main',
            },
          }}
        >
          <CardContent
            sx={{
              p: { xs: 1.75, sm: 2.25, md: 2.5 },
              '&:last-child': { pb: { xs: 1.75, sm: 2.25, md: 2.5 } },
            }}
          >
            <Stack spacing={2.25} alignItems="center">
              <Box
                sx={{
                  px: 1.5,
                  py: 0.65,
                  borderRadius: (t) => t.radius('sm'),
                  fontSize: '0.8rem',
                  fontWeight: 800,
                  color: 'secondary.dark',
                  bgcolor: 'secondary.light',
                  border: '1px solid',
                  borderColor: 'rgba(196, 92, 74, 0.4)',
                }}
              >
                تکمیل ثبت
              </Box>

              <Box
                sx={{
                  width: '100%',
                  maxWidth: 640,
                  mx: 'auto',
                  p: { xs: 2.5, sm: 3.5 },
                  borderRadius: (t) => t.radius('md'),
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.default',
                  textAlign: 'center',
                }}
              >
                <CheckCircleOutline color="success" sx={{ fontSize: 64, mb: 1.5 }} />
                <Typography variant="h2" mb={1}>
                  خرابی با موفقیت ثبت شد
                </Typography>
                <Typography color="text.secondary" mb={1}>
                  {completedCount > 1
                    ? `${toFaNumber(completedCount)} مورد خرابی در یک پرونده ثبت شد.`
                    : 'پرونده خرابی برای خودرو ایجاد شد.'}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2.5}>
                  تا زمان بستن این پرونده، ثبت خرابی جدید برای همین خودرو ممکن نیست.
                </Typography>
                <Box
                  sx={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 1.5,
                    py: 0.75,
                    mb: 2.5,
                    borderRadius: (t) => t.radius('sm'),
                    bgcolor: completedFault?.sap_notification_number
                      ? 'success.light'
                      : 'warning.light',
                    color: completedFault?.sap_notification_number
                      ? 'success.dark'
                      : 'warning.dark',
                    fontWeight: 800,
                  }}
                >
                  <span>PM Notification SAP:</span>
                  <span>{completedFault?.sap_notification_number || 'در صف ارسال'}</span>
                </Box>
                {selectedVehicle && (
                  <Typography fontWeight={700} mb={2.5}>
                    {selectedVehicle.license_plate} — {selectedVehicle.vehicle_number}
                  </Typography>
                )}
                <RouterLink
                  to={selectedVehicle ? `/vehicles/${selectedVehicle.id}` : '/vehicles'}
                  style={{ textDecoration: 'none' }}
                >
                  <Button variant="contained" size="large">
                    مشاهده خودرو
                  </Button>
                </RouterLink>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    );
  }

  return (
    <Stack spacing={{ xs: 1.5, md: 2 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="ثبت خرابی موردی"
        breadcrumbs={[
          { label: 'راننده' },
          { label: 'ثبت خرابی موردی' },
        ]}
      />

      <Card
        variant="outlined"
        sx={{
          width: '100%',
          borderColor: 'divider',
          borderRadius: (t) => t.radius('md'),
          boxShadow: '0 8px 22px rgba(15, 107, 76, 0.07)',
          bgcolor: 'background.paper',
          overflow: 'hidden',
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            insetInlineStart: 0,
            top: 0,
            bottom: 0,
            width: 4,
            bgcolor: 'secondary.main',
          },
        }}
      >
        <CardContent
          sx={{
            p: { xs: 1.75, sm: 2.25, md: 2.5 },
            '&:last-child': { pb: { xs: 1.75, sm: 2.25, md: 2.5 } },
          }}
        >
          <Stack spacing={2.25} alignItems="center">
            <Stack direction="row" gap={1} flexWrap="wrap" justifyContent="center" width="100%">
              {stepLabels.map((step) => {
                const active = flowStep === step.key;
                const done =
                  (step.key === 'vehicle' && Boolean(vehicleId)) ||
                  (step.key === 'fault' && selectedCatalogs.length > 0) ||
                  (step.key === 'details' && false);
                return (
                  <Box
                    key={step.key}
                    sx={{
                      px: 1.5,
                      py: 0.65,
                      borderRadius: (t) => t.radius('sm'),
                      fontSize: '0.8rem',
                      fontWeight: active ? 800 : 650,
                      color: active || done ? 'secondary.dark' : 'text.secondary',
                      bgcolor: active || done ? 'secondary.light' : 'action.hover',
                      border: '1px solid',
                      borderColor: active || done ? 'rgba(196, 92, 74, 0.4)' : 'transparent',
                    }}
                  >
                    {step.label}
                  </Box>
                );
              })}
            </Stack>

            <Box
              sx={{
                width: '100%',
                maxWidth: 640,
                mx: 'auto',
                p: { xs: 1.5, sm: 2 },
                borderRadius: (t) => t.radius('md'),
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.default',
              }}
            >
              {!catalogs.length ? (
                <EmptyState
                  title="کاتالوگ خرابی یافت نشد"
                  subtitle="ابتدا همگام‌سازی SAP را اجرا کنید."
                />
              ) : (
                <Stack spacing={2}>
                  <Box>
                    <Typography fontWeight={800} mb={1.25}>
                      {isDriver ? 'خودرو' : 'انتخاب خودرو'}
                    </Typography>
                    {isDriver ? (
                      selectedVehicle ? (
                        <Stack
                          direction="row"
                          alignItems="center"
                          gap={1.25}
                          sx={{
                            p: 1.25,
                            borderRadius: (t) => t.radius('sm'),
                            border: '1px solid',
                            borderColor: 'divider',
                            bgcolor: 'background.paper',
                          }}
                        >
                          <DirectionsCar sx={{ color: 'secondary.main' }} />
                          <Box minWidth={0}>
                            <Typography fontWeight={800}>{selectedVehicle.license_plate}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              {selectedVehicle.vehicle_number}
                            </Typography>
                          </Box>
                        </Stack>
                      ) : vehicles.length > 1 ? (
                        <RtlSelectField
                          label="خودرو"
                          value={vehicleId}
                          displayEmpty
                          onChange={(event) => {
                            setVehicleId(String(event.target.value));
                            setSelectedIds([]);
                            setDescription('');
                            setSubmitError('');
                          }}
                        >
                          <MenuItem value="">
                            <em>انتخاب خودرو</em>
                          </MenuItem>
                          {vehicles.map((item) => (
                            <MenuItem key={item.id} value={item.id}>
                              {item.license_plate} — {item.vehicle_number}
                            </MenuItem>
                          ))}
                        </RtlSelectField>
                      ) : null
                    ) : (
                      <RtlSelectField
                        label="خودرو"
                        value={vehicleId}
                        displayEmpty
                        onChange={(event) => {
                          setVehicleId(String(event.target.value));
                          setSelectedIds([]);
                          setDescription('');
                          setSubmitError('');
                        }}
                      >
                        <MenuItem value="">
                          <em>انتخاب خودرو</em>
                        </MenuItem>
                        {vehicles.map((item) => (
                          <MenuItem key={item.id} value={item.id}>
                            {item.license_plate} — {item.vehicle_number}
                          </MenuItem>
                        ))}
                      </RtlSelectField>
                    )}
                  </Box>

                  {vehicleId && (
                    <Box>
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1.25}
                        gap={1}
                      >
                        <Typography fontWeight={800}>انتخاب خرابی</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {selectedCatalogs.length > 0
                            ? `${toFaNumber(selectedCatalogs.length)} انتخاب‌شده`
                            : `${toFaNumber(groups.reduce((sum, group) => sum + group.items.length, 0))} مورد`}
                        </Typography>
                      </Stack>

                      <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                        می‌توانید چند مورد را با هم انتخاب و یک‌جا ثبت کنید.
                      </Typography>

                      <RtlTextField
                        size="small"
                        fullWidth
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="جستجو در دسته، کد یا شرح..."
                        sx={{ mb: 1.25 }}
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <Search fontSize="small" />
                            </InputAdornment>
                          ),
                        }}
                      />

                      <Box
                        sx={{
                          maxHeight: 340,
                          overflowY: 'auto',
                          borderRadius: (t) => t.radius('md'),
                          border: '1px solid',
                          borderColor: 'divider',
                          bgcolor: 'background.paper',
                          overscrollBehavior: 'contain',
                        }}
                      >
                        {groups.length === 0 ? (
                          <Box p={2}>
                            <Typography variant="body2" color="text.secondary" textAlign="center">
                              موردی یافت نشد
                            </Typography>
                          </Box>
                        ) : (
                          groups.map((group) => {
                            const expanded = expandedCategory === group.category;
                            const selectedInGroup = group.items.filter((item) =>
                              selectedIds.includes(item.id),
                            ).length;
                            return (
                              <Accordion
                                key={group.category}
                                disableGutters
                                elevation={0}
                                expanded={expanded}
                                onChange={(_event, next) =>
                                  setExpandedCategory(next ? group.category : false)
                                }
                                sx={{
                                  '&:before': { display: 'none' },
                                  borderBottom: '1px solid',
                                  borderColor: 'divider',
                                  bgcolor: 'transparent',
                                }}
                              >
                                <AccordionSummary
                                  expandIcon={<ExpandMore />}
                                  sx={{
                                    minHeight: 48,
                                    px: 1.5,
                                    '& .MuiAccordionSummary-content': {
                                      my: 1,
                                      alignItems: 'center',
                                      gap: 1,
                                    },
                                  }}
                                >
                                  <Typography fontWeight={800} flex={1} noWrap>
                                    {group.category}
                                  </Typography>
                                  {selectedInGroup > 0 && (
                                    <Chip
                                      size="small"
                                      color="error"
                                      label={toFaNumber(selectedInGroup)}
                                    />
                                  )}
                                  <Chip
                                    size="small"
                                    label={toFaNumber(group.items.length)}
                                    sx={{ bgcolor: 'primary.light', color: 'primary.dark' }}
                                  />
                                </AccordionSummary>
                                <AccordionDetails sx={{ px: 1, pt: 0, pb: 1 }}>
                                  <Stack spacing={0.75}>
                                    {group.items.map((item) => {
                                      const selected = selectedIds.includes(item.id);
                                      return (
                                        <Box
                                          key={item.id}
                                          onClick={() => toggleCatalog(item)}
                                          sx={{
                                            cursor: 'pointer',
                                            px: 1.25,
                                            py: 1,
                                            borderRadius: (t) => t.radius('sm'),
                                            border: '1px solid',
                                            borderColor: selected ? 'secondary.main' : 'divider',
                                            bgcolor: selected ? 'secondary.light' : 'background.paper',
                                            transition:
                                              'border-color 0.15s ease, background-color 0.15s ease',
                                            '&:hover': {
                                              borderColor: selected ? 'secondary.dark' : 'primary.main',
                                            },
                                          }}
                                        >
                                      <Stack direction="row" justifyContent="space-between" gap={1} alignItems="center">
                                            <Box minWidth={0} flex={1}>
                                              <Typography fontWeight={800} noWrap>
                                                {item.code_text}
                                              </Typography>
                                              <Typography variant="caption" color="text.secondary">
                                                {item.code}
                                                {item.defect_class_text
                                                  ? ` · ${item.defect_class_text}`
                                                  : ''}
                                                {` · شدت ${SEVERITY_LABELS[severityFromDefectClass(item.defect_class)]}`}
                                              </Typography>
                                            </Box>
                                            {selected && (
                                              <CheckCircle sx={{ color: 'error.main', fontSize: 20 }} />
                                            )}
                                          </Stack>
                                        </Box>
                                      );
                                    })}
                                  </Stack>
                                </AccordionDetails>
                              </Accordion>
                            );
                          })
                        )}
                      </Box>
                    </Box>
                  )}

                  {selectedCatalogs.length > 0 && severity && selectedVehicle && (
                    <Box
                      sx={{
                        p: 1.5,
                        borderRadius: (t) => t.radius('md'),
                        border: '1px solid',
                        borderColor: 'rgba(201, 65, 50, 0.22)',
                        bgcolor: 'background.paper',
                      }}
                    >
                      <Stack
                        direction="row"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1}
                        gap={1}
                      >
                        <Typography fontWeight={800}>
                          {toFaNumber(selectedCatalogs.length)} خرابی انتخاب‌شده
                        </Typography>
                        <Chip size="small" label={selectedVehicle.license_plate} />
                      </Stack>

                      <Stack spacing={0.75} mb={1.5}>
                        {selectedCatalogs.map((item) => {
                          const itemSeverity = severityFromDefectClass(item.defect_class);
                          return (
                            <Box
                              key={item.id}
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                                px: 1,
                                py: 0.75,
                                borderRadius: (t) => t.radius('sm'),
                                border: '1px solid',
                                borderColor: 'divider',
                                bgcolor: 'background.default',
                              }}
                            >
                              <Box minWidth={0} flex={1}>
                                <Typography fontWeight={700} noWrap fontSize="0.875rem">
                                  {item.code_text || item.code}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {item.code}
                                  {item.group_text ? ` · ${item.group_text}` : ''}
                                </Typography>
                              </Box>
                              <Chip
                                size="small"
                                color="error"
                                variant="outlined"
                                label={SEVERITY_LABELS[itemSeverity]}
                              />
                              <Box
                                component="button"
                                type="button"
                                aria-label="حذف"
                                onClick={() => removeCatalog(item.id)}
                                sx={{
                                  border: 'none',
                                  background: 'transparent',
                                  cursor: 'pointer',
                                  color: 'text.secondary',
                                  fontSize: '1.25rem',
                                  lineHeight: 1,
                                  p: 0.25,
                                  '&:hover': { color: 'error.main' },
                                }}
                              >
                                ×
                              </Box>
                            </Box>
                          );
                        })}
                      </Stack>

                      <RtlTextField
                        label="شرح تکمیلی"
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        multiline
                        minRows={2}
                        fullWidth
                        placeholder="در صورت نیاز جزئیات بیشتری بنویسید"
                      />

                      {canEdit && (
                        <Stack direction="row" justifyContent="flex-end" mt={1.5}>
                          <Button
                            variant="contained"
                            color="error"
                            startIcon={<ReportProblem />}
                            loading={submitting}
                            onClick={submit}
                          >
                            {selectedCatalogs.length > 1
                              ? `ثبت ${toFaNumber(selectedCatalogs.length)} خرابی`
                              : 'ثبت خرابی'}
                          </Button>
                        </Stack>
                      )}
                    </Box>
                  )}

                  {submitError && <Alert severity="error">{submitError}</Alert>}
                </Stack>
              )}
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
