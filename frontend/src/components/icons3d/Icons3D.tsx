/**
 * Custom 3D-style domain icons for FMMS.
 * Layered fills + soft highlights give depth without external icon packs.
 */
import { SvgIcon, type SvgIconProps } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';
import type { ReactNode } from 'react';

type IconProps = SvgIconProps;

let gradSeq = 0;
function uid(prefix: string) {
  gradSeq += 1;
  return `${prefix}-${gradSeq}`;
}

/** Shared wrapper so icons inherit MUI color / fontSize. */
function Base({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <SvgIcon viewBox="0 0 24 24" {...props}>
      {children}
    </SvgIcon>
  );
}

export function Dashboard3D(props: IconProps) {
  const id = uid('dash');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-a`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.55" />
        </linearGradient>
        <linearGradient id={`${id}-b`} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.35" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.9" />
        </linearGradient>
      </defs>
      {/* back plate */}
      <rect x="2.5" y="2.5" width="8.5" height="8.5" rx="1.8" fill={`url(#${id}-a)`} opacity="0.95" />
      <rect x="13" y="2.5" width="8.5" height="5.5" rx="1.6" fill={`url(#${id}-b)`} />
      <rect x="13" y="10" width="8.5" height="11.5" rx="1.8" fill={`url(#${id}-a)`} opacity="0.75" />
      <rect x="2.5" y="13" width="8.5" height="8.5" rx="1.8" fill={`url(#${id}-b)`} opacity="0.85" />
      {/* highlight dots */}
      <circle cx="5.2" cy="5.2" r="1.1" fill="#fff" opacity="0.35" />
      <circle cx="15.5" cy="4.5" r="0.9" fill="#fff" opacity="0.3" />
    </Base>
  );
}

export function Car3D(props: IconProps) {
  const id = uid('car');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-body`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.55" />
        </linearGradient>
        <linearGradient id={`${id}-win`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#fff" stopOpacity="0.12" />
        </linearGradient>
      </defs>
      {/* shadow under body */}
      <ellipse cx="12" cy="20.2" rx="8" ry="1.2" fill="currentColor" opacity="0.18" />
      {/* body */}
      <path
        d="M4.2 14.2h15.6c.9 0 1.5.7 1.5 1.5v2.2c0 .5-.4.9-.9.9h-1.1c-.2-1.1-1.2-2-2.4-2s-2.2.9-2.4 2H9.5c-.2-1.1-1.2-2-2.4-2s-2.2.9-2.4 2H3.6c-.5 0-.9-.4-.9-.9v-2.2c0-.8.6-1.5 1.5-1.5z"
        fill={`url(#${id}-body)`}
      />
      {/* cabin */}
      <path
        d="M6.2 14.2 7.6 9.8c.3-.9 1.1-1.5 2-1.5h4.8c.9 0 1.7.6 2 1.5l1.4 4.4H6.2z"
        fill={`url(#${id}-body)`}
        opacity="0.92"
      />
      {/* windows */}
      <path d="M8.1 10.2h3.1v2.6H7.4l.7-2.6z" fill={`url(#${id}-win)`} />
      <path d="M12.8 10.2h3.1l.7 2.6h-3.8v-2.6z" fill={`url(#${id}-win)`} />
      {/* wheels */}
      <circle cx="7.1" cy="18.6" r="2.05" fill="currentColor" opacity="0.95" />
      <circle cx="7.1" cy="18.6" r="0.85" fill="#fff" opacity="0.35" />
      <circle cx="16.9" cy="18.6" r="2.05" fill="currentColor" opacity="0.95" />
      <circle cx="16.9" cy="18.6" r="0.85" fill="#fff" opacity="0.35" />
      {/* headlight */}
      <rect x="18.8" y="15.1" width="1.6" height="1.2" rx="0.4" fill="#fff" opacity="0.45" />
    </Base>
  );
}

export function Checklist3D(props: IconProps) {
  const id = uid('chk');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-p`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      <rect x="4" y="2.5" width="13.5" height="19" rx="2.2" fill={`url(#${id}-p)`} opacity="0.9" />
      <rect x="5.5" y="4" width="10.5" height="16" rx="1.4" fill="#fff" opacity="0.18" />
      {/* lines */}
      <rect x="8.5" y="7" width="6" height="1.4" rx="0.5" fill="#fff" opacity="0.75" />
      <rect x="8.5" y="11" width="6" height="1.4" rx="0.5" fill="#fff" opacity="0.55" />
      <rect x="8.5" y="15" width="4.5" height="1.4" rx="0.5" fill="#fff" opacity="0.4" />
      {/* checks */}
      <path d="M6.2 7.2 6.9 8l1.4-1.8" stroke="#fff" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.95" />
      <path d="M6.2 11.2 6.9 12l1.4-1.8" stroke="#fff" strokeWidth="1.3" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
      <circle cx="7" cy="15.7" r="0.85" fill="#fff" opacity="0.45" />
    </Base>
  );
}

