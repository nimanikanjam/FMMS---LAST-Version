/**
 * Standalone driver-facing page: "وضعیت خودروی من".
 *
 * Resolves the logged-in driver's assigned vehicle(s) and renders the
 * fault/repair flowchart from MyVehicleStatusFlow. Kept in its own file —
 * to remove the feature, delete this file + MyVehicleStatusFlow.tsx, drop
 * the route/module entries (App.tsx, app/modules.ts, app/access.ts).
 */
import { useEffect, useState } from 'react';
import { Card, CardActionArea, CardContent, Stack, Typography } from '@mui/material';
import { AccessTime, Notifications } from '@mui/icons-material';
import { api } from '../../api/client';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { KpiCard } from '../../components/KpiCard';
import { CarRepair, DirectionsCar } from '../../components/icons3d/Icons3D';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { VehicleStatusBadge } from '../../components/StatusBadge';
import type { AuthUser, RepairOrder, Vehicle, VehicleStatus } from '../../types/fmms';
import { formatDateTime } from '../../utils/format';
import {
  MyVehicleStatusFlow,
  pickActiveOrder,
  REPAIR_STATUS_LABELS,
  type RepairTimelineEvent,
} from './MyVehicleStatusFlow';

const VEHICLE_STATUS_TONE: Record<VehicleStatus, 'success' | 'warning' | 'error' | 'secondary'> = {
  ACTIVE: 'success',
  UNDER_REPAIR: 'warning',
  UNDER_EXTERNAL_REPAIR: 'warning',
  WAITING_DRIVER_CONFIRMATION: 'warning',
  EXITED_CENTER: 'secondary',
  SUSPENDED: 'error',
  OUT_OF_SERVICE: 'error',
  DECOMMISSIONED: 'error',
  INACTIVE: 'secondary',
};

const VEHICLE_PAGE_SIZE = 50;

function vehicleAssignedToDriver(vehicle: Vehicle, customerNumber: string): boolean {
  return (
    vehicle.driver1?.customer_number === customerNumber ||
    vehicle.driver2?.customer_number === customerNumber
  );
}

async function findAssignedVehicles(customerNumber: string): Promise<Vehicle[]> {
  let page = 1;
  let loaded: Vehicle[] = [];
  let total = Infinity;
  while (loaded.length < total) {
    const result = await api.listVehicles('', 'license_plate', {
      page,
      pageSize: VEHICLE_PAGE_SIZE,
    });
    loaded = [...loaded, ...result.results];
    total = result.count;
    page += 1;
    if (result.results.length === 0) break;
  }
  return loaded.filter((vehicle) => vehicleAssignedToDriver(vehicle, customerNumber));
}

