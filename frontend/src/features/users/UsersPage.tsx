import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import { Add, Close } from '@mui/icons-material';
import { api, ApiError } from '../../api/client';
import { useCanEdit } from '../../app/CurrentUserContext';
import { ROLE_LABELS, ROLE_OPTIONS } from '../../app/roles';
import { Button } from '../../components/Button';
import { EmptyState, ErrorState } from '../../components/States';
import { FeaturePage } from '../../components/FeaturePage';
import { PageHeader } from '../../components/PageHeader';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { UserAccount } from '../../types/fmms';

type FormState = {
  id: string | null;
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: string;
  personnel_number: string;
  is_active: boolean;
  // Only ever set automatically from the DRIVER-role SAP lookup below.
  // No other role has a UI to assign a plate.
  assignedVehicleId: string | null;
};

type DriverLookupState = 'idle' | 'loading' | 'found' | 'no_vehicle' | 'not_found';

const EMPTY_FORM: FormState = {
  id: null,
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: 'VIEWER',
  personnel_number: '',
  is_active: true,
  assignedVehicleId: null,
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  return Array.isArray(payload) ? payload : (payload.results ?? []);
}

/** Admin-only account management. DRIVER-role plates are resolved automatically from SAP. */
export function UsersPage() {
  const canEdit = useCanEdit();
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const [driverLookup, setDriverLookup] = useState<DriverLookupState>('idle');
  const [driverVehiclePlate, setDriverVehiclePlate] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listUsers({ page: 1, pageSize: 100 });
      setUsers(normalizePaginated(result));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت لیست کاربران انجام نشد');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  // DRIVER role: the assigned vehicle isn't picked manually — it's resolved
  // from the SAP driver linked by personnel number, same as the driver's own
  // "وضعیت خودروی من" page.
  useEffect(() => {
    if (!dialogOpen || form.role !== 'DRIVER') {
      setDriverLookup('idle');
      setDriverVehiclePlate(null);
      return;
    }
    const personnelNumber = form.personnel_number.trim();
    if (!personnelNumber) {
      setDriverLookup('idle');
      setDriverVehiclePlate(null);
      setForm((f) => (f.assignedVehicleId ? { ...f, assignedVehicleId: null } : f));
      return;
    }
    let cancelled = false;
    setDriverLookup('loading');
    const timer = setTimeout(() => {
      api
        .listDrivers({ search: personnelNumber, pageSize: 5 })
        .then((result) => {
          if (cancelled) return;
          const driver = result.results.find((d) => d.personnel_number === personnelNumber);
          if (!driver) {
            setDriverLookup('not_found');
            setDriverVehiclePlate(null);
            setForm((f) => ({ ...f, assignedVehicleId: null }));
            return;
          }
          const vehicle = driver.current_vehicle_as_driver ?? driver.current_vehicle_as_assistant ?? null;
          setForm((f) => ({ ...f, assignedVehicleId: vehicle?.id ?? null }));
          if (vehicle) {
            setDriverLookup('found');
            setDriverVehiclePlate(vehicle.license_plate);
          } else {
            setDriverLookup('no_vehicle');
            setDriverVehiclePlate(null);
          }
        })
        .catch(() => {
          if (cancelled) return;
          setDriverLookup('not_found');
          setDriverVehiclePlate(null);
          setForm((f) => ({ ...f, assignedVehicleId: null }));
        });
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [dialogOpen, form.role, form.personnel_number]);

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setFormError('');
    setDialogOpen(true);
  };

  const openEdit = (user: UserAccount) => {
    setFormError('');
    setForm({
      id: user.id,
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      password: '',
      role: user.role,
      personnel_number: user.personnel_number || '',
      is_active: user.is_active,
      // Non-DRIVER roles have no plate UI, so this is only ever touched by
      // the DRIVER SAP lookup effect below — preserved as-is otherwise.
      assignedVehicleId: user.assigned_vehicle_id,
    });
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (saving) return;
    setDialogOpen(false);
  };

  const submit = async () => {
    setFormError('');
    if (
      !form.username.trim() ||
      !form.email.trim() ||
      !form.full_name.trim() ||
      !form.personnel_number.trim()
    ) {
      setFormError('نام کاربری، ایمیل، نام کامل و کد پرسنلی الزامی است.');
      return;
    }
    if (!form.id && !form.password.trim()) {
      setFormError('برای ایجاد کاربر جدید، رمز عبور الزامی است.');
      return;
    }
    setSaving(true);
    try {
      if (form.id) {
        await api.updateUser(form.id, {
          email: form.email.trim(),
          full_name: form.full_name.trim(),
          role: form.role,
          personnel_number: form.personnel_number.trim(),
          assigned_vehicle_id: form.assignedVehicleId,
          is_active: form.is_active,
          ...(form.password.trim() ? { password: form.password.trim() } : {}),
        });
      } else {
        await api.createUser({
          username: form.username.trim(),
          email: form.email.trim(),
          full_name: form.full_name.trim(),
          password: form.password.trim(),
          role: form.role,
          personnel_number: form.personnel_number.trim(),
          assigned_vehicle_id: form.assignedVehicleId,
        });
      }
      setDialogOpen(false);
      await load();
    } catch (err) {
      if (err instanceof ApiError) {
        const details = err.details as Record<string, string[]> | undefined;
        const firstMessage = details ? Object.values(details).flat()[0] : undefined;
        setFormError(firstMessage || err.message);
      } else {
        setFormError(err instanceof Error ? err.message : 'ثبت اطلاعات کاربر انجام نشد');
      }
    } finally {
      setSaving(false);
    }
  };

  const columns: Array<RtlDataTableColumn<UserAccount, keyof UserAccount | 'actions'>> = [
    { key: 'full_name', label: 'نام کامل', skeleton: 'text', render: (u) => u.full_name },
    { key: 'username', label: 'نام کاربری', skeleton: 'text', render: (u) => u.username },
    {
      key: 'role',
      label: 'نقش',
      skeleton: 'badge',
      render: (u) => <PlainStatusBadge label={ROLE_LABELS[u.role] ?? u.role} tone="neutral" />,
    },
    {
      key: 'assigned_vehicle_plate',
      label: 'پلاک تخصیص‌یافته',
      skeleton: 'text',
      render: (u) => u.assigned_vehicle_plate || '—',
    },
    {
      key: 'is_active',
      label: 'وضعیت',
      skeleton: 'badge',
      render: (u) => (
        <PlainStatusBadge
          label={u.is_active ? 'فعال' : 'غیرفعال'}
          tone={u.is_active ? 'success' : 'error'}
        />
      ),
    },
    ...(canEdit
      ? [
          {
            key: 'actions' as const,
            label: 'ویرایش',
            align: 'center' as const,
            skeleton: 'button' as const,
            render: (u: UserAccount) => (
              <Button size="small" variant="outlined" onClick={() => void openEdit(u)}>
                ویرایش
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <FeaturePage>
      <PageHeader
        title="کاربران"
        description="حساب‌های کاربری سامانه را مدیریت کنید."
        breadcrumbs={[{ label: 'مدیریت' }, { label: 'کاربران' }]}
        accentColor="secondary.main"
        actions={
          canEdit ? (
            <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
              کاربر جدید
            </Button>
          ) : undefined
        }
      />

      {error && <ErrorState message={error} onRetry={() => void load()} />}

      {!error && (loading || users.length > 0) && (
        <RtlDataTable
          columns={columns}
          rows={users}
          getRowKey={(u) => u.id}
          loading={loading}
          skeletonRows={6}
          minWidth={760}
          emptyMessage="کاربری ثبت نشده است"
        />
      )}

      {!loading && !error && users.length === 0 && (
        <EmptyState title="کاربری ثبت نشده است" subtitle="با دکمه «کاربر جدید» اولین حساب را بسازید." />
      )}

      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {form.id ? 'ویرایش کاربر' : 'کاربر جدید'}
          <IconButton onClick={closeDialog} size="small">
            <Close fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} mt={0.5}>
            {formError && <Typography color="error.main" variant="body2">{formError}</Typography>}

            <RtlTextField
              label="نام کاربری"
              value={form.username}
              disabled={Boolean(form.id)}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              fullWidth
              required
            />
            <RtlTextField
              label="نام کامل"
              value={form.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              fullWidth
              required
            />
            <RtlTextField
              label="ایمیل"
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              fullWidth
              required
            />
            <RtlTextField
              label={form.id ? 'رمز عبور جدید (اختیاری)' : 'رمز عبور'}
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              fullWidth
              required={!form.id}
            />
            <RtlSelectField
              label="نقش"
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as string }))}
            >
              {ROLE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </RtlSelectField>
            <RtlTextField
              label="کد پرسنلی SAP"
              value={form.personnel_number}
              onChange={(e) => setForm((f) => ({ ...f, personnel_number: e.target.value }))}
              fullWidth
              required
            />
            {form.role === 'DRIVER' && (
              <>
                <RtlTextField
                  label="پلاک تخصیص‌یافته"
                  value={
                    driverLookup === 'loading'
                      ? 'در حال یافتن خودرو...'
                      : driverVehiclePlate || ''
                  }
                  placeholder="با تکمیل کد پرسنلی، به‌صورت خودکار پر می‌شود"
                  disabled
                  fullWidth
                />
                {driverLookup === 'not_found' && (
                  <Typography variant="caption" color="warning.main">
                    راننده‌ای با این کد پرسنلی در SAP یافت نشد.
                  </Typography>
                )}
                {driverLookup === 'no_vehicle' && (
                  <Typography variant="caption" color="warning.main">
                    این راننده در حال حاضر خودرویی در SAP ندارد.
                  </Typography>
                )}
              </>
            )}
            {form.id && (
              <RtlSelectField
                label="وضعیت حساب"
                value={form.is_active ? 'active' : 'inactive'}
                onChange={(e) =>
                  setForm((f) => ({ ...f, is_active: e.target.value === 'active' }))
                }
              >
                <MenuItem value="active">فعال</MenuItem>
                <MenuItem value="inactive">غیرفعال</MenuItem>
              </RtlSelectField>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, pt: 1 }}>
          <Button variant="outlined" color="inherit" onClick={closeDialog} disabled={saving}>
            انصراف
          </Button>
          <Button variant="contained" loading={saving} onClick={() => void submit()}>
            {form.id ? 'ذخیره تغییرات' : 'ایجاد کاربر'}
          </Button>
        </DialogActions>
      </Dialog>
    </FeaturePage>
  );
}
