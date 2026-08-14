/**
 * Standalone "my vehicle status" flowchart tab.
 *
 * Self-contained by design: everything this tab needs (step model, visuals,
 * data fetch) lives in this one file. To remove the feature, delete this
 * file and drop its single import + tab entry from VehiclePage.tsx.
 */
import { useEffect, useState } from 'react';
import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import {
  CheckCircle,
  ErrorOutline,
  HourglassEmpty,
  RadioButtonUnchecked,
  TaskAlt,
} from '@mui/icons-material';
import { api } from '../../api/client';
import { EmptyState, LoadingState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import type { RepairOrder } from '../../types/fmms';
import { formatDateTime } from '../../utils/format';

const ACTIVE_REPAIR_STATUSES = new Set([
  'CREATED',
  'APPROVED',
  'WORKSHOP_ASSIGNED',
  'WAITING_EXTERNAL_REFERRAL_APPROVAL',
  'WAITING_EXTERNAL_DELIVERY',
  'EXTERNAL_REPAIR_IN_PROGRESS',
  'WAITING_EXTERNAL_PICKUP',
  'WAITING_EXTERNAL_ADMIN_REVIEW',
  'WAITING_WORKSHOP_CONFIRMATION',
  'WAITING_PARTS',
  'ASSIGNED',
  'IN_PROGRESS',
  'WAITING_DRIVER_CONFIRMATION',
  'WAITING_TRANSPORT_FINAL_APPROVAL',
  'ACCEPTED_BY_DRIVER',
]);

const STOPPED_STATUS_MESSAGES: Record<string, string> = {
  REJECTED_BY_TRANSPORT: 'درخواست تعمیر توسط واحد ترابری رد شد.',
  REJECTED_BY_DRIVER: 'راننده تحویل خودرو را رد کرد.',
  CANCELLED: 'این دستور تعمیر لغو شد.',
  NO_REPAIR_NEEDED: 'بررسی فنی نشان داد نیازی به تعمیر نبود؛ خودرو تحویل داده شد.',
};

const REPAIR_STATUS_LABELS: Record<string, string> = {
  CREATED: 'ثبت‌شده',
  APPROVED: 'تأییدشده توسط ترابری',
  WORKSHOP_ASSIGNED: 'ارجاع به تعمیرگاه مرکزی',
  WAITING_WORKSHOP_CONFIRMATION: 'در انتظار تصمیم فنی',
  WAITING_EXTERNAL_REFERRAL_APPROVAL: 'در انتظار مجوز ارجاع بیرونی',
  WAITING_EXTERNAL_DELIVERY: 'در انتظار تحویل به تعمیرگاه بیرونی',
  EXTERNAL_REPAIR_IN_PROGRESS: 'در حال تعمیر (بیرونی)',
  WAITING_EXTERNAL_PICKUP: 'آماده بازگشت از تعمیرگاه بیرونی',
  WAITING_EXTERNAL_ADMIN_REVIEW: 'در حال بررسی اداری',
  WAITING_PARTS: 'در انتظار قطعه',
  ASSIGNED: 'در حال تعمیر',
  IN_PROGRESS: 'در حال تعمیر',
  WAITING_DRIVER_CONFIRMATION: 'در انتظار تایید راننده',
  WAITING_TRANSPORT_FINAL_APPROVAL: 'در انتظار تایید نهایی ترابری',
  ACCEPTED_BY_DRIVER: 'تایید شده توسط راننده',
  REJECTED_BY_DRIVER: 'رد شده توسط راننده',
  REJECTED_BY_TRANSPORT: 'رد شده توسط ترابری',
  NO_REPAIR_NEEDED: 'عدم نیاز به تعمیر',
  COMPLETED: 'تکمیل‌شده',
  CANCELLED: 'لغوشده',
};

type FlowStep = {
  key: string;
  label: string;
  statuses: string[];
};

const PREFIX_STEPS: FlowStep[] = [
  { key: 'created', label: 'ثبت گزارش خرابی و ایجاد دستور تعمیر', statuses: ['CREATED'] },
  { key: 'approved', label: 'تأیید واحد ترابری', statuses: ['APPROVED'] },
];

const INTERNAL_STEPS: FlowStep[] = [
  {
    key: 'workshop',
    label: 'ارسال به تعمیرگاه مرکزی',
    statuses: ['WORKSHOP_ASSIGNED', 'WAITING_WORKSHOP_CONFIRMATION'],
  },
  {
    key: 'in_progress',
    label: 'در حال تعمیر',
    statuses: ['ASSIGNED', 'IN_PROGRESS', 'WAITING_PARTS'],
  },
  {
    key: 'handover',
    label: 'تحویل خودرو به راننده',
    statuses: ['WAITING_DRIVER_CONFIRMATION'],
  },
  {
    key: 'final_approval',
    label: 'تأیید نهایی ترابری',
    statuses: ['WAITING_TRANSPORT_FINAL_APPROVAL', 'ACCEPTED_BY_DRIVER'],
  },
  { key: 'completed', label: 'تکمیل تعمیر', statuses: ['COMPLETED'] },
];

const EXTERNAL_STEPS: FlowStep[] = [
  {
    key: 'referral',
    label: 'در انتظار مجوز ارجاع به تعمیرگاه بیرونی',
    statuses: ['WAITING_EXTERNAL_REFERRAL_APPROVAL'],
  },
  {
    key: 'delivery',
    label: 'تحویل خودرو به تعمیرگاه بیرونی',
    statuses: ['WAITING_EXTERNAL_DELIVERY'],
  },
  {
    key: 'in_progress',
    label: 'در حال تعمیر در تعمیرگاه بیرونی',
    statuses: ['EXTERNAL_REPAIR_IN_PROGRESS'],
  },
  {
    key: 'review',
    label: 'بازگشت خودرو و بررسی اداری',
    statuses: ['WAITING_EXTERNAL_PICKUP', 'WAITING_EXTERNAL_ADMIN_REVIEW'],
  },
  { key: 'completed', label: 'تکمیل تعمیر', statuses: ['COMPLETED'] },
];

function buildSteps(order: RepairOrder): FlowStep[] {
  const branch = order.workshop_type === 'EXTERNAL' ? EXTERNAL_STEPS : INTERNAL_STEPS;
  return [...PREFIX_STEPS, ...branch];
}

function pickActiveOrder(repairs: RepairOrder[]): RepairOrder | null {
  const active = repairs.filter((r) => ACTIVE_REPAIR_STATUSES.has(r.status));
  if (active.length === 0) return null;
  return active.reduce((latest, current) =>
    (current.updated_at || '') > (latest.updated_at || '') ? current : latest,
  );
}

function FlowConnector({ done }: { done: boolean }) {
  return (
    <Box
      sx={{
        width: 2,
        flex: 1,
        minHeight: 22,
        mx: 'auto',
        bgcolor: done ? 'success.main' : 'divider',
        transition: 'background-color 0.3s ease',
      }}
    />
  );
}

function FlowNode({
  step,
  state,
  isLast,
  waitingParts,
}: {
  step: FlowStep;
  state: 'done' | 'active' | 'pending';
  isLast: boolean;
  waitingParts: boolean;
}) {
  return (
    <Stack direction="row" spacing={3.5} alignItems="stretch">
      <Stack alignItems="center" sx={{ width: 34, flexShrink: 0 }}>
        <Box
          sx={{
            width: 34,
            height: 34,
            borderRadius: '50%',
            display: 'grid',
            placeItems: 'center',
            flexShrink: 0,
            bgcolor:
              state === 'done'
                ? 'success.main'
                : state === 'active'
                  ? 'warning.main'
                  : (t) => (t.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'),
            color: state === 'pending' ? 'text.disabled' : 'common.white',
            boxShadow: state === 'active' ? '0 0 0 4px rgba(237,108,2,0.16)' : 'none',
            transition: 'all 0.3s ease',
          }}
        >
          {state === 'done' ? (
            <CheckCircle fontSize="small" />
          ) : state === 'active' ? (
            <HourglassEmpty fontSize="small" />
          ) : (
            <RadioButtonUnchecked fontSize="small" />
          )}
        </Box>
        {!isLast && <FlowConnector done={state === 'done'} />}
      </Stack>
      <Box sx={{ pb: isLast ? 0.5 : 3, pt: 0.6 }}>
        <Typography
          fontWeight={state === 'active' ? 800 : 600}
          color={
            state === 'pending' ? 'text.disabled' : state === 'active' ? 'warning.dark' : 'text.primary'
          }
        >
          {step.label}
        </Typography>
        {state === 'active' && waitingParts && (
          <Typography variant="caption" color="warning.dark" fontWeight={700} display="block" mt={0.5}>
            در انتظار تأمین قطعه
          </Typography>
        )}
      </Box>
    </Stack>
  );
}

function StoppedBanner({ order }: { order: RepairOrder }) {
  const message = STOPPED_STATUS_MESSAGES[order.status] ?? 'روند این دستور تعمیر متوقف شد.';
  const reason = order.transport_rejection_reason || order.workshop_decision_note;
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1.25,
        p: 1.75,
        borderRadius: (t) => t.radius('md'),
        bgcolor: (t) => (t.palette.mode === 'dark' ? 'rgba(224,122,106,0.12)' : 'rgba(196,92,74,0.08)'),
        border: '1px solid',
        borderColor: 'secondary.main',
      }}
    >
      <ErrorOutline color="secondary" sx={{ mt: 0.25 }} />
      <Box>
        <Typography fontWeight={800} color="secondary.dark">
          {message}
        </Typography>
        {reason && (
          <Typography variant="body2" color="text.secondary" mt={0.25}>
            {reason}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

function RecentActivity({ repairOrderId }: { repairOrderId: string }) {
  const [events, setEvents] = useState<Array<{ event_type: string; description: string; created_at: string }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getRepairOrderTimeline(repairOrderId)
      .then((result) => {
        if (!cancelled) setEvents(result);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [repairOrderId]);

  if (loading) return <LoadingState label="در حال دریافت رویدادها" />;
  if (events.length === 0) return null;

  const recent = [...events].reverse().slice(0, 5);

  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2" fontWeight={800} color="text.secondary">
        آخرین رویدادها
      </Typography>
      {recent.map((event, index) => (
        <Stack key={`${event.created_at}-${index}`} direction="row" spacing={1} alignItems="flex-start">
          <Box sx={{ mt: 0.6, width: 6, height: 6, borderRadius: '50%', bgcolor: 'secondary.main', flexShrink: 0 }} />
          <Box minWidth={0} flex={1}>
            <Typography variant="body2">{event.description}</Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDateTime(event.created_at)}
            </Typography>
          </Box>
        </Stack>
      ))}
    </Stack>
  );
}

/** "وضعیت خودروی من" — flowchart of the vehicle's current fault/repair journey. */
export function MyVehicleStatusFlow({ repairs }: { repairs: RepairOrder[] }) {
  const order = pickActiveOrder(repairs);

  if (!order) {
    return (
      <EmptyState
        icon={TaskAlt}
        title="خودرو در حال حاضر تعمیر یا خرابی فعالی ندارد"
        subtitle="به محض ثبت خرابی جدید، روند تعمیر اینجا نمایش داده می‌شود."
      />
    );
  }

  const stopped = order.status in STOPPED_STATUS_MESSAGES;
  const steps = buildSteps(order);
  const currentIndex = steps.findIndex((step) => step.statuses.includes(order.status));
  const waitingParts = order.status === 'WAITING_PARTS';

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1}>
        <PlainStatusBadge
          label={REPAIR_STATUS_LABELS[order.status] ?? order.status}
          tone={stopped ? 'error' : order.status === 'COMPLETED' ? 'success' : 'warning'}
        />
        <Typography variant="caption" color="text.secondary">
          آخرین به‌روزرسانی: {formatDateTime(order.updated_at)}
        </Typography>
      </Stack>

      {stopped && <StoppedBanner order={order} />}

      <Card variant="outlined" sx={{ borderRadius: (t) => t.radius('md') }}>
        <CardContent>
          <Stack>
            {steps.map((step, index) => {
              const state: 'done' | 'active' | 'pending' =
                currentIndex === -1
                  ? 'pending'
                  : index < currentIndex
                    ? 'done'
                    : index === currentIndex
                      ? stopped
                        ? 'done'
                        : 'active'
                      : 'pending';
              return (
                <FlowNode
                  key={step.key}
                  step={step}
                  state={state}
                  isLast={index === steps.length - 1}
                  waitingParts={waitingParts}
                />
              );
            })}
          </Stack>
        </CardContent>
      </Card>

      <RecentActivity repairOrderId={order.id} />
    </Stack>
  );
}