export function People3D(props: IconProps) {
  const id = uid('ppl');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-f`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      {/* back person */}
      <circle cx="16.2" cy="7.2" r="2.6" fill="currentColor" opacity="0.45" />
      <path d="M12.4 19.5c.4-3.2 2-5 3.8-5s3.4 1.8 3.8 5" fill="currentColor" opacity="0.4" />
      {/* front person */}
      <circle cx="9.2" cy="7.4" r="3.1" fill={`url(#${id}-f)`} />
      <circle cx="8.2" cy="6.4" r="1" fill="#fff" opacity="0.28" />
      <path
        d="M3.2 20.2c.5-4.1 2.8-6.4 6-6.4s5.5 2.3 6 6.4"
        fill={`url(#${id}-f)`}
      />
      <ellipse cx="9.2" cy="15.2" rx="2.2" ry="0.7" fill="#fff" opacity="0.18" />
    </Base>
  );
}

export function Wrench3D(props: IconProps) {
  const id = uid('wr');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-m`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.45" />
        </linearGradient>
      </defs>
      {/* wrench body */}
      <path
        d="M14.8 3.2c-1.6 0-3 .8-3.8 2.1l-6.6 6.6c-.4.4-.4 1 0 1.4l1.1 1.1 1.8-1.8 1.3 1.3-1.8 1.8 1.1 1.1c.4.4 1 .4 1.4 0l6.6-6.6c1.3-.8 2.1-2.2 2.1-3.8 0-.4-.3-.7-.7-.7-.3 0-.5.1-.7.3l-1.5 1.5-1.6-1.6 1.5-1.5c.2-.2.3-.4.3-.7 0-.4-.3-.7-.7-.7z"
        fill={`url(#${id}-m)`}
      />
      {/* highlight along shaft */}
      <path
        d="M9.2 12.8 15 7"
        stroke="#fff"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.35"
      />
      {/* gear accent */}
      <circle cx="7.2" cy="16.8" r="3.2" fill="currentColor" opacity="0.55" />
      <circle cx="7.2" cy="16.8" r="1.4" fill="#fff" opacity="0.25" />
      <circle cx="7.2" cy="16.8" r="0.6" fill="currentColor" opacity="0.9" />
    </Base>
  );
}

export function Truck3D(props: IconProps) {
  const id = uid('trk');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-b`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      <ellipse cx="12" cy="20.4" rx="9" ry="1.1" fill="currentColor" opacity="0.15" />
      {/* cargo box */}
      <rect x="2.2" y="6.5" width="11.2" height="9.2" rx="1.4" fill={`url(#${id}-b)`} />
      <rect x="3.2" y="7.5" width="9.2" height="3.2" rx="0.8" fill="#fff" opacity="0.2" />
      {/* cabin */}
      <path
        d="M13.8 10.5h4.2c.7 0 1.3.4 1.6 1l1.2 2.6c.1.3.2.6.2.9v1.7c0 .6-.5 1.1-1.1 1.1h-6.1V10.5z"
        fill={`url(#${id}-b)`}
        opacity="0.92"
      />
      <path d="M15.2 11.4h2.6l1 2.2h-3.6v-2.2z" fill="#fff" opacity="0.35" />
      {/* wheels */}
      <circle cx="6.2" cy="17.6" r="2.15" fill="currentColor" />
      <circle cx="6.2" cy="17.6" r="0.9" fill="#fff" opacity="0.35" />
      <circle cx="16.6" cy="17.6" r="2.15" fill="currentColor" />
      <circle cx="16.6" cy="17.6" r="0.9" fill="#fff" opacity="0.35" />
    </Base>
  );
}

export function Box3D(props: IconProps) {
  const id = uid('box');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-top`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.65" />
        </linearGradient>
        <linearGradient id={`${id}-side`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.85" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.4" />
        </linearGradient>
      </defs>
      {/* isometric box */}
      <path d="M12 3.2 20.2 7.5 12 11.8 3.8 7.5Z" fill={`url(#${id}-top)`} />
      <path d="M3.8 7.5 12 11.8v9L3.8 16.5Z" fill={`url(#${id}-side)`} opacity="0.9" />
      <path d="M12 11.8 20.2 7.5v9L12 20.8Z" fill="currentColor" opacity="0.55" />
      {/* tape / highlight */}
      <path d="M12 3.2v8.6" stroke="#fff" strokeWidth="1.1" opacity="0.35" />
      <path d="M8 5.4 16 9.4" stroke="#fff" strokeWidth="0.9" opacity="0.25" />
    </Base>
  );
}

