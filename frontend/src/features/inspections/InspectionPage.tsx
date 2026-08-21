import { useEffect, useMemo, useRef, useState, type UIEvent } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  Link,
  MenuItem,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { Cancel, CheckCircle, CheckCircleOutline, Logout } from '@mui/icons-material';
import { ReportProblem } from '../../components/icons3d/Icons3D';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { Button } from '../../components/Button';
import { PageHeader } from '../../components/PageHeader';
import { RtlAutocomplete } from '../../components/RtlAutocomplete';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type {
  AuthUser,
  ChecklistResult,
  Driver,
  FailureSeverity,
  InspectionDefectOption,
  InspectionTemplate,
  OdometerReading,
  Vehicle,
} from '../../types/fmms';
import { toFaNumber } from '../../utils/format';
import { severityFromDefectClass } from '../../utils/severity';

type ChecklistDraft = {
  templateId: string;
  category: string;
  code: string;
  description: string;
  result: ChecklistResult | '';
  notes: string;
  severity: FailureSeverity | '';
  defectOptionId: string;
  errors: { result?: string; notes?: string; defectOption?: string };
};

const SEVERITY_LABELS: Record<FailureSeverity, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

const SEVERITY_CHIP_STYLE: Record<FailureSeverity, { bg: string; color: string; border: string }> = {
  LOW: { bg: 'rgba(100, 112, 103, 0.12)', color: '#4b544e', border: 'rgba(100, 112, 103, 0.35)' },
  MEDIUM: { bg: 'rgba(210, 138, 32, 0.14)', color: '#8a5a13', border: 'rgba(210, 138, 32, 0.42)' },
  HIGH: { bg: 'rgba(201, 65, 50, 0.12)', color: '#a3352a', border: 'rgba(201, 65, 50, 0.36)' },
  CRITICAL: { bg: '#c94132', color: '#ffffff', border: '#c94132' },
};

const VEHICLE_PAGE_SIZE = 20;

const OPEN_REPAIR_TERMINAL = new Set([
  'COMPLETED',
  'ACCEPTED_BY_DRIVER',
  'REJECTED_BY_DRIVER',
  'REJECTED_BY_TRANSPORT',
  'CANCELLED',
]);

function mergeVehicles(current: Vehicle[], incoming: Vehicle[]): Vehicle[] {
  const seen = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !seen.has(item.id))];
}

function isAdminUser(user: AuthUser | null): boolean {
  if (!user) return false;
  return user.is_superuser || user.is_staff || user.role === 'ADMIN';
}

function isDriverUser(user: AuthUser | null): boolean {
  return Boolean(user && user.role === 'DRIVER');
}

function vehicleAssignedToDriver(vehicle: Vehicle, customerNumber: string): boolean {
  return (
    vehicle.driver1?.customer_number === customerNumber ||
    vehicle.driver2?.customer_number === customerNumber
  );
}

function normalizeTemplates(
  payload: { results?: InspectionTemplate[] } | InspectionTemplate[],
): InspectionTemplate[] {
  const items = Array.isArray(payload) ? payload : (payload.results ?? []);
  return [...items].sort(
    (a, b) =>
      a.group_text.localeCompare(b.group_text, 'fa') ||
      a.code.localeCompare(b.code, 'en', { numeric: true }),
  );
}

function hasAssignedDriver(vehicle: Vehicle): boolean {
  return Boolean(vehicle.driver1 || vehicle.driver2);
}

function normalizePersonnelNumber(value: string): string {
  return value.trim();
}

function findDriverByPersonnelNumber(
  drivers: Driver[],
  personnelNumber: string,
): Driver | null {
  const needle = normalizePersonnelNumber(personnelNumber);
  if (!needle) return null;
  return (
    drivers.find(
      (driver) => normalizePersonnelNumber(driver.personnel_number || '') === needle,
    ) ?? null
  );
}

function assignedVehicleIdForDriver(driver: Driver): string {
  return (
    driver.current_vehicle_as_driver?.id ||
    driver.current_vehicle_as_assistant?.id ||
    ''
  );
}

function DriverNameLink({
  driver,
}: {
  driver: Vehicle['driver1'];
}) {
  const label = driver?.name || driver?.customer_number || '—';
  if (!driver?.id) {
    return (
      <Typography fontWeight={700} noWrap>
        {label}
      </Typography>
    );
  }
  return (
    <Link
      component={RouterLink}
      to={`/drivers/${driver.id}`}
      underline="hover"
      fontWeight={700}
      noWrap
      display="block"
    >
      {label}
    </Link>
  );
}

function ResultToggle({
  value,
  onChange,
  size = 'small',
}: {
  value: ChecklistResult | '';
  onChange: (next: ChecklistResult) => void;
  size?: 'small' | 'medium';
}) {
  const large = size === 'medium';
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value || null}
      onChange={(_event, next: ChecklistResult | null) => {
        if (next) {
          onChange(next);
          return;
        }
        // Re-selecting the active option yields null; re-fire so PASS advances again after «قبلی».
        if (value === 'PASS' || value === 'FAIL') {
          onChange(value);
        }
      }}
      sx={{
        flexShrink: 0,
        gap: 1.5,
        width: large ? '100%' : 'auto',
        '& .MuiToggleButtonGroup-grouped': {
          border: '1px solid',
          borderRadius: (t) => `${t.radius('sm')} !important`,
          px: large ? 2.5 : 1.75,
          py: large ? 1.1 : 0.5,
          flex: large ? 1 : 'initial',
          fontWeight: 800,
          fontSize: large ? '0.95rem' : '0.8rem',
          textTransform: 'none',
          gap: 0.75,
          '&:not(:first-of-type)': { ml: 0, borderRadius: (t) => `${t.radius('sm')} !important` },
          '&:first-of-type': { borderRadius: (t) => `${t.radius('sm')} !important` },
        },
      }}
    >
      <ToggleButton
        value="PASS"
        sx={{
          color: 'text.secondary',
          borderColor: 'divider !important',
          bgcolor: 'background.paper',
          boxShadow: 'none',
          '&:hover': {
            bgcolor: 'primary.light',
            borderColor: 'primary.main !important',
            color: 'primary.dark',
          },
          '&.Mui-selected, &.Mui-selected:hover': {
            bgcolor: 'primary.main',
            borderColor: 'primary.main !important',
            color: 'primary.contrastText',
            boxShadow: '0 2px 10px rgba(15, 107, 76, 0.28)',
          },
        }}
      >
        <CheckCircle sx={{ fontSize: large ? 22 : 18 }} />
        سالم
      </ToggleButton>
      <ToggleButton
        value="FAIL"
        sx={{
          color: 'text.secondary',
          borderColor: 'divider !important',
          bgcolor: 'background.paper',
          boxShadow: 'none',
          '&:hover': {
            bgcolor: 'secondary.light',
            borderColor: 'secondary.main !important',
            color: 'secondary.dark',
          },
          '&.Mui-selected, &.Mui-selected:hover': {
            bgcolor: 'secondary.main',
            borderColor: 'secondary.main !important',
            color: 'secondary.contrastText',
            boxShadow: '0 2px 10px rgba(196, 92, 74, 0.32)',
          },
        }}
      >
        <Cancel sx={{ fontSize: large ? 22 : 18 }} />
        خراب
      </ToggleButton>
    </ToggleButtonGroup>
  );
}

