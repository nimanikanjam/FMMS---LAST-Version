import { useEffect, useState } from 'react';
import {
  Autocomplete,
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
import { Button } from '../../components/Button';
import { EmptyState, ErrorState } from '../../components/States';
import { FeaturePage } from '../../components/FeaturePage';
import { PageHeader } from '../../components/PageHeader';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { UserAccount, Vehicle } from '../../types/fmms';

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'مدیر سامانه',
  SUPERVISOR: 'ناظر',
  DISTRIBUTION: 'ناظر توزیع',
  TRANSPORT: 'ناظر ترابری',
  WAREHOUSE: 'ناظر انبار',
  WORKSHOP_SUPERVISOR: 'ناظر تعمیرگاه مرکزی',
  TECHNICIAN: 'تعمیرکار',
  DRIVER: 'راننده',
  VIEWER: 'مشاهده‌گر',
};

const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));

type FormState = {
  id: string | null;
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: string;
  personnel_number: string;
  is_active: boolean;
  vehicle: Vehicle | null;
};

const EMPTY_FORM: FormState = {
  id: null,
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: 'VIEWER',
  personnel_number: '',
  is_active: true,
  vehicle: null,
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  return Array.isArray(payload) ? payload : (payload.results ?? []);
}

/** Admin-only account management, including manually assigning a plate to a user. */
export function UsersPage() {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const [vehicleOptions, setVehicleOptions] = useState<Vehicle[]>([]);
  const [vehicleSearch, setVehicleSearch] = useState('');
  const [vehicleLoading, setVehicleLoading] = useState(false);

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

  useEffect(() => {
    if (!dialogOpen) return;
    let cancelled = false;
    setVehicleLoading(true);
    api
      .listVehicles('', 'license_plate', { page: 1, pageSize: 20, search: vehicleSearch || undefined })
      .then((result) => {
        if (!cancelled) setVehicleOptions(result.results);
      })
      .catch(() => {
        if (!cancelled) setVehicleOptions([]);
      })
      .finally(() => {
        if (!cancelled) setVehicleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dialogOpen, vehicleSearch]);

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setFormError('');
    setDialogOpen(true);
  };

  const openEdit = async (user: UserAccount) => {
    setFormError('');
    let vehicle: Vehicle | null = null;
    if (user.assigned_vehicle_id) {
      try {
        vehicle = await api.getVehicle(user.assigned_vehicle_id);
      } catch {
        vehicle = null;
      }
    }
    setForm({
      id: user.id,
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      password: '',
      role: user.role,
      personnel_number: user.personnel_number || '',
      is_active: user.is_active,
      vehicle,
    });
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (saving) return;
    setDialogOpen(false);
  };

  const submit = async () => {
    setFormError('');
    if (!form.username.trim() || !form.email.trim() || !form.full_name.trim()) {
      setFormError('نام کاربری، ایمیل و نام کامل الزامی است.');
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
          assigned_vehicle_id: form.vehicle?.id ?? null,
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
          assigned_vehicle_id: form.vehicle?.id ?? null,
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
    {
      key: 'actions',
      label: 'ویرایش',
      align: 'center',
      skeleton: 'button',
      render: (u) => (
        <Button size="small" variant="outlined" onClick={() => void openEdit(u)}>
          ویرایش
        </Button>
      ),
    },
  ];

  return (
    <FeaturePage>
      <PageHeader
        title="کاربران"
        description="حساب‌های کاربری سامانه و تخصیص پلاک خودرو به هر کاربر را مدیریت کنید."
        breadcrumbs={[{ label: 'مدیریت' }, { label: 'کاربران' }]}
        accentColor="secondary.main"
        actions={
          <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
            کاربر جدید
          </Button>
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
              label="کد پرسنلی SAP (اختیاری)"
              value={form.personnel_number}
              onChange={(e) => setForm((f) => ({ ...f, personnel_number: e.target.value }))}
              fullWidth
            />
            <Autocomplete
              options={vehicleOptions}
              value={form.vehicle}
              loading={vehicleLoading}
              onChange={(_, next) => setForm((f) => ({ ...f, vehicle: next }))}
              onInputChange={(_, next) => setVehicleSearch(next)}
              getOptionLabel={(option) => option.license_plate}
              isOptionEqualToValue={(option, val) => option.id === val.id}
              renderInput={(params) => (
                <RtlTextField {...params} label="پلاک تخصیص‌یافته (اختیاری)" />
              )}
              noOptionsText="خودرویی یافت نشد"
              clearOnBlur={false}
            />
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
