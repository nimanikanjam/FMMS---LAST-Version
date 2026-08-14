import {
  Alert,
  Box,
  Card,
  CardContent,
  Divider,
  Grid,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import {
  Add,
  DirectionsCar,
  Download,
  Inbox,
  LocalGasStation,
  ReportProblem,
  Search,
  Speed,
  Sync,
} from '@mui/icons-material';
import { useMemo, useState, type ReactNode } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { KpiCard } from '../../components/KpiCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlTextField } from '../../components/RtlTextField';
import { FilterPanel } from '../../components/FilterPanel';
import { RtlSelectField } from '../../components/RtlSelectField';
import { Button } from '../../components/Button';
import { JalaliDateField } from '../../components/JalaliDateField';
import { JalaliDateTimeField } from '../../components/JalaliDateTimeField';
import type { VehicleStatus } from '../../types/fmms';

const statuses: VehicleStatus[] = ['ACTIVE', 'UNDER_REPAIR', 'INACTIVE', 'DECOMMISSIONED'];

const vehicleRows = [
  { plate: 'ایران ۲۱ - ۴۵۶ ع ۱۲', model: 'کامیونت ایسوزو', status: 'ACTIVE' as VehicleStatus, km: '۱۲۸,۴۲۰' },
  { plate: 'ایران ۶۸ - ۲۱۹ ب ۳۴', model: 'وانت مزدا', status: 'UNDER_REPAIR' as VehicleStatus, km: '۸۶,۳۱۰' },
  { plate: 'ایران ۳۳ - ۷۸۸ س ۵۱', model: 'تریلی ولوو', status: 'DECOMMISSIONED' as VehicleStatus, km: '۳۴۲,۹۰۰' },
];

type ShowcaseSortKey = keyof typeof vehicleRows[number];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Box component="section">
      <Typography variant="h2" mb={1.5}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

export function ComponentShowcasePage() {
  const [jalaliDate, setJalaliDate] = useState('');
  const [jalaliDateTime, setJalaliDateTime] = useState('');
  const [orderBy, setOrderBy] = useState<ShowcaseSortKey>('plate');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const sortedRows = useMemo(() => {
    return [...vehicleRows].sort((a, b) => {
      const result = String(a[orderBy]).localeCompare(String(b[orderBy]), 'fa', { numeric: true, sensitivity: 'base' });
      return order === 'asc' ? result : -result;
    });
  }, [order, orderBy]);

  const changeSort = (key: ShowcaseSortKey) => {
    if (orderBy === key) {
      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setOrderBy(key);
    setOrder('asc');
  };
  const showcaseColumns: Array<RtlDataTableColumn<typeof vehicleRows[number], ShowcaseSortKey>> = [
    { key: 'plate', label: 'پلاک', sortable: true, render: (row) => row.plate },
    { key: 'model', label: 'مدل', sortable: true, render: (row) => row.model },
    { key: 'status', label: 'وضعیت', sortable: true, render: (row) => <VehicleStatusBadge status={row.status} /> },
    { key: 'km', label: 'کیلومتر', sortable: true, render: (row) => row.km },
  ];

  return (
    <Stack spacing={2.25} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="کتابخانه کامپوننت‌ها"
        description="نمونه قطعات پایه برای صفحه‌های فاز ۱"
        breadcrumbs={[
          { label: 'داشبورد', to: '/vehicles' },
          { label: 'کامپوننت‌ها' },
        ]}
        actions={
          <>
            <Button variant="outlined" color="secondary" startIcon={<Download />}>
              خروجی
            </Button>
            <Button variant="contained" color="primary" startIcon={<Add />}>
              اقدام اصلی
            </Button>
          </>
        }
      />

      <Section title="کارت‌های شاخص">
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <KpiCard label="کل خودروها" value="۱۲۸" helper="همگام با SAP" icon={DirectionsCar} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <KpiCard label="در تعمیر" value="۹" helper="نیازمند پیگیری" icon={ReportProblem} tone="warning" />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <KpiCard label="میانگین پیمایش" value="۲۱۴ km" helper="روزانه" icon={Speed} tone="info" />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <KpiCard label="مصرف ثبت‌شده" value="۳,۸۲۰ L" helper="ماه جاری" icon={LocalGasStation} tone="secondary" />
          </Grid>
        </Grid>
      </Section>

      <Section title="تقویم شمسی">
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
            <Card>
              <CardContent>
                <JalaliDateField label="تاریخ" value={jalaliDate} onChange={setJalaliDate} fullWidth />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
            <Card>
              <CardContent>
                <JalaliDateTimeField
                  label="تاریخ و ساعت"
                  value={jalaliDateTime}
                  onChange={setJalaliDateTime}
                  fullWidth
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Section>

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Section title="فرم و فیلتر">
            <Stack spacing={1.5}>
              <FilterPanel>
                <RtlTextField label="جست‌وجوی پلاک یا کد SAP" fullWidth InputProps={{ startAdornment: <Search fontSize="small" /> }} />
                <RtlSelectField<VehicleStatus> label="وضعیت خودرو" defaultValue="ACTIVE">
                  {statuses.map((status) => (
                    <MenuItem key={status} value={status}>
                      <VehicleStatusBadge status={status} />
                    </MenuItem>
                  ))}
                </RtlSelectField>
              </FilterPanel>
              <Card>
                <CardContent>
                  <Stack spacing={1.5}>
                    <RtlTextField label="کیلومتر امروز" defaultValue="128430" fullWidth />
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                      <Button variant="contained" color="primary" startIcon={<Sync />} fullWidth>
                        ثبت تغییر
                      </Button>
                      <Button variant="outlined" color="secondary" fullWidth>
                        انصراف
                      </Button>
                      <Button variant="contained" color="secondary" loading fullWidth>
                        در حال ثبت
                      </Button>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            </Stack>
          </Section>
        </Grid>

        <Grid size={{ xs: 12, lg: 7 }}>
          <Section title="جدول داده">
            <RtlDataTable
              columns={showcaseColumns}
              rows={sortedRows}
              getRowKey={(row) => row.plate}
              minWidth={640}
              orderBy={orderBy}
              order={order}
              onSort={changeSort}
            />
          </Section>
        </Grid>
      </Grid>

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, md: 6, xl: 4 }}>
          <Section title="وضعیت‌ها">
            <Card>
              <CardContent>
                <Stack direction="row" gap={1} flexWrap="wrap">
                  {statuses.map((status) => (
                    <VehicleStatusBadge key={status} status={status} />
                  ))}
                  <PlainStatusBadge label="ثبت دستی راننده" />
                </Stack>
                <Divider sx={{ my: 2 }} />
                <Stack direction="row" gap={1} flexWrap="wrap">
                  {statuses.map((status) => (
                    <VehicleStatusBadge key={`${status}-solid`} status={status} appearance="solid" />
                  ))}
                  <PlainStatusBadge label="سالید" appearance="solid" />
                </Stack>
                <Divider sx={{ my: 2 }} />
                <Alert severity="info">همگام‌سازی بعدی: ۲۴ ساعت آینده</Alert>
              </CardContent>
            </Card>
          </Section>
        </Grid>
        <Grid size={{ xs: 12, md: 6, xl: 4 }}>
          <Section title="حالت‌های صفحه">
            <Card>
              <CardContent>
                <Stack spacing={1.5}>
                  <LoadingState label="در حال دریافت خودروها" />
                  <ErrorState message="ارتباط با سرویس برقرار نشد." onRetry={() => undefined} />
                </Stack>
              </CardContent>
            </Card>
          </Section>
        </Grid>
        <Grid size={{ xs: 12, xl: 4 }}>
          <Section title="حالت خالی">
            <Card>
              <CardContent>
                <EmptyState title="داده‌ای برای نمایش نیست" subtitle="پس از همگام‌سازی SAP، رکوردها اینجا دیده می‌شوند." icon={Inbox} />
              </CardContent>
            </Card>
          </Section>
        </Grid>
      </Grid>
    </Stack>
  );
}