export function Handshake3D(props: IconProps) {
  const id = uid('hs');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-h`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      {/* left sleeve */}
      <path d="M2.5 9.5c1.5-2 4-3 6.2-2.2l2.5 1.1-1.8 4.2-3.2-1.4c-1.8-.8-3-2.8-3.7-1.7z" fill={`url(#${id}-h)`} opacity="0.75" />
      {/* right sleeve */}
      <path d="M21.5 9.5c-1.5-2-4-3-6.2-2.2l-2.5 1.1 1.8 4.2 3.2-1.4c1.8-.8 3-2.8 3.7-1.7z" fill={`url(#${id}-h)`} opacity="0.75" />
      {/* clasped hands */}
      <path
        d="M8.2 10.2c1.2-.6 2.6-.4 3.8.4 1.2-.9 2.8-1.1 4.1-.3.8.5 1.2 1.4 1.1 2.3-.2 1.4-1.4 2.4-2.8 2.6l-1.6.2c-1.6.2-3.1-.6-3.9-1.9-.6-1-.6-2.2.1-3.1.3-.4.6-.7.9-.9.1 0 .2 0 .3 0.3.2.6.5.8.9.4.7.4 1.6 0 2.2-.2.3-.6.4-.9.2z"
        fill={`url(#${id}-h)`}
      />
      <path d="M10.5 12.2c.6.4 1.4.5 2.1.3" stroke="#fff" strokeWidth="1" strokeLinecap="round" opacity="0.35" />
      {/* base shadow */}
      <ellipse cx="12" cy="19.8" rx="6" ry="1" fill="currentColor" opacity="0.15" />
    </Base>
  );
}

export function Alert3D(props: IconProps) {
  const id = uid('al');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-t`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      <path
        d="M12 2.8 21.2 19.2c.4.7-.1 1.6-.9 1.6H3.7c-.8 0-1.3-.9-.9-1.6L12 2.8z"
        fill={`url(#${id}-t)`}
      />
      <path d="M12 4.6 19.4 18.4H4.6L12 4.6z" fill="#fff" opacity="0.12" />
      <rect x="11.1" y="9" width="1.8" height="5.2" rx="0.9" fill="#fff" opacity="0.95" />
      <circle cx="12" cy="16.6" r="1.05" fill="#fff" opacity="0.95" />
    </Base>
  );
}

export function Sync3D(props: IconProps) {
  const id = uid('sy');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-r`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.45" />
        </linearGradient>
      </defs>
      <circle cx="12" cy="12" r="9" fill="currentColor" opacity="0.12" />
      <path
        d="M18.6 12a6.6 6.6 0 0 0-11-4.9l-.8-.8v3.4h3.4l-1.1-1.1A4.8 4.8 0 0 1 16.8 12"
        fill={`url(#${id}-r)`}
      />
      <path
        d="M5.4 12a6.6 6.6 0 0 0 11 4.9l.8.8v-3.4h-3.4l1.1 1.1A4.8 4.8 0 0 1 7.2 12"
        fill={`url(#${id}-r)`}
        opacity="0.75"
      />
      <circle cx="12" cy="12" r="2" fill="#fff" opacity="0.25" />
    </Base>
  );
}

export function Settings3D(props: IconProps) {
  const id = uid('st');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-g`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      <path
        d="M19.4 12.9v-1.8l2-1.2-1.2-2.8-2.3.6a6.7 6.7 0 0 0-1.5-.9L15.9 4h-2.8l-.5 2.4c-.5.2-1 .5-1.5.9l-2.3-.6-1.2 2.8 2 1.2v1.8l-2 1.2 1.2 2.8 2.3-.6c.5.4 1 .7 1.5.9l.5 2.4h2.8l.5-2.4c.5-.2 1-.5 1.5-.9l2.3.6 1.2-2.8-2-1.2z"
        fill={`url(#${id}-g)`}
        opacity="0.9"
      />
      <circle cx="14.5" cy="12" r="3.2" fill="currentColor" opacity="0.35" />
      <circle cx="14.5" cy="12" r="1.7" fill="#fff" opacity="0.35" />
      <circle cx="9.5" cy="12" r="2.4" fill={`url(#${id}-g)`} />
      <circle cx="9.5" cy="12" r="1.1" fill="#fff" opacity="0.3" />
    </Base>
  );
}

