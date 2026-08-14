import type { AuthUser } from '../types/fmms';
import { isNavGroup, navSections, type NavEntry, type NavGroup } from './modules';

/**
 * Module keys a DRIVER role may access: the full "راننده" nav group,
 * except the "لیست راننده‌ها" (all-drivers) list.
 */
const DRIVER_MODULE_KEYS = new Set([
  'dashboard',
  'myVehicleStatus',
  'inspections',
  'manualFault',
  'handover',
  'driverExternalWorkshop',
]);

/** Workshop (تعمیرات) unit: central workshop technical-decision inbox. */
const WORKSHOP_MODULE_KEYS = new Set(['dashboard', 'workshop']);

/** Distribution (توزیع) unit: fault disposition queue. */
const DISTRIBUTION_MODULE_KEYS = new Set(['dashboard', 'faults']);

/** Transport (ترابری) unit: repair queue, parts decisions, external workshop. */
const TRANSPORT_MODULE_KEYS = new Set([
  'dashboard',
  'repairs',
  'transportParts',
  'transportExternalWorkshop',
]);

/**
 * Role → allowed module keys.
 * `null` / missing role = unrestricted (ADMIN/VIEWER are handled directly
 * in `canAccessModule`, since they always see every section).
 */
const ROLE_MODULE_KEYS: Record<string, Set<string> | null> = {
  DRIVER: DRIVER_MODULE_KEYS,
  WORKSHOP_SUPERVISOR: WORKSHOP_MODULE_KEYS,
  DISTRIBUTION: DISTRIBUTION_MODULE_KEYS,
  TRANSPORT: TRANSPORT_MODULE_KEYS,
};

/** Map app paths to module keys for route guards. */
export const PATH_MODULE_KEYS: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/vehicles': 'vehicles',
  '/checklists': 'checklists',
  '/drivers': 'drivers',
  '/my-vehicle-status': 'myVehicleStatus',
  '/inspections': 'inspections',
  '/faults': 'faults',
  '/faults/new': 'manualFault',
  '/repairs': 'repairs',
  '/transport/parts': 'transportParts',
  '/transport/external-workshop': 'transportExternalWorkshop',
  '/driver/external-workshop': 'driverExternalWorkshop',
  '/workshop': 'workshop',
  '/handover': 'handover',
  '/sap': 'sap',
  '/components': 'components',
  '/materials': 'materials',
  '/users': 'users',
  '/settings': 'settings',
};

export function isDriverRole(user: AuthUser | null | undefined): boolean {
  return Boolean(user && user.role === 'DRIVER');
}

export function isWorkshopRole(user: AuthUser | null | undefined): boolean {
  return Boolean(user && user.role === 'WORKSHOP_SUPERVISOR');
}

export function isDistributionRole(user: AuthUser | null | undefined): boolean {
  return Boolean(user && user.role === 'DISTRIBUTION');
}

export function isTransportRole(user: AuthUser | null | undefined): boolean {
  return Boolean(user && user.role === 'TRANSPORT');
}

/** Manual SAP full sync is limited to ADMIN (and Django superuser). */
export function canRunSapFullSync(user: AuthUser | null | undefined): boolean {
  return Boolean(
    user && (user.is_superuser || user.role === 'ADMIN'),
  );
}

export function moduleKeyForPath(pathname: string): string | null {
  if (PATH_MODULE_KEYS[pathname]) return PATH_MODULE_KEYS[pathname];
  if (pathname.startsWith('/drivers/')) return 'drivers';
  if (pathname.startsWith('/faults')) return 'faults';
  return null;
}

/**
 * ADMIN (مدیر کل) and VIEWER (ناظر کل) always see every section — ADMIN
 * with full edit rights, VIEWER read-only (enforced server-side by the
 * API's role permissions, since write actions still hit the backend).
 */
export function canAccessModule(user: AuthUser | null | undefined, moduleKey: string): boolean {
  if (!user) return false;
  if (user.is_superuser || user.role === 'ADMIN' || user.role === 'VIEWER') {
    return true;
  }
  const allowed = ROLE_MODULE_KEYS[user.role];
  if (allowed == null) return true;
  return allowed.has(moduleKey);
}

export function canAccessPath(user: AuthUser | null | undefined, pathname: string): boolean {
  const moduleKey = moduleKeyForPath(pathname);
  if (!moduleKey) return true;
  return canAccessModule(user, moduleKey);
}

function filterNavEntry(user: AuthUser, entry: NavEntry): NavEntry | null {
  if (isNavGroup(entry)) {
    const children = entry.children.filter((child) => canAccessModule(user, child.key));
    if (!children.length) return null;
    return { ...entry, children } satisfies NavGroup;
  }
  return canAccessModule(user, entry.key) ? entry : null;
}

/** Filter sidebar sections by the authenticated user's role. */
export function navSectionsForUser(user: AuthUser | null | undefined) {
  if (!user) return [];
  return navSections
    .map((section) => ({
      ...section,
      entries: section.entries
        .map((entry) => filterNavEntry(user, entry))
        .filter((entry): entry is NavEntry => entry != null),
    }))
    .filter((section) => section.entries.length > 0);
}