export function MyVehicleStatusPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [assignedVehicles, setAssignedVehicles] = useState<Vehicle[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<Vehicle | null>(null);
  const [repairs, setRepairs] = useState<RepairOrder[]>([]);
  const [events, setEvents] = useState<RepairTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      setLoading(true);
      setError('');
      try {
        const me = await api.me();
        if (cancelled) return;
        setUser(me);

        if (me.assigned_vehicle_id) {
          const [vehicle, repairsResult] = await Promise.all([
            api.getVehicle(me.assigned_vehicle_id),
            api.listRepairOrders({ vehicleId: me.assigned_vehicle_id }),
          ]);
          if (cancelled) return;
          setAssignedVehicles([vehicle]);
          setSelectedVehicle(vehicle);
          setRepairs(repairsResult.results ?? []);
          return;
        }

        const customerNumber = me.linked_driver?.customer_number;
        if (!customerNumber) return;

        const vehicles = await findAssignedVehicles(customerNumber);
        if (cancelled) return;
        setAssignedVehicles(vehicles);
        if (vehicles.length === 1) {
          const repairsResult = await api.listRepairOrders({ vehicleId: vehicles[0].id });
          if (cancelled) return;
          setSelectedVehicle(vehicles[0]);
          setRepairs(repairsResult.results ?? []);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'دریافت اطلاعات خودرو انجام نشد');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeOrder = pickActiveOrder(repairs);
  const activeOrderId = activeOrder?.id ?? '';

  useEffect(() => {
    if (!activeOrderId) {
      setEvents([]);
      return;
    }
    let cancelled = false;
    api
      .getRepairOrderTimeline(activeOrderId)
      .then((result) => {
        if (!cancelled) setEvents(result);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeOrderId]);

  const latestEvent = events[events.length - 1] ?? null;

  const openVehicle = async (vehicle: Vehicle) => {
    setLoading(true);
    setError('');
    try {
      const repairsResult = await api.listRepairOrders({ vehicleId: vehicle.id });
      setSelectedVehicle(vehicle);
      setRepairs(repairsResult.results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت وضعیت خودرو انجام نشد');
    } finally {
      setLoading(false);
    }
  };

  return (
    <FeaturePage>
      <PageHeader
        title="وضعیت خودروی من"
        description="روند خرابی و تعمیر خودروی خودتان را به‌صورت لحظه‌ای دنبال کنید."
        breadcrumbs={[{ label: 'راننده' }, { label: 'وضعیت خودروی من' }]}
        accentColor="secondary.main"
      />

      {loading && <LoadingState label="در حال دریافت اطلاعات خودرو" />}

      {!loading && error && <ErrorState message={error} onRetry={() => window.location.reload()} />}

      {!loading && !error && user && !user.linked_driver && !user.assigned_vehicle_id && (
        <EmptyState
          title="این صفحه مخصوص راننده‌هاست"
          subtitle="حساب کاربری شما به‌عنوان راننده در سامانه ثبت نشده و خودرویی هم به شما تخصیص نیافته است."
        />
      )}

      {!loading &&
        !error &&
        (user?.linked_driver || user?.assigned_vehicle_id) &&
        assignedVehicles.length === 0 && (
        <EmptyState
          title="خودرویی به شما اساین نشده است"
          subtitle="با واحد ترابری هماهنگ کنید تا خودرویی به شما تخصیص یابد."
        />
      )}

      {!loading &&
        !error &&
        assignedVehicles.length > 1 &&
        !selectedVehicle && (
          <Stack spacing={1.25}>
            <Typography fontWeight={800}>خودروی مورد نظر را انتخاب کنید</Typography>
            {assignedVehicles.map((vehicle) => (
              <Card key={vehicle.id} variant="outlined" sx={{ borderRadius: (t) => t.radius('md') }}>
                <CardActionArea onClick={() => void openVehicle(vehicle)}>
                  <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
                      <Stack>
                        <Typography fontWeight={800}>{vehicle.license_plate}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          شناسه خودرو: {vehicle.vehicle_number}
                        </Typography>
                      </Stack>
                      <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Stack>
        )}

      {!loading && !error && selectedVehicle && (
        <Stack spacing={2}>
          <KpiGrid mdColumns={4}>
            <KpiCard
              label="پلاک و شناسه خودرو"
              value={selectedVehicle.license_plate}
              helper={`شناسه: ${selectedVehicle.vehicle_number}`}
              icon={DirectionsCar}
              tone="primary"
            />
            <KpiCard
              label="وضعیت خودرو"
              value={selectedVehicle.status_label}
              icon={CarRepair}
              tone={VEHICLE_STATUS_TONE[selectedVehicle.status] ?? 'secondary'}
            />
            <KpiCard
              label="آخرین به‌روزرسانی"
              value={
                activeOrder
                  ? formatDateTime(activeOrder.updated_at)
                  : formatDateTime(selectedVehicle.updated_at)
              }
              helper={activeOrder ? REPAIR_STATUS_LABELS[activeOrder.status] ?? activeOrder.status : undefined}
              icon={AccessTime}
              tone="info"
            />
            <KpiCard
              label="آخرین رویداد"
              value={latestEvent ? latestEvent.description : 'رویدادی ثبت نشده'}
              helper={latestEvent ? formatDateTime(latestEvent.created_at) : undefined}
              icon={Notifications}
              tone="secondary"
            />
          </KpiGrid>

          <MyVehicleStatusFlow repairs={repairs} events={events} />

          {assignedVehicles.length > 1 && (
            <Typography
              variant="body2"
              color="secondary.main"
              fontWeight={700}
              sx={{ cursor: 'pointer', width: 'fit-content' }}
              onClick={() => setSelectedVehicle(null)}
            >
              انتخاب خودروی دیگر
            </Typography>
          )}
        </Stack>
      )}
    </FeaturePage>
  );
}
