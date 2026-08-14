import type { AuthUser } from '../types/fmms';
import { isNavGroup, navSections, type NavEntry, type NavGroup } from './modules';

/** Module keys a DRIVER role may access in the shell navigation. */
const DRIVER_MODULE_KEYS = new Set([
  'dashboard',
  'myVehicleStatus',
  'inspections',
  'handover',
  'driverExternalWorkshop',
]);

/** Central workshop supervisor / technician inbox. */
const WORKSHOP_MODULE_KEYS = new Set(['dashboard', 'workshop']);

/** Distribution unit: fault disposition queue. */
const DISTRIBUTION_MODULE_KEYS = new Set([
  'dashboard',
  'faults',
  'vehicles',
  'checklists',
]);

/** Transport unit: repair queue + parts decisions. */
const TRANSPORT_MODULE_KEYS = new Set([
  'dashboard',
  'repairs',
  'transportParts',
  'transportExternalWorkshop',
  'vehicles',
  'drivers',
]);

/**
 * Role → allowed module keys.
 * `null` / missing role = unrestricted (legacy/open until mapped).
 */
const ROLE_MODULE_KEYS: Record<string, Set<string> | null> = {
  DRIVER: DRIVER_MODULE_KEYS,
  WORKSHOP_SUPERVISOR: WORKSHOP_MODULE_KEYS,
  TECHNICIAN: WORKSHOP_MODULE_KEYS,
  DISTRIBUTION: DISTRIBUTION_MODULE_KEYS,
  TRANSPORT: TRANSPORT_MODULE_KEYS,
  WAREHOUSE: new Set(['dashboard', 'transportParts', 'materials']),
  VIEWER: new Set(['dashboard', 'vehicles', 'checklists', 'drivers', 'faults', 'sap']),
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
  return Boolean(
    user && (user.role === 'WORKSHOP_SUPERVISOR' || user.role === 'TECHNICIAN'),
  );
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

export function canAccessModule(user: AuthUser | null | undefined, moduleKey: string): boolean {
  if (!user) return false;
  if (user.is_superuser || user.role === 'ADMIN' || user.role === 'SUPERVISOR') {
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