function isItemComplete(item: ChecklistDraft): boolean {
  if (!item.result) return false;
  if (item.result === 'FAIL') {
    return Boolean(item.defectOptionId && item.severity);
  }
  return true;
}

/** Keep only digits; convert Persian/Arabic numerals to ASCII. */
function digitsOnly(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/\D/g, '');
}

/** Matches Django PositiveIntegerField / DB integer upper bound. */
const MAX_ODOMETER_KM = 2_147_483_647;
/** Must match backend ``RecordVehicleOdometerService`` minimum daily growth. */
const MIN_DAILY_DELTA_KM = 10;

function todayDateIso(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function readingDateKey(reading: OdometerReading): string {
  return reading.reading_date.slice(0, 10);
}

/** Latest odometer from a day before today (never today's reading). */
function pickPreviousOdometer(readings: OdometerReading[]): OdometerReading | null {
  if (!readings.length) return null;
  const today = todayDateIso();
  const priorDays = readings
    .filter((item) => readingDateKey(item) < today)
    .sort((a, b) => readingDateKey(b).localeCompare(readingDateKey(a)));
  return priorDays[0] ?? null;
}

function pickTodayOdometer(readings: OdometerReading[]): OdometerReading | null {
  const today = todayDateIso();
  return readings.find((item) => readingDateKey(item) === today) ?? null;
}

/**
 * Daily vehicle inspection flow wizard:
 * personnel lookup (admin) / assigned vehicle (driver) → odometer → checklist → submit.
 */
export function InspectionPage() {
  const canEdit = useCanEdit();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [bootLoading, setBootLoading] = useState(true);
  const [bootError, setBootError] = useState('');

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclePage, setVehiclePage] = useState(1);
  const [vehicleTotal, setVehicleTotal] = useState(0);
  const [vehiclesLoadingMore, setVehiclesLoadingMore] = useState(false);
  const vehiclesLoadingRef = useRef(false);
  const vehiclePagingRef = useRef({ page: 1, total: 0, count: 0 });
  const [selectedVehicleId, setSelectedVehicleId] = useState('');
  const [adminPersonnelNumber, setAdminPersonnelNumber] = useState('');
  const [personnelLookupError, setPersonnelLookupError] = useState('');
  const [personnelLookupLoading, setPersonnelLookupLoading] = useState(false);
  const [flowStep, setFlowStep] = useState<'vehicle' | 'odometer' | 'checklist'>('vehicle');

  vehiclePagingRef.current = {
    page: vehiclePage,
    total: vehicleTotal,
    count: vehicles.length,
  };

  const vehicleHasMore = vehicles.length < vehicleTotal;

  const [odometer, setOdometer] = useState('');
  const [odometerError, setOdometerError] = useState('');
  const [previousOdometer, setPreviousOdometer] = useState<OdometerReading | null>(null);
  const [previousOdometerLoading, setPreviousOdometerLoading] = useState(false);
  const [odometerSaving, setOdometerSaving] = useState(false);
  const [odometerRecorded, setOdometerRecorded] = useState(false);

  const [items, setItems] = useState<ChecklistDraft[]>([]);
  const [wizardIndex, setWizardIndex] = useState(0);

  const [defectOptions, setDefectOptions] = useState<InspectionDefectOption[]>([]);
  const [defectOptionsLoading, setDefectOptionsLoading] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [hadFailures, setHadFailures] = useState(false);
  const [completedInspection, setCompletedInspection] = useState<{
    id: string;
    vehicle_id: string;
    driver_id: string;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState<'exit' | 'fault' | 'disposition' | ''>('');
  const [actionError, setActionError] = useState('');
  const [actionInfo, setActionInfo] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [faultReported, setFaultReported] = useState(false);
  /** True after distribution marks usable (no open fault/repair). */
  const [exitUnlocked, setExitUnlocked] = useState(false);
  /** True after a successful exit, or when vehicle is already EXITED_CENTER. */
  const [exitedCenter, setExitedCenter] = useState(false);

  const admin = isAdminUser(user);
  const driverMode = isDriverUser(user);
  const linkedCustomerNumber = user?.linked_driver?.customer_number || '';
  const isOperationalVehicle = (vehicle: Vehicle) => vehicle.status === 'ACTIVE';
  const selectableVehicles = useMemo(() => {
    return vehicles.filter((vehicle) => {
      if (!isOperationalVehicle(vehicle)) return false;
      if (driverMode) {
        return Boolean(
          linkedCustomerNumber && vehicleAssignedToDriver(vehicle, linkedCustomerNumber),
        );
      }
      return admin ? hasAssignedDriver(vehicle) : hasAssignedDriver(vehicle);
    });
  }, [admin, driverMode, linkedCustomerNumber, vehicles]);
  const selectedVehicle =
    selectableVehicles.find((item) => item.id === selectedVehicleId) ??
    vehicles.find((item) => item.id === selectedVehicleId) ??
    null;
  const selectedVehicleOperational = Boolean(
    selectedVehicle && isOperationalVehicle(selectedVehicle),
  );

  const completedCount = items.filter((item) => isItemComplete(item)).length;
  const progress = items.length
    ? Math.round(((wizardIndex + 1) / items.length) * 100)
    : 0;
  const currentItem = items[wizardIndex] ?? null;
  const isLastItem = items.length > 0 && wizardIndex >= items.length - 1;
  const currentComplete = currentItem ? isItemComplete(currentItem) : false;
  const checklistComplete = items.length > 0 && items.every(isItemComplete);

  // The defect catalog is small and has its own grouping, unrelated to the
  // checklist's — so it is fetched once, not per checklist item.
  useEffect(() => {
    let cancelled = false;
    setDefectOptionsLoading(true);
    api
      .listInspectionDefectOptions()
      .then((page) => {
        if (cancelled) return;
        setDefectOptions(Array.isArray(page) ? page : (page.results ?? []));
      })
      .catch(() => {
        if (!cancelled) setDefectOptions([]);
      })
      .finally(() => {
        if (!cancelled) setDefectOptionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const odometerValid = useMemo(() => {
    const odometerValue = Number(odometer);
    return (
      Boolean(odometer.trim()) &&
      !Number.isNaN(odometerValue) &&
      odometerValue >= 0 &&
      odometerValue <= MAX_ODOMETER_KM
    );
  }, [odometer]);

  const canSubmit = useMemo(() => {
    if (!selectedVehicleId || !selectedVehicleOperational || items.length === 0 || submitting) {
      return false;
    }
    return odometerValid && checklistComplete;
  }, [
    checklistComplete,
    items.length,
    odometerValid,
    selectedVehicleId,
    selectedVehicleOperational,
    submitting,
  ]);

  const assignedVehicleForDriver = useMemo(() => {
    if (!driverMode || !linkedCustomerNumber) return null;
    const assigned = selectableVehicles;
    return assigned.length === 1 ? assigned[0] : null;
  }, [driverMode, linkedCustomerNumber, selectableVehicles]);

  const loadVehiclesPage = async (page: number, append: boolean) => {
    if (vehiclesLoadingRef.current) return null;
    vehiclesLoadingRef.current = true;
    if (append) setVehiclesLoadingMore(true);
    try {
      const result = await api.listVehicles('', 'license_plate', {
        page,
        pageSize: VEHICLE_PAGE_SIZE,
      });
      setVehicleTotal(result.count);
      setVehiclePage(page);
      setVehicles((prev) => (append ? mergeVehicles(prev, result.results) : result.results));
      return result;
    } finally {
      vehiclesLoadingRef.current = false;
      setVehiclesLoadingMore(false);
    }
  };

  const loadMoreVehicles = () => {
    const { page, total, count } = vehiclePagingRef.current;
    if (count >= total || vehiclesLoadingRef.current) return;
    void loadVehiclesPage(page + 1, true);
  };

  const handleVehicleMenuScroll = (event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    if (target.scrollTop + target.clientHeight >= target.scrollHeight - 48) {
      loadMoreVehicles();
    }
  };

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      setBootLoading(true);
      setBootError('');
      try {
        const [me, templatePayload] = await Promise.all([
          api.me(),
          api.listInspectionTemplates(),
        ]);
        if (cancelled) return;
        setUser(me);

        const nextTemplates = normalizeTemplates(templatePayload).filter((item) => item.is_active);
        setItems(
          nextTemplates.map((template) => ({
            templateId: template.id,
            category: template.group_text,
            code: template.code,
            description: template.code_text,
            result: '',
            notes: '',
            severity: '',
            defectOptionId: '',
            errors: {},
          })),
        );
        setWizardIndex(0);

        if (isAdminUser(me)) {
          // Admin resolves vehicle via driver personnel number — no vehicle list needed.
          setVehicles([]);
          setVehicleTotal(0);
          setVehiclePage(1);
          setFlowStep('vehicle');
          return;
        }

        const vehiclePageResult = await api.listVehicles('', 'license_plate', {
          page: 1,
          pageSize: VEHICLE_PAGE_SIZE,
        });
        if (cancelled) return;
        let loadedVehicles = vehiclePageResult.results;
        let loadedTotal = vehiclePageResult.count;
        let loadedPage = 1;
        setVehicles(loadedVehicles);
        setVehicleTotal(loadedTotal);
        setVehiclePage(loadedPage);

        if (isDriverUser(me)) {
          const customer = me.linked_driver?.customer_number || '';
          if (!me.personnel_number?.trim() || !customer) {
            setBootError(
              'حساب کاربری شما به کد پرسنلی SAP یا راننده فعال متصل نیست. با مدیر سیستم هماهنگ کنید.',
            );
            return;
          }
          const findAssigned = (list: Vehicle[]) =>
            list.filter(
              (item) =>
                item.status === 'ACTIVE' && vehicleAssignedToDriver(item, customer),
            );

          let assigned = findAssigned(loadedVehicles);
          while (assigned.length < 1 && loadedVehicles.length < loadedTotal) {
            loadedPage += 1;
            const next = await api.listVehicles('', 'license_plate', {
              page: loadedPage,
              pageSize: VEHICLE_PAGE_SIZE,
            });
            if (cancelled) return;
            loadedVehicles = mergeVehicles(loadedVehicles, next.results);
            loadedTotal = next.count;
            setVehicles(loadedVehicles);
            setVehicleTotal(loadedTotal);
            setVehiclePage(loadedPage);
            assigned = findAssigned(loadedVehicles);
          }

          if (assigned.length === 1) {
            setSelectedVehicleId(assigned[0].id);
            setFlowStep('odometer');
          } else if (assigned.length > 1) {
            setFlowStep('vehicle');
          } else {
            setBootError('خودروی عملیاتی اساین‌شده به شما یافت نشد.');
          }
        } else {
          setFlowStep('vehicle');
        }
      } catch (err) {
        if (!cancelled) {
          setBootError(err instanceof Error ? err.message : 'خطا در آماده‌سازی فرم بازرسی');
        }
      } finally {
        if (!cancelled) setBootLoading(false);
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!admin && assignedVehicleForDriver) {
      setSelectedVehicleId(assignedVehicleForDriver.id);
      setFlowStep('odometer');
    }
  }, [admin, assignedVehicleForDriver]);

  useEffect(() => {
    if (!selectedVehicleId) {
      setPreviousOdometer(null);
      setOdometer('');
      setOdometerRecorded(false);
      setOdometerError('');
      return;
    }

    let cancelled = false;
    setPreviousOdometerLoading(true);
    setOdometer('');
    setOdometerRecorded(false);
    setOdometerError('');
    void api
      .getOdometerHistory(selectedVehicleId)
      .then((readings) => {
        if (cancelled) return;
        const list = Array.isArray(readings) ? readings : [];
        setPreviousOdometer(pickPreviousOdometer(list));
        const todayReading = pickTodayOdometer(list);
        // Only hydrate today's already-saved value — never invent previous+delta.
        if (todayReading) {
          setOdometer(String(todayReading.odometer_km));
          setOdometerRecorded(true);
        }
      })
      .catch(() => {
        if (!cancelled) setPreviousOdometer(null);
      })
      .finally(() => {
        if (!cancelled) setPreviousOdometerLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedVehicleId]);

  const updateItem = (index: number, patch: Partial<ChecklistDraft>) => {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              ...patch,
              errors: {},
            }
          : item,
      ),
    );
  };

  const goNext = () => {
    setWizardIndex((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
  };

  const goPrev = () => {
    setWizardIndex((current) => Math.max(current - 1, 0));
  };

  const handleResultChange = (next: ChecklistResult) => {
    if (!currentItem) return;
    updateItem(wizardIndex, {
      result: next,
      notes: next === 'FAIL' ? currentItem.notes : '',
      severity: next === 'FAIL' ? currentItem.severity : '',
      defectOptionId: next === 'FAIL' ? currentItem.defectOptionId : '',
    });
    if (next === 'PASS' && !isLastItem) {
      // Advance after PASS so the driver sees one item at a time.
      window.setTimeout(() => {
        setWizardIndex((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
      }, 180);
    }
  };

  const validateCurrentItem = (): boolean => {
    if (!currentItem) return false;
    const errors: ChecklistDraft['errors'] = {};
    if (!currentItem.result) {
      errors.result = 'وضعیت الزامی است';
    }
    if (currentItem.result === 'FAIL' && !currentItem.defectOptionId) {
      errors.defectOption = 'انتخاب نوع خرابی الزامی است';
    }
    if (Object.keys(errors).length) {
      updateItem(wizardIndex, { errors });
      return false;
    }
    return true;
  };

  const handleNext = () => {
    if (!validateCurrentItem()) return;
    if (!isLastItem) goNext();
  };

  const validate = (): boolean => {
    let ok = true;
    if (!selectedVehicleId || !selectedVehicleOperational) {
      setSubmitError('ثبت چک‌لیست فقط برای خودروی عملیاتی مجاز است.');
      ok = false;
    }
    if (!odometer.trim() || Number.isNaN(Number(odometer)) || Number(odometer) < 0) {
      setOdometerError('مقدار کیلومتر معتبر الزامی است');
      ok = false;
    } else {
      setOdometerError('');
    }

    setItems((current) =>
      current.map((item) => {
        const errors: ChecklistDraft['errors'] = {};
        if (!item.result) {
          errors.result = 'وضعیت الزامی است';
          ok = false;
        }
        if (item.result === 'FAIL' && !item.defectOptionId) {
          errors.defectOption = 'انتخاب نوع خرابی الزامی است';
          ok = false;
        }
        return { ...item, errors };
      }),
    );
    return ok;
  };

  const submit = async () => {
    if (!validate() || !selectedVehicleId) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      const payloadItems = items.map((item) => ({
        category: item.category,
        description: item.description,
        result: item.result as ChecklistResult,
        notes: item.result === 'FAIL' ? item.notes : null,
        severity: item.result === 'FAIL' ? (item.severity as FailureSeverity) : null,
      }));

      const driverId =
        selectedVehicle?.driver1?.id ||
        selectedVehicle?.driver2?.id ||
        null;
      const created = await api.createInspection({
        vehicle_id: selectedVehicleId,
        inspection_type: 'PRE_TRIP',
        odometer_value: Number(odometer),
        odometer_unit: 'KM',
        inspected_at: new Date().toISOString(),
        driver_id: driverId,
        items: payloadItems,
      });
      const submitted = await api.submitInspection(created.id);
      setHadFailures(Boolean(submitted.has_failures));
      setCompletedInspection({
        id: submitted.id,
        vehicle_id: submitted.vehicle_id,
        driver_id:
          submitted.driver_id ||
          created.driver_id ||
          driverId ||
          '',
      });
      setActionError('');
      setActionInfo('');
      setActionSuccess('');
      setFaultReported(false);
      setExitUnlocked(false);
      setExitedCenter(selectedVehicle?.status === 'EXITED_CENTER');
      setCompleted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'ثبت بازرسی انجام نشد');
    } finally {
      setSubmitting(false);
    }
  };

  const resolveDriverIdForExit = async (): Promise<string> => {
    if (completedInspection?.driver_id) return completedInspection.driver_id;
    const fromVehicle =
      selectedVehicle?.driver1?.id || selectedVehicle?.driver2?.id || '';
    if (fromVehicle) return fromVehicle;

    const customerNumber =
      selectedVehicle?.driver1?.customer_number ||
      selectedVehicle?.driver2?.customer_number ||
      '';
    if (!customerNumber) return '';

    const page = await api.listDrivers({
      search: customerNumber,
      page: 1,
      pageSize: 20,
    });
    const match = (page.results ?? []).find(
      (driver) => driver.customer_number === customerNumber,
    );
    return match?.id ?? '';
  };

  const handleExitCenter = async () => {
    if (!completedInspection || exitedCenter) return;
    // After اعلام خرابی, exit stays hidden until distribution unlocks it.
    if (faultReported && !exitUnlocked) return;
    setActionLoading('exit');
    setActionError('');
    setActionInfo('');
    setActionSuccess('');
    try {
      const driverId = await resolveDriverIdForExit();
      if (!driverId) {
        setActionError('راننده تخصیص‌یافته برای ثبت خروج یافت نشد.');
        return;
      }
      await api.driverExitCenter(driverId, {
        vehicle_id: completedInspection.vehicle_id,
        inspection_id: completedInspection.id,
      });
      setCompletedInspection((current) =>
        current ? { ...current, driver_id: driverId } : current,
      );
      setExitedCenter(true);
      setActionSuccess('خروج خودرو از مرکز ثبت شد.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'ثبت خروج از مرکز انجام نشد';
      const alreadyExited =
        /only active vehicles can exit/i.test(message) ||
        /VEHICLE_NOT_ACTIVE/i.test(message) ||
        /خارج شده از مرکز/i.test(message);
      if (alreadyExited) {
        setExitedCenter(true);
        setActionInfo('این خودرو قبلاً از مرکز خارج شده است.');
        return;
      }
      setActionError(message);
    } finally {
      setActionLoading('');
    }
  };

  const handleReportFault = async () => {
    if (!completedInspection) return;
    setActionLoading('fault');
    setActionError('');
    setActionInfo('');
    setActionSuccess('');
    try {
      await api.reportInspectionFault(completedInspection.id);
      setFaultReported(true);
      setExitUnlocked(false);
      setActionSuccess(
        'خرابی ثبت شد و به واحد توزیع ارسال شد. تا تعیین تکلیف، خروج مجاز نیست.',
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'اعلام خرابی انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const handleCheckDisposition = async () => {
    if (!completedInspection) return;
    setActionLoading('disposition');
    setActionError('');
    setActionInfo('');
    setActionSuccess('');
    try {
      const [faultsPage, repairsPage] = await Promise.all([
        api.listFaults(completedInspection.vehicle_id, { page: 1, pageSize: 50 }),
        api.listRepairOrders({
          vehicleId: completedInspection.vehicle_id,
          page: 1,
          pageSize: 50,
        }),
      ]);
      const openFault = (faultsPage.results ?? []).some((fault) => fault.status !== 'CLOSED');
      const openRepair = (repairsPage.results ?? []).some(
        (order) => !OPEN_REPAIR_TERMINAL.has(order.status),
      );
      if (openFault || openRepair) {
        setExitUnlocked(false);
        setActionError(
          openRepair
            ? 'خودرو برای تعمیر ارجاع شده و هنوز خروج مجاز نیست.'
            : 'هنوز تصمیم واحد توزیع ثبت نشده است.',
        );
        return;
      }
      setExitUnlocked(true);
      setActionSuccess(
        'واحد توزیع خودرو را قابل‌استفاده اعلام کرد. می‌توانید گرفتن خودرو و خروج از مرکز را تایید کنید.',
      );
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'بررسی تصمیم توزیع انجام نشد',
      );
    } finally {
      setActionLoading('');
    }
  };

  const validateOdometerStep = (): boolean => {
    if (!odometer.trim() || Number.isNaN(Number(odometer)) || Number(odometer) < 0) {
      setOdometerError('مقدار کیلومتر معتبر الزامی است');
      return false;
    }
    if (Number(odometer) > MAX_ODOMETER_KM) {
      setOdometerError(`حداکثر مقدار کیلومتر ${toFaNumber(MAX_ODOMETER_KM)} است`);
      return false;
    }
    if (previousOdometer) {
      const minimum = previousOdometer.odometer_km + MIN_DAILY_DELTA_KM;
      if (Number(odometer) < minimum) {
        setOdometerError(
          `حداقل کیلومتر قابل ثبت ${toFaNumber(minimum)} است (آخرین ثبت‌شده: ${toFaNumber(previousOdometer.odometer_km)} + ${toFaNumber(MIN_DAILY_DELTA_KM)})`,
        );
        return false;
      }
    }
    setOdometerError('');
    return true;
  };

  const goToOdometer = () => {
    if (!selectedVehicleId || !selectedVehicleOperational) return;
    setWizardIndex(0);
    setFlowStep('odometer');
  };

  const resolveAdminVehicleByPersonnel = async () => {
    const personnel = normalizePersonnelNumber(adminPersonnelNumber);
    if (!personnel) {
      setPersonnelLookupError('کد پرسنلی راننده را وارد کنید.');
      return;
    }

    setPersonnelLookupLoading(true);
    setPersonnelLookupError('');
    try {
      const page = await api.listDrivers({
        search: personnel,
        status: 'ACTIVE',
        page: 1,
        pageSize: 20,
      });
      const driver = findDriverByPersonnelNumber(page.results ?? [], personnel);
      if (!driver) {
        setSelectedVehicleId('');
        setPersonnelLookupError('راننده‌ای با این کد پرسنلی یافت نشد.');
        return;
      }

      const vehicleId = assignedVehicleIdForDriver(driver);
      if (!vehicleId) {
        setSelectedVehicleId('');
        setPersonnelLookupError(
          'برای راننده با این کد پرسنلی خودرویی تخصیص داده نشده است.',
        );
        return;
      }

      const vehicle = await api.getVehicle(vehicleId);
      if (vehicle.status !== 'ACTIVE') {
        setSelectedVehicleId('');
        setPersonnelLookupError(
          'خودروی تخصیص‌یافته به این راننده عملیاتی نیست و ثبت چک‌لیست برای آن مجاز نیست.',
        );
        return;
      }

      setVehicles((prev) => {
        if (prev.some((item) => item.id === vehicle.id)) {
          return prev.map((item) => (item.id === vehicle.id ? vehicle : item));
        }
        return [vehicle, ...prev];
      });
      setSelectedVehicleId(vehicle.id);
      setWizardIndex(0);
      setOdometer('');
      setOdometerError('');
      setOdometerRecorded(false);
      setFlowStep('odometer');
    } catch (err) {
      setSelectedVehicleId('');
      setPersonnelLookupError(
        err instanceof Error ? err.message : 'خطا در جستجوی راننده با کد پرسنلی',
      );
    } finally {
      setPersonnelLookupLoading(false);
    }
  };

  const goToChecklist = async () => {
    if (!validateOdometerStep() || !selectedVehicleId || !selectedVehicleOperational) {
      if (selectedVehicleId && !selectedVehicleOperational) {
        setOdometerError('ثبت چک‌لیست فقط برای خودروی عملیاتی مجاز است.');
      }
      return;
    }

    if (odometerRecorded) {
      setWizardIndex(0);
      setFlowStep('checklist');
      return;
    }

    setOdometerSaving(true);
    setOdometerError('');
    try {
      const today = todayDateIso();
      await api.recordOdometer(selectedVehicleId, {
        reading_date: today,
        odometer_km: Number(odometer),
      });
      setOdometerRecorded(true);
      setWizardIndex(0);
      setFlowStep('checklist');
    } catch (err) {
      setOdometerError(err instanceof Error ? err.message : 'ثبت کیلومتر انجام نشد');
    } finally {
      setOdometerSaving(false);
    }
  };

  const stepLabels = admin
    ? [
        { key: 'vehicle', label: 'کد پرسنلی راننده' },
        { key: 'odometer', label: 'کیلومتر' },
        { key: 'checklist', label: 'چک‌لیست' },
      ]
    : [
        { key: 'odometer', label: 'کیلومتر' },
        { key: 'checklist', label: 'چک‌لیست' },
      ];

  const vehicleSummary = selectedVehicle ? (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 1.25,
        px: 1.5,
        py: 1.35,
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'action.disabledBackground',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          پلاک
        </Typography>
        <Link
          component={RouterLink}
          to={`/vehicles?vehicleId=${encodeURIComponent(selectedVehicle.id)}`}
          underline="hover"
          fontWeight={800}
          display="block"
          color="primary.dark"
        >
          {selectedVehicle.license_plate}
        </Link>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          شناسه خودرو
        </Typography>
        <Typography fontWeight={800}>{selectedVehicle.vehicle_number}</Typography>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          راننده اصلی
        </Typography>
        <DriverNameLink driver={selectedVehicle.driver1} />
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          کمک راننده
        </Typography>
        <DriverNameLink driver={selectedVehicle.driver2} />
      </Box>
    </Box>
  ) : null;

  if (bootLoading) return <LoadingState label="در حال آماده‌سازی بازرسی روزانه" />;
  if (bootError) return <ErrorState message={bootError} onRetry={() => window.location.reload()} />;

  if (!canEdit) {
    return (
      <Stack spacing={2} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="بازرسی روزانه خودرو"
          breadcrumbs={[
            { label: 'راننده' },
            { label: 'بازرسی روزانه' },
          ]}
        />
        <EmptyState
          title="این بخش قابل مشاهده نیست."
          subtitle="بازرسی روزانه یک فرآیند ثبت است و برای نقش ناظر کل (فقط مشاهده) در دسترس نیست."
        />
      </Stack>
    );
  }

  if (!admin && !assignedVehicleForDriver) {
    return (
      <Stack spacing={2} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="بازرسی روزانه خودرو"
          breadcrumbs={[
            { label: 'راننده' },
            { label: 'بازرسی روزانه' },
          ]}
        />
        <EmptyState
          title="در حال حاضر هیچ خودرویی به شما تخصیص داده نشده است."
          subtitle="پس از تخصیص خودرو توسط سامانه، امکان ثبت بازرسی فعال می‌شود."
        />
      </Stack>
    );
  }

  if (completed) {
    return (
      <Stack spacing={{ xs: 1.5, md: 2 }} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="بازرسی روزانه خودرو"
          breadcrumbs={[
            { label: 'راننده' },
            { label: 'بازرسی روزانه' },
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
              bgcolor: 'primary.main',
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
                  color: 'primary.dark',
                  bgcolor: 'primary.light',
                  border: '1px solid',
                  borderColor: 'rgba(15, 107, 76, 0.28)',
                }}
              >
                تکمیل بازرسی
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
                <CheckCircleOutline sx={{ fontSize: 64, mb: 1.5, color: 'success.main' }} />
                <Typography variant="h2" mb={1}>
                  بازرسی با موفقیت ثبت شد
                </Typography>
                <Typography color="text.secondary" mb={2.5}>
                  {exitedCenter
                    ? 'خروج خودرو از مرکز ثبت شده است.'
                    : hadFailures
                      ? faultReported
                        ? exitUnlocked
                          ? 'واحد توزیع خودرو را قابل‌استفاده اعلام کرد. می‌توانید اقدام به خروج کنید.'
                          : 'خرابی اعلام شد. تا تعیین تکلیف در واحد توزیع، دکمه خروج نمایش داده نمی‌شود.'
                        : 'موارد خراب در چک‌لیست ثبت شد. اعلام خرابی اختیاری است و تصمیم خروج با راننده است.'
                      : 'تمام موارد چک‌لیست بدون خرابی ثبت شد.'}
                </Typography>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  useFlexGap
                  justifyContent="center"
                  alignItems="center"
                  sx={{ gap: 2, '& > *': { margin: 0 } }}
                >
                  {hadFailures && !faultReported && (
                    <Button
                      variant="outlined"
                      color="error"
                      size="large"
                      startIcon={<ReportProblem />}
                      onClick={handleReportFault}
                      loading={actionLoading === 'fault'}
                      disabled={actionLoading !== ''}
                    >
                      اعلام خرابی
                    </Button>
                  )}
                  {hadFailures && faultReported && !exitUnlocked && (
                    <Button
                      variant="outlined"
                      size="large"
                      startIcon={<CheckCircle />}
                      onClick={() => void handleCheckDisposition()}
                      loading={actionLoading === 'disposition'}
                      disabled={actionLoading !== ''}
                    >
                      بررسی تصمیم توزیع
                    </Button>
                  )}
                  {!exitedCenter && (!faultReported || exitUnlocked) && (
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<Logout />}
                      onClick={() => void handleExitCenter()}
                      loading={actionLoading === 'exit'}
                      disabled={actionLoading !== ''}
                    >
                      اقدام به خروج
                    </Button>
                  )}
                </Stack>
                {actionInfo && (
                  <Alert severity="info" sx={{ mt: 2, textAlign: 'right' }}>
                    {actionInfo}
                  </Alert>
                )}
                {actionError && (
                  <Alert severity="error" sx={{ mt: 2, textAlign: 'right' }}>
                    {actionError}
                  </Alert>
                )}
                {actionSuccess && (
                  <Alert severity="success" sx={{ mt: 2, textAlign: 'right' }}>
                    {actionSuccess}
                  </Alert>
                )}
                {hadFailures && !faultReported && !exitedCenter ? (
                  <Typography variant="caption" color="text.secondary" display="block" mt={1.25}>
                    اعلام خرابی اختیاری است. در صورت نیاز می‌توانید اقدام به خروج کنید.
                  </Typography>
                ) : null}
                {hadFailures && faultReported && !exitUnlocked && !exitedCenter ? (
                  <Typography variant="caption" color="text.secondary" display="block" mt={1.25}>
                    پس از مشخص شدن وضعیت خرابی در توزیع، با «بررسی تصمیم توزیع» امکان خروج فعال
                    می‌شود.
                  </Typography>
                ) : null}
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
        title="بازرسی روزانه خودرو"
        breadcrumbs={[
          { label: 'راننده' },
          { label: 'بازرسی روزانه' },
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
            bgcolor: 'primary.main',
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
                return (
                  <Box
                    key={step.key}
                    sx={{
                      px: 1.5,
                      py: 0.65,
                      borderRadius: (t) => t.radius('sm'),
                      fontSize: '0.8rem',
                      fontWeight: active ? 800 : 650,
                      color: active ? 'primary.dark' : 'text.secondary',
                      bgcolor: active ? 'primary.light' : 'action.hover',
                      border: '1px solid',
                      borderColor: active ? 'rgba(15, 107, 76, 0.28)' : 'transparent',
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
                {flowStep === 'vehicle' && (
                  <Stack spacing={2}>
                    {admin ? (
                      <>
                        <Typography fontWeight={800}>کد پرسنلی راننده</Typography>
                        <Typography variant="body2" color="text.secondary">
                          کد پرسنلی راننده را وارد کنید تا خودروی تخصیص‌یافته پیدا شود.
                        </Typography>
                        <RtlTextField
                          label="کد پرسنلی"
                          value={adminPersonnelNumber}
                          onChange={(event) => {
                            setAdminPersonnelNumber(event.target.value);
                            setPersonnelLookupError('');
                            setSelectedVehicleId('');
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') {
                              event.preventDefault();
                              void resolveAdminVehicleByPersonnel();
                            }
                          }}
                          error={Boolean(personnelLookupError)}
                          helperText={personnelLookupError || undefined}
                          fullWidth
                          disabled={personnelLookupLoading}
                          inputDir="ltr"
                          inputProps={{
                            autoComplete: 'off',
                            inputMode: 'text',
                          }}
                        />
                        <Stack direction="row" justifyContent="flex-end">
                          <Button
                            variant="contained"
                            disabled={
                              personnelLookupLoading ||
                              !normalizePersonnelNumber(adminPersonnelNumber)
                            }
                            onClick={() => void resolveAdminVehicleByPersonnel()}
                          >
                            {personnelLookupLoading ? 'در حال جستجو...' : 'ادامه'}
                          </Button>
                        </Stack>
                      </>
                    ) : (
                      <>
                        <Typography fontWeight={800}>انتخاب خودرو</Typography>
                        <RtlSelectField
                          label="خودرو"
                          value={selectedVehicleId}
                          displayEmpty
                          onChange={(event) => {
                            setSelectedVehicleId(String(event.target.value));
                            setWizardIndex(0);
                            setOdometer('');
                            setOdometerError('');
                            setOdometerRecorded(false);
                          }}
                          fullWidth
                          MenuProps={{
                            PaperProps: {
                              onScroll: handleVehicleMenuScroll,
                              sx: { maxHeight: 260 },
                            },
                          }}
                        >
                          <MenuItem value="">
                            <em>انتخاب خودرو دارای راننده</em>
                          </MenuItem>
                          {selectableVehicles.map((vehicle) => (
                            <MenuItem key={vehicle.id} value={vehicle.id}>
                              {vehicle.license_plate} — {vehicle.vehicle_number}
                              {vehicle.status_label ? ` (${vehicle.status_label})` : ''}
                            </MenuItem>
                          ))}
                          {(vehiclesLoadingMore || vehicleHasMore) && (
                            <MenuItem
                              disabled
                              value="__loading__"
                              sx={{ justifyContent: 'center', opacity: 1 }}
                            >
                              {vehiclesLoadingMore ? (
                                <CircularProgress size={18} />
                              ) : (
                                <Typography variant="caption" color="text.secondary">
                                  برای موارد بیشتر اسکرول کنید
                                </Typography>
                              )}
                            </MenuItem>
                          )}
                        </RtlSelectField>
                        {!selectableVehicles.length && (
                          <Typography variant="body2" color="text.secondary">
                            {driverMode
                              ? 'خودروی عملیاتی اساین‌شده به کد پرسنلی شما یافت نشد.'
                              : 'خودرویی عملیاتی با راننده تخصیص‌یافته یافت نشد.'}
                          </Typography>
                        )}
                        {selectedVehicleId && !selectedVehicleOperational ? (
                          <Alert severity="warning">
                            این خودرو عملیاتی نیست و ثبت چک‌لیست برای آن مجاز نیست.
                          </Alert>
                        ) : null}
                        {vehicleSummary}
                        <Stack direction="row" justifyContent="flex-end">
                          <Button
                            variant="contained"
                            disabled={!selectedVehicleId || !selectedVehicleOperational}
                            onClick={goToOdometer}
                          >
                            ادامه
                          </Button>
                        </Stack>
                      </>
                    )}
                  </Stack>
                )}

                {flowStep === 'odometer' && (
                  <Stack spacing={2}>
                    <Typography fontWeight={800}>ثبت کیلومتر</Typography>
                    {vehicleSummary}
                    <RtlTextField
                      label="مقدار کیلومتر"
                      value={odometer}
                      onChange={(event) => {
                        setOdometerRecorded(false);
                        setOdometer(digitsOnly(event.target.value).slice(0, 10));
                      }}
                      onKeyDown={(event) => {
                        if (
                          event.key.length === 1 &&
                          !/[0-9۰-۹٠-٩]/.test(event.key) &&
                          !event.ctrlKey &&
                          !event.metaKey
                        ) {
                          event.preventDefault();
                        }
                      }}
                      error={Boolean(odometerError)}
                      helperText={
                        odometerError ||
                        (previousOdometerLoading
                          ? 'در حال دریافت سابقه کیلومتر...'
                          : odometerRecorded
                            ? 'مقدار امروز قبلاً ثبت شده؛ در صورت نیاز می‌توانید اصلاح کنید.'
                            : previousOdometer
                              ? `آخرین مقدار ثبت‌شده (روزهای قبل): ${toFaNumber(previousOdometer.odometer_km)} KM — حداقل امروز: ${toFaNumber(previousOdometer.odometer_km + MIN_DAILY_DELTA_KM)}`
                              : selectedVehicleId
                                ? 'سابقه‌ای ثبت نشده؛ مقدار امروز را وارد کنید (دیفالت ندارد).'
                                : 'فقط عدد وارد کنید')
                      }
                      inputProps={{
                        inputMode: 'numeric',
                        pattern: '[0-9]*',
                        autoComplete: 'off',
                      }}
                      fullWidth
                      disabled={odometerSaving}
                    />
                    <Stack direction="row" justifyContent="space-between">
                      {admin ? (
                        <Button
                          variant="outlined"
                          disabled={odometerSaving}
                          onClick={() => setFlowStep('vehicle')}
                        >
                          قبلی
                        </Button>
                      ) : (
                        <Box />
                      )}
                      <Button
                        variant="contained"
                        disabled={
                          !odometerValid ||
                          odometerSaving ||
                          !selectedVehicleOperational
                        }
                        onClick={() => void goToChecklist()}
                      >
                        {odometerSaving ? 'در حال ثبت کیلومتر...' : 'ادامه به چک‌لیست'}
                      </Button>
                    </Stack>
                  </Stack>
                )}

                {flowStep === 'checklist' && (
                  <Stack spacing={2}>
                    <Stack
                      direction={{ xs: 'column', sm: 'row' }}
                      justifyContent="space-between"
                      alignItems={{ xs: 'stretch', sm: 'center' }}
                      gap={1}
                    >
                      <Typography fontWeight={800}>چک‌لیست روزانه</Typography>
                      <Typography variant="body2" color="text.secondary">
                        مورد {toFaNumber(items.length ? wizardIndex + 1 : 0)} از{' '}
                        {toFaNumber(items.length)}
                        {completedCount > 0 ? ` · ${toFaNumber(completedCount)} تکمیل‌شده` : ''}
                      </Typography>
                    </Stack>

                    {vehicleSummary}

                    <LinearProgress
                      variant="determinate"
                      value={progress}
                      color="primary"
                      sx={{
                        height: 7,
                        borderRadius: (t) => t.radius('sm'),
                        bgcolor: 'primary.light',
                        '& .MuiLinearProgress-bar': {
                          borderRadius: (t) => t.radius('sm'),
                          bgcolor: 'primary.main',
                        },
                      }}
                    />

                    {!items.length && (
                      <EmptyState
                        title="آیتم چک‌لیستی یافت نشد"
                        subtitle="ابتدا قالب‌های بازرسی را از SAP همگام‌سازی کنید."
                      />
                    )}

                    {currentItem && (
                      <Box
                        sx={{
                          p: { xs: 1.75, sm: 2 },
                          border: '1px solid',
                          borderColor:
                            currentItem.errors.result ||
                            currentItem.errors.notes ||
                            currentItem.errors.defectOption
                              ? 'error.main'
                              : 'divider',
                          borderRadius: (t) => t.radius('md'),
                          bgcolor: 'background.paper',
                          boxShadow: '0 4px 14px rgba(15, 107, 76, 0.05)',
                        }}
                        >
                        <Stack
                          direction="row"
                          spacing={1}
                          justifyContent="space-between"
                          alignItems="center"
                          mb={1.25}
                          sx={{
                            px: 1.25,
                            py: 0.75,
                            borderRadius: (t) => t.radius('sm'),
                            bgcolor: 'action.disabledBackground',
                            border: '1px solid',
                            borderColor: 'divider',
                          }}
                        >
                          <Typography variant="body2" color="text.primary" fontWeight={900}>
                            {currentItem.category}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            fontWeight={900}
                            sx={{
                              direction: 'ltr',
                              px: 0.75,
                              py: 0.25,
                              borderRadius: (t) => t.radius('sm'),
                              bgcolor: 'background.paper',
                              border: '1px solid',
                              borderColor: 'divider',
                            }}
                          >
                            {currentItem.code}
                          </Typography>
                        </Stack>
                        <Typography
                          fontWeight={800}
                          fontSize={{ xs: '1.05rem', sm: '1.15rem' }}
                          mb={2}
                          textAlign="center"
                        >
                          {currentItem.description}
                        </Typography>

                        <ResultToggle
                          size="medium"
                          value={currentItem.result}
                          onChange={handleResultChange}
                        />

                        {currentItem.errors.result && (
                          <Typography
                            variant="caption"
                            color="error.main"
                            display="block"
                            mt={1}
                            textAlign="center"
                          >
                            {currentItem.errors.result}
                          </Typography>
                        )}

                        {currentItem.result === 'FAIL' && (
                          <Stack spacing={1.5} mt={2.25}>
                            <Alert severity="warning" sx={{ py: 0.5 }}>
                              برای ادامه، نوع خرابی را از فهرست انتخاب کنید.
                            </Alert>
                            <RtlAutocomplete
                              label="نوع خرابی"
                              options={defectOptions}
                              loading={defectOptionsLoading}
                              value={
                                defectOptions.find(
                                  (option) => option.id === currentItem.defectOptionId,
                                ) ?? null
                              }
                              onChange={(_, next) =>
                                updateItem(wizardIndex, {
                                  defectOptionId: next?.id ?? '',
                                  severity: next ? severityFromDefectClass(next.defect_class) : '',
                                })
                              }
                              getOptionLabel={(option) => option.code_text}
                              groupBy={(option) => option.group_text}
                              isOptionEqualToValue={(option, val) => option.id === val.id}
                              noOptionsText="موردی یافت نشد"
                              error={Boolean(currentItem.errors.defectOption)}
                              helperText={currentItem.errors.defectOption}
                            />
                            {currentItem.defectOptionId && currentItem.severity && (
                              <Stack direction="row" alignItems="center" gap={0.75}>
                                <Typography variant="caption" color="text.secondary" fontWeight={700}>
                                  شدت خرابی:
                                </Typography>
                                <Chip
                                  size="small"
                                  label={SEVERITY_LABELS[currentItem.severity]}
                                  sx={{
                                    height: 26,
                                    fontWeight: 800,
                                    fontSize: '0.8rem',
                                    bgcolor: SEVERITY_CHIP_STYLE[currentItem.severity].bg,
                                    color: SEVERITY_CHIP_STYLE[currentItem.severity].color,
                                    border: '1px solid',
                                    borderColor: SEVERITY_CHIP_STYLE[currentItem.severity].border,
                                  }}
                                />
                              </Stack>
                            )}
                            <RtlTextField
                              label="توضیح تکمیلی (اختیاری)"
                              value={currentItem.notes}
                              onChange={(event) =>
                                updateItem(wizardIndex, { notes: event.target.value })
                              }
                              multiline
                              minRows={2}
                              fullWidth
                            />
                          </Stack>
                        )}

                        <Stack
                          direction="row"
                          justifyContent="space-between"
                          alignItems="center"
                          gap={1.25}
                          mt={2.5}
                        >
                          <Button
                            variant="outlined"
                            onClick={() => {
                              if (wizardIndex === 0) setFlowStep('odometer');
                              else goPrev();
                            }}
                          >
                            قبلی
                          </Button>

                          {!isLastItem ? (
                            <Button
                              variant="contained"
                              disabled={!currentComplete}
                              onClick={handleNext}
                            >
                              مورد بعدی
                            </Button>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              {checklistComplete
                                ? 'چک‌لیست کامل شد'
                                : currentItem.result === 'FAIL'
                                  ? 'نوع خرابی را انتخاب کنید'
                                  : 'وضعیت این مورد را مشخص کنید'}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    )}

                    {submitError && isLastItem && <Alert severity="error">{submitError}</Alert>}

                    {isLastItem && (
                      <Stack direction="row" justifyContent="flex-end" pt={0.5}>
                        <Button
                          variant="contained"
                          size="large"
                          disabled={!canSubmit}
                          onClick={() => void submit()}
                        >
                          {submitting ? 'در حال ثبت...' : 'ثبت و ارسال بازرسی'}
                        </Button>
                      </Stack>
                    )}
                  </Stack>
                )}
              </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
