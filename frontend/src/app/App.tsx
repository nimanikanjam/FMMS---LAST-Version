import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Box, Card, CardContent, Typography } from '@mui/material';
import { AppLayout } from '../layouts/AppLayout';
import { api } from '../api/client';
import { LoginPage } from '../features/auth/LoginPage';
import { VehiclePage } from '../features/vehicles/VehiclePage';
import { DriversPage } from '../features/drivers/DriversPage';
import { MyVehicleStatusPage } from '../features/vehicles/MyVehicleStatusPage';
import { ChecklistsPage } from '../features/inspections/ChecklistsPage';
import { InspectionPage } from '../features/inspections/InspectionPage';
import { DistributionFaultsPage } from '../features/faults/DistributionFaultsPage';
import { ManualFaultPage } from '../features/faults/ManualFaultPage';
import { TransportRepairsPage } from '../features/repairs/TransportRepairsPage';
import { CentralWorkshopPage } from '../features/workshop/CentralWorkshopPage';
import { TransportPartsPage } from '../features/transport/TransportPartsPage';
import { HandoverPage } from '../features/handover/HandoverPage';
import { ExternalWorkshopPage } from '../features/externalWorkshop/ExternalWorkshopPage';
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { SapTransactionsPage } from '../features/sap/SapTransactionsPage';
import { ComponentShowcasePage } from '../features/showcase/ComponentShowcasePage';
import { MaterialsPage } from '../features/materials/MaterialsPage';
import { UsersPage } from '../features/users/UsersPage';
import { modules } from './modules';
import { RequireModule } from './RequireModule';
import { CurrentUserProvider } from './CurrentUserContext';

function PlaceholderPage({ label }: { label: string }) {
  return (
    <Box maxWidth={720}>
      <Card>
        <CardContent>
          <Typography variant="h2" mb={1}>
            {label}
          </Typography>
          <Typography color="text.secondary">
            این بخش در فازهای بعدی صفحه‌به‌صفحه فعال می‌شود.
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

function RequireAuth() {
  if (!api.getAccessToken()) return <Navigate to="/login" replace />;
  return (
    <CurrentUserProvider>
      <AppLayout />
    </CurrentUserProvider>
  );
}

function guarded(moduleKey: string, element: ReactNode) {
  return <RequireModule moduleKey={moduleKey}>{element}</RequireModule>;
}

const dedicatedPaths = new Set([
  '/dashboard',
  '/vehicles',
  '/checklists',
  '/drivers',
  '/my-vehicle-status',
  '/inspections',
  '/faults',
  '/faults/new',
  '/repairs',
  '/transport/parts',
  '/workshop',
  '/handover',
  '/driver/external-workshop',
  '/transport/external-workshop',
  '/materials',
  '/sap',
  '/components',
  '/users',
]);

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={guarded('dashboard', <DashboardPage />)} />
        <Route path="/vehicles" element={guarded('vehicles', <VehiclePage />)} />
        <Route path="/checklists" element={guarded('checklists', <ChecklistsPage />)} />
        <Route path="/drivers" element={guarded('drivers', <DriversPage />)} />
        <Route path="/drivers/:driverId" element={guarded('drivers', <DriversPage />)} />
        <Route
          path="/my-vehicle-status"
          element={guarded('myVehicleStatus', <MyVehicleStatusPage />)}
        />
        <Route path="/inspections" element={guarded('inspections', <InspectionPage />)} />
        <Route path="/faults" element={guarded('faults', <DistributionFaultsPage />)} />
        <Route path="/faults/new" element={guarded('manualFault', <ManualFaultPage />)} />
        <Route path="/repairs" element={guarded('repairs', <TransportRepairsPage />)} />
        <Route
          path="/transport/parts"
          element={guarded('transportParts', <TransportPartsPage />)}
        />
        <Route path="/workshop" element={guarded('workshop', <CentralWorkshopPage />)} />
        <Route path="/handover" element={guarded('handover', <HandoverPage />)} />
        <Route
          path="/driver/external-workshop"
          element={guarded('driverExternalWorkshop', <ExternalWorkshopPage mode="driver" />)}
        />
        <Route
          path="/transport/external-workshop"
          element={guarded('transportExternalWorkshop', <ExternalWorkshopPage mode="transport" />)}
        />
        <Route path="/materials" element={guarded('materials', <MaterialsPage />)} />
        <Route path="/sap" element={guarded('sap', <SapTransactionsPage />)} />
        <Route path="/users" element={guarded('users', <UsersPage />)} />
        <Route path="/components" element={guarded('components', <ComponentShowcasePage />)} />
        {modules
          .filter((item) => !item.enabled && !dedicatedPaths.has(item.path))
          .map((item) => (
            <Route
              key={item.key}
              path={item.path}
              element={guarded(item.key, <PlaceholderPage label={item.label} />)}
            />
          ))}
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
