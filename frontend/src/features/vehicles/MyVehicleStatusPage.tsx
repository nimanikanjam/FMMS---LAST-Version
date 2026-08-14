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
import { api } from '../../api/client';
import { FeaturePage } from '../../components/FeaturePage';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { VehicleStatusBadge } from '../../components/StatusBadge';
import type { AuthUser, RepairOrder, Vehicle } from '../../types/fmms';
import { MyVehicleStatusFlow } from './MyVehicleStatusFlow';

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

      {!loading && !error && user && !user.linked_driver && (
        <EmptyState
          title="این صفحه مخصوص راننده‌هاست"
          subtitle="حساب کاربری شما به‌عنوان راننده در سامانه ثبت نشده است."
        />
      )}

      {!loading && !error && user?.linked_driver && assignedVehicles.length === 0 && (
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
          <Card variant="outlined" sx={{ borderRadius: (t) => t.radius('md') }}>
            <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
                <Stack>
                  <Typography fontWeight={900} fontSize="1.1rem">
                    {selectedVehicle.license_plate}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    شناسه خودرو: {selectedVehicle.vehicle_number}
                  </Typography>
                </Stack>
                <VehicleStatusBadge status={selectedVehicle.status} label={selectedVehicle.status_label} />
              </Stack>
            </CardContent>
          </Card>

          <MyVehicleStatusFlow repairs={repairs} />

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