export function Widgets3D(props: IconProps) {
  const id = uid('wd');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-c`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      <rect x="2.5" y="2.5" width="8" height="8" rx="2" fill={`url(#${id}-c)`} />
      <rect x="13.5" y="2.5" width="8" height="8" rx="2" fill={`url(#${id}-c)`} opacity="0.7" />
      <rect x="2.5" y="13.5" width="8" height="8" rx="2" fill={`url(#${id}-c)`} opacity="0.7" />
      <rect x="13.5" y="13.5" width="8" height="8" rx="2" fill={`url(#${id}-c)`} opacity="0.45" />
      <circle cx="6.5" cy="6.5" r="1.3" fill="#fff" opacity="0.35" />
    </Base>
  );
}

export function CarRepair3D(props: IconProps) {
  const id = uid('cr');
  return (
    <Base {...props}>
      <defs>
        <linearGradient id={`${id}-b`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="1" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0.5" />
        </linearGradient>
      </defs>
      {/* car silhouette small */}
      <path
        d="M3.5 13.5h10.5c.6 0 1 .5 1 1v1.4c0 .3-.2.6-.5.6H13c-.15-.8-.9-1.4-1.8-1.4s-1.65.6-1.8 1.4H7.6c-.15-.8-.9-1.4-1.8-1.4S4.15 15.7 4 16.5H3c-.3 0-.5-.3-.5-.6V14.5c0-.5.4-1 1-1z"
        fill={`url(#${id}-b)`}
      />
      <path d="M5.2 13.5 6.2 10.6c.2-.6.7-1 1.3-1h3.2c.6 0 1.1.4 1.3 1l1 2.9H5.2z" fill={`url(#${id}-b)`} opacity="0.9" />
      <circle cx="5.8" cy="16.5" r="1.35" fill="currentColor" />
      <circle cx="11.2" cy="16.5" r="1.35" fill="currentColor" />
      {/* floating wrench */}
      <path
        d="M16.2 4.2c-1.1 0-2 .6-2.5 1.5l-3.8 3.8.9.9 1.1-1.1.9.9-1.1 1.1.9.9c.3.3.7.3 1 0l3.8-3.8c.9-.5 1.5-1.4 1.5-2.5 0-.3-.2-.5-.5-.5-.2 0-.3.1-.4.2l-.9.9-1.1-1.1.9-.9c.1-.1.2-.2.2-.4 0-.3-.2-.5-.5-.5z"
        fill={`url(#${id}-b)`}
      />
      <path d="M12.4 10.2 16.8 5.8" stroke="#fff" strokeWidth="1" strokeLinecap="round" opacity="0.3" />
    </Base>
  );
}

/** Map module keys → 3D icons (SvgIconComponent-compatible). */
export const icons3d = {
  dashboard: Dashboard3D as unknown as SvgIconComponent,
  vehicles: Car3D as unknown as SvgIconComponent,
  checklists: Checklist3D as unknown as SvgIconComponent,
  components: Widgets3D as unknown as SvgIconComponent,
  drivers: People3D as unknown as SvgIconComponent,
  inspections: Alert3D as unknown as SvgIconComponent,
  manualFault: Alert3D as unknown as SvgIconComponent,
  faults: CarRepair3D as unknown as SvgIconComponent,
  handover: Handshake3D as unknown as SvgIconComponent,
  driverExternalWorkshop: Truck3D as unknown as SvgIconComponent,
  transportExternalWorkshop: Truck3D as unknown as SvgIconComponent,
  repairs: Wrench3D as unknown as SvgIconComponent,
  transportParts: Box3D as unknown as SvgIconComponent,
  workshop: Wrench3D as unknown as SvgIconComponent,
  materials: Box3D as unknown as SvgIconComponent,
  sap: Sync3D as unknown as SvgIconComponent,
  settings: Settings3D as unknown as SvgIconComponent,
} as const;

// Public aliases mirror MUI icon exports so existing shared component contracts
// accept the custom icons without weakening their types across the application.
export const Dashboard = Dashboard3D as unknown as SvgIconComponent;
export const DirectionsCar = Car3D as unknown as SvgIconComponent;
export const FactCheck = Checklist3D as unknown as SvgIconComponent;
export const Widgets = Widgets3D as unknown as SvgIconComponent;
export const PeopleAlt = People3D as unknown as SvgIconComponent;
export const ReportProblem = Alert3D as unknown as SvgIconComponent;
export const CarRepair = CarRepair3D as unknown as SvgIconComponent;
export const Handshake = Handshake3D as unknown as SvgIconComponent;
export const LocalShipping = Truck3D as unknown as SvgIconComponent;
export const Build = Wrench3D as unknown as SvgIconComponent;
export const Inventory2 = Box3D as unknown as SvgIconComponent;
export const Sync = Sync3D as unknown as SvgIconComponent;
export const Settings = Settings3D as unknown as SvgIconComponent;
