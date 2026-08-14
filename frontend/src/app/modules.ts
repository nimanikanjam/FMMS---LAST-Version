import type { SvgIconComponent } from '@mui/icons-material';
import {
  Build,
  CarRepair,
  Dashboard,
  DirectionsCar,
  FactCheck,
  Handshake,
  Inventory2,
  LocalShipping,
  PeopleAlt,
  ReportProblem,
  Settings,
  Sync,
  Widgets,
} from '../components/icons3d/Icons3D';

export interface AppModule {
  key: string;
  label: string;
  path: string;
  icon: SvgIconComponent;
  enabled: boolean;
}

export interface NavGroup {
  key: string;
  label: string;
  icon: SvgIconComponent;
  children: AppModule[];
}

export type NavEntry = AppModule | NavGroup;

export function isNavGroup(entry: NavEntry): entry is NavGroup {
  return 'children' in entry;
}

export const modules: AppModule[] = [
  { key: 'dashboard', label: 'داشبورد', path: '/dashboard', icon: Dashboard, enabled: true },
  { key: 'vehicles', label: 'لیست خودروها', path: '/vehicles', icon: DirectionsCar, enabled: true },
  { key: 'checklists', label: 'لیست بازرسی روزانه', path: '/checklists', icon: FactCheck, enabled: true },
  { key: 'components', label: 'کامپوننت‌ها', path: '/components', icon: Widgets, enabled: true },
  { key: 'drivers', label: 'لیست راننده‌ها', path: '/drivers', icon: PeopleAlt, enabled: true },
  { key: 'myVehicleStatus', label: 'وضعیت خودروی من', path: '/my-vehicle-status', icon: CarRepair, enabled: true },
  { key: 'inspections', label: 'بازرسی روزانه', path: '/inspections', icon: ReportProblem, enabled: true },
  { key: 'manualFault', label: 'ثبت خرابی موردی', path: '/faults/new', icon: ReportProblem, enabled: true },
  { key: 'faults', label: 'کارتابل توزیع', path: '/faults', icon: CarRepair, enabled: true },
  { key: 'handover', label: 'تحویل و تایید', path: '/handover', icon: Handshake, enabled: true },
  { key: 'driverExternalWorkshop', label: 'تحویل تعمیرگاه بیرونی', path: '/driver/external-workshop', icon: LocalShipping, enabled: true },
  { key: 'transportExternalWorkshop', label: 'ثبت فاکتور تعمیرگاه بیرونی', path: '/transport/external-workshop', icon: LocalShipping, enabled: true },
  { key: 'repairs', label: 'کارتابل ترابری', path: '/repairs', icon: Build, enabled: true },
  { key: 'transportParts', label: 'درخواست قطعات', path: '/transport/parts', icon: Inventory2, enabled: true },
  { key: 'workshop', label: 'تعمیرگاه مرکزی', path: '/workshop', icon: Build, enabled: true },
  { key: 'materials', label: 'قطعات و انبار', path: '/materials', icon: Inventory2, enabled: true },
  { key: 'sap', label: 'یکپارچه‌سازی SAP', path: '/sap', icon: Sync, enabled: true },
  { key: 'users', label: 'کاربران', path: '/users', icon: PeopleAlt, enabled: true },
  { key: 'settings', label: 'تنظیمات', path: '/settings', icon: Settings, enabled: false },
];

const byKey = (key: string): AppModule => {
  const mod = modules.find((item) => item.key === key);
  if (!mod) throw new Error(`Unknown module: ${key}`);
  return mod;
};

/** Sidebar / drawer navigation tree (supports nested groups). */
export const navSections: Array<{ label: string; entries: NavEntry[] }> = [
  {
    label: 'اصلی',
    entries: [
      byKey('dashboard'),
      {
        key: 'vehicle',
        label: 'خودرو',
        icon: DirectionsCar,
        children: [byKey('vehicles'), byKey('checklists')],
      },
      {
        key: 'distribution',
        label: 'توزیع خودرو',
        icon: LocalShipping,
        children: [byKey('faults')],
      },
      {
        key: 'transport',
        label: 'ترابری',
        icon: Build,
        children: [byKey('repairs'), byKey('transportParts'), byKey('transportExternalWorkshop')],
      },
      {
        key: 'workshopGroup',
        label: 'تعمیرات',
        icon: Build,
        children: [byKey('workshop')],
      },
      {
        key: 'driver',
        label: 'راننده',
        icon: PeopleAlt,
        children: [
          byKey('drivers'),
          byKey('myVehicleStatus'),
          byKey('inspections'),
          byKey('manualFault'),
          byKey('handover'),
          byKey('driverExternalWorkshop'),
        ],
      },
    ],
  },
  {
    label: 'مدیریت',
    entries: [
      byKey('components'),
      byKey('materials'),
      byKey('sap'),
      byKey('users'),
      byKey('settings'),
    ],
  },
];
