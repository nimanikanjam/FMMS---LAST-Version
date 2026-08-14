/**
 * FMMS's six user roles — one per operational unit plus two system-wide
 * roles. Kept in sync with `FMMSUserRole` in
 * apps/authentication/infrastructure/models.py.
 */
export type UserRole =
  | 'DRIVER'
  | 'TRANSPORT'
  | 'DISTRIBUTION'
  | 'WORKSHOP_SUPERVISOR'
  | 'ADMIN'
  | 'VIEWER';

export const ROLE_LABELS: Record<string, string> = {
  DRIVER: 'راننده',
  TRANSPORT: 'مسئول ترابری',
  DISTRIBUTION: 'مسئول توزیع',
  WORKSHOP_SUPERVISOR: 'مسئول تعمیرات',
  ADMIN: 'مدیر کل',
  VIEWER: 'ناظر کل',
};

export const ROLE_DESCRIPTIONS: Record<string, string> = {
  DRIVER: 'دسترسی به بخش راننده، به‌جز فهرست راننده‌ها.',
  TRANSPORT: 'دسترسی به تب ترابری.',
  DISTRIBUTION: 'دسترسی به تب توزیع.',
  WORKSHOP_SUPERVISOR: 'دسترسی به تب تعمیرات.',
  ADMIN: 'دسترسی کامل به تمامی بخش‌های سامانه با قابلیت ویرایش.',
  VIEWER: 'دسترسی به تمامی بخش‌های سامانه فقط به‌صورت تماشاگر (بدون امکان ویرایش).',
};

export const ROLE_OPTIONS: Array<{ value: UserRole; label: string; description: string }> = (
  Object.keys(ROLE_LABELS) as UserRole[]
).map((value) => ({
  value,
  label: ROLE_LABELS[value],
  description: ROLE_DESCRIPTIONS[value],
}));

export function roleLabel(role: string | null | undefined): string {
  if (!role) return '';
  return ROLE_LABELS[role] ?? role;
}
