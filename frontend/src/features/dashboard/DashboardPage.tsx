import {useEffect, useState} from 'react';
import {Box, Card, CardActionArea, CardContent, Stack, Typography} from '@mui/material';
import {ChevronLeft, ErrorOutline, Speed, TaskAlt} from '@mui/icons-material';
import {
    Build,
    CarRepair,
    DirectionsCar,
    PeopleAlt,
    Sync,
} from '../../components/icons3d/Icons3D';
import {Link as RouterLink} from 'react-router-dom';
import {api} from '../../api/client';
import {FeaturePage, KpiGrid} from '../../components/FeaturePage';
import {KpiCard} from '../../components/KpiCard';
import {PageHeader} from '../../components/PageHeader';
import {ErrorState, LoadingState} from '../../components/States';
import type {DriverSummary, SAPTransactionSummary, VehicleSummary} from '../../types/fmms';
import {formatDateTime, toFaNumber} from '../../utils/format';

type QueueCounts = {
    openFaults: number;
    transportQueue: number;
    workshopQueue: number;
};

type QuickLink = {
    title: string;
    subtitle: string;
    to: string;
    icon: typeof DirectionsCar;
    tone: 'primary' | 'secondary' | 'warning' | 'success' | 'error' | 'info';
    imageSrc?: string;
};

const API_ORIGIN = (() => {
    try {
        return new URL(import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').origin;
    } catch {
        return '';
    }
})();

/**
 * Operations dashboard built from vehicle/driver summary APIs and queue counts.
 */
export function DashboardPage() {
    const [vehicleSummary, setVehicleSummary] = useState<VehicleSummary | null>(null);
    const [driverSummary, setDriverSummary] = useState<DriverSummary | null>(null);
    const [sapSummary, setSapSummary] = useState<SAPTransactionSummary | null>(null);
    const [queues, setQueues] = useState<QueueCounts>({
        openFaults: 0,
        transportQueue: 0,
        workshopQueue: 0,
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const load = async () => {
        setLoading(true);
        setError('');
        try {
            const [
                vehicles,
                drivers,
                openFaults,
                transportCreated,
                transportApproved,
                workshopQueue,
                sap,
            ] = await Promise.all([
                api.getVehicleSummary(),
                api.getDriverSummary(),
                api.listFaults(undefined, {status: 'OPEN', page: 1, pageSize: 1}),
                api.listRepairOrders({status: 'CREATED', page: 1, pageSize: 1}),
                api.listRepairOrders({status: 'APPROVED', page: 1, pageSize: 1}),
                api.listRepairOrders({
                    status: 'WORKSHOP_ASSIGNED',
                    workshopType: 'INTERNAL',
                    page: 1,
                    pageSize: 1,
                }),
                api.getSapTransactionSummary().catch(() => null),
            ]);
            setVehicleSummary(vehicles);
            setDriverSummary(drivers);
            setSapSummary(sap);
            setQueues({
                openFaults: openFaults.count ?? 0,
                transportQueue: (transportCreated.count ?? 0) + (transportApproved.count ?? 0),
                workshopQueue: workshopQueue.count ?? 0,
            });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'خلاصه داشبورد بارگذاری نشد');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        void load();
    }, []);

    const workQueueLinks: QuickLink[] = [
        {
            title: 'کارتابل توزیع',
            subtitle: `${toFaNumber(queues.openFaults)} خرابی در انتظار تصمیم توزیع`,
            to: '/faults',
            icon: CarRepair,
            tone: 'secondary',
            imageSrc: '/dashboard-card-distribution.png',
        },
        {
            title: 'کارتابل ترابری',
            subtitle: `${toFaNumber(queues.transportQueue)} درخواست در صف ترابری`,
            to: '/repairs',
            icon: Build,
            tone: 'secondary',
            imageSrc: '/dashboard-card-transport.png',
        },
        {
            title: 'تعمیرگاه مرکزی',
            subtitle: `${toFaNumber(queues.workshopQueue)} درخواست در انتظار تصمیم فنی`,
            to: '/workshop',
            icon: Build,
            tone: 'warning',
            imageSrc: '/dashboard-card-workshop.png',
        },
    ];

    const masterDataLinks: QuickLink[] = [
        {
            title: 'خودروها',
            subtitle: `${toFaNumber(vehicleSummary?.active_fleet_count)} خودرو فعال`,
            to: '/vehicles',
            icon: DirectionsCar,
            tone: 'primary',
        },
        {
            title: 'راننده‌ها',
            subtitle: `${toFaNumber(driverSummary?.active_count)} راننده فعال`,
            to: '/drivers',
            icon: PeopleAlt,
            tone: 'secondary',
        },
    ];

    return (
        <FeaturePage>
            <PageHeader
                title="نمای کلی عملیات ناوگان"
                description="خلاصه وضعیت ناوگان، راننده‌ها و صف‌های عملیاتی در یک نگاه."
                breadcrumbs={[{label: 'داشبورد'}]}
                accentColor="secondary.main"
                accentSide="right"
                backgroundImage={`/dashboard.png`}
                backgroundSize="300px auto"
                backgroundPosition="left center"
            />

            {error && <ErrorState message={error} onRetry={() => void load()}/>}
            {loading && !error && <LoadingState label="در حال بارگذاری داشبورد…"/>}

            {!loading && !error && (
                <>
                    <SectionTitle title="وضعیت ناوگان"/>
                    <KpiGrid mdColumns={4}>
                        <KpiCard
                            label="خودروهای فعال"
                            value={toFaNumber(vehicleSummary?.active_fleet_count)}
                            icon={DirectionsCar}
                            tone="primary"
                        />
                        <KpiCard
                            label="آماده بهره‌برداری"
                            value={toFaNumber(vehicleSummary?.operational_fleet_count)}
                            icon={TaskAlt}
                            tone="success"
                        />
                        <KpiCard
                            label="خودروهای در تعمیر"
                            value={toFaNumber(vehicleSummary?.under_repair_fleet_count)}
                            icon={Build}
                            tone="secondary"
                        />
                        <KpiCard
                            label="خودروهای خارج از سرویس"
                            value={toFaNumber(vehicleSummary?.unusable_fleet_count)}
                            icon={ErrorOutline}
                            tone="error"
                        />
                    </KpiGrid>

                    <SectionTitle title="راننده‌ها و عملکرد"/>
                    <KpiGrid mdColumns={4}>
                        <KpiCard
                            label="راننده‌های فعال"
                            value={toFaNumber(driverSummary?.active_count)}
                            icon={PeopleAlt}
                            tone="primary"
                        />
                        <KpiCard
                            label="راننده‌های دارای خودرو"
                            value={toFaNumber(driverSummary?.with_vehicle_count)}
                            icon={DirectionsCar}
                            tone="secondary"
                        />
                        <KpiCard
                            label="میانگین کارکرد خودروها"
                            value={toFaNumber(vehicleSummary?.average_odometer_km)}
                            icon={Speed}
                            tone="info"
                        />
                        <KpiCard
                            label="میانگین خرابی در ۳۰ روز اخیر"
                            value={toFaNumber(vehicleSummary?.average_faults_last_30_days)}
                            icon={CarRepair}
                            tone="secondary"
                        />
                    </KpiGrid>

                    <SectionTitle title="صفحه‌های کاری"/>
                    <QuickLinkGrid columns={3} links={workQueueLinks} variant="work"/>

                    <SectionTitle title="دسترسی سریع"/>
                    <QuickLinkGrid columns={2} links={masterDataLinks} variant="quick"/>

                    <Card
                        variant="outlined"
                        sx={{
                            borderRadius: (t) => t.radius('md'),
                            boxShadow: '0 14px 32px rgba(15, 35, 29, 0.06)',
                        }}
                    >
                        <CardActionArea component={RouterLink} to="/sap">
                            <CardContent
                                sx={{
                                    p: {xs: 1.75, md: 2},
                                    '&:last-child': {pb: {xs: 1.75, md: 2}},
                                }}
                            >
                                <Stack
                                    direction={{xs: 'column', md: 'row'}}
                                    spacing={1.5}
                                    alignItems={{xs: 'flex-start', md: 'center'}}
                                >
                                    <Stack
                                        direction="row"
                                        spacing={1.5}
                                        alignItems="center"
                                        sx={{minWidth: 0, flex: 1}}
                                    >
                                        <Box
                                            sx={{
                                                width: 48,
                                                height: 48,
                                                borderRadius: (t) => t.radius('lg'),
                                                bgcolor: 'secondary.light',
                                                color: 'secondary.dark',
                                                display: 'grid',
                                                placeItems: 'center',
                                                flexShrink: 0,
                                            }}
                                        >
                                            <Sync fontSize="medium"/>
                                        </Box>
                                        <Box minWidth={0} flex={1}>
                                            <Typography fontWeight={800}>همگام‌سازی و تراکنش‌های SAP</Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                خودرو: {formatDateTime(vehicleSummary?.last_sap_sync_at)} · راننده:{' '}
                                                {formatDateTime(driverSummary?.last_sap_sync_at)}
                                                {sapSummary
                                                    ? ` · کل تراکنش‌ها: ${toFaNumber(sapSummary.total)} · ناموفق: ${toFaNumber(sapSummary.failed + sapSummary.exhausted)}`
                                                    : ''}
                                            </Typography>
                                        </Box>
                                    </Stack>
                                    <ChevronLeft sx={{color: 'text.secondary', display: {xs: 'none', md: 'block'}}}/>
                                </Stack>
                            </CardContent>
                        </CardActionArea>
                    </Card>
                </>
            )}
        </FeaturePage>
    );
}

function SectionTitle({title}: { title: string }) {
    return (
        <Typography
            variant="subtitle1"
            fontWeight={900}
            sx={{
                mt: {xs: 0.5, md: 1},
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                '&::before': {
                    content: '""',
                    width: 9,
                    height: 9,
                    borderRadius: '50%',
                    bgcolor: 'secondary.main',
                    flexShrink: 0,
                    boxShadow: (t) =>
                        t.palette.mode === 'dark'
                            ? '0 0 0 3px rgba(232,137,120,0.2)'
                            : '0 0 0 3px rgba(196,87,61,0.15)',
                },
            }}
        >
            {title}
        </Typography>
    );
}

function QuickLinkGrid({
                           links,
                           columns,
                           variant,
                       }: {
    links: QuickLink[];
    columns: 2 | 3;
    variant: 'work' | 'quick';
}) {
    return (
        <Box
            sx={{
                display: 'grid',
                gridTemplateColumns: {
                    xs: '1fr',
                    md: 'repeat(2, minmax(0, 1fr))',
                    lg: `repeat(${columns}, minmax(0, 1fr))`,
                },
                gap: 1.5,
            }}
        >
            {links.map((link) => (
                <QuickLinkCard key={link.to} link={link} variant={variant}/>
            ))}
        </Box>
    );
}

function QuickLinkCard({link, variant}: { link: QuickLink; variant: 'work' | 'quick' }) {
    const Icon = link.icon;
    return (
        <Card
            variant="outlined"
            sx={{
                borderRadius: (t) => t.radius('md'),
                boxShadow: '0 14px 32px rgba(15, 35, 29, 0.06)',
                overflow: 'hidden',
            }}
        >
            <CardActionArea
                component={RouterLink}
                to={link.to}
                sx={{height: '100%', alignItems: 'stretch'}}
            >
                <CardContent
                    sx={{
                        p: 1.75,
                        '&:last-child': {pb: 1.75},
                        display: 'flex',
                        gap: 1.5,
                        alignItems: 'center',
                        direction: 'rtl',
                        minHeight: variant === 'work' ? 92 : 78,
                        position: 'relative',
                    }}
                >
                    {variant === 'work' && (
                        <Box
                            sx={{
                                position: 'absolute',
                                left: 12,
                                top: '50%',
                                width: 132,
                                height: 72,
                                borderRadius: (t) => t.radius('md'),
                                display: {xs: 'none', sm: 'block'},
                                transform: 'translateY(-50%)',
                                overflow: 'hidden',
                                backgroundColor: '#fff',
                                border: '1px solid',
                                borderColor: 'divider',
                                boxShadow: '0 10px 24px rgba(15, 35, 29, 0.08)',
                                '&::after': {
                                    content: '""',
                                    position: 'absolute',
                                    inset: 0,
                                    background:
                                        'linear-gradient(90deg, rgba(255,255,255,0) 50%, rgba(255,255,255,0.86) 100%)',
                                },
                            }}
                        >
                            {link.imageSrc && (
                                <Box
                                    component="img"
                                    src={link.imageSrc}
                                    alt=""
                                    aria-hidden="true"
                                    sx={{
                                        width: '100%',
                                        height: '100%',
                                        display: 'block',
                                        objectFit: 'cover',
                                        objectPosition: 'center',
                                    }}
                                />
                            )}
                        </Box>
                    )}
                    <Box
                        sx={{
                            width: 44,
                            height: 44,
                            borderRadius: (t) => t.radius('lg'),
                            bgcolor: `${link.tone}.light`,
                            color: `${link.tone}.dark`,
                            display: 'grid',
                            placeItems: 'center',
                            flexShrink: 0,
                        }}
                    >
                        <Icon fontSize="medium"/>
                    </Box>
                    <Box minWidth={0} textAlign="right">
                        <Typography fontWeight={800}>{link.title}</Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>
                            {link.subtitle}
                        </Typography>
                    </Box>
                    <Box sx={{flex: 1}}/>
                    <ChevronLeft
                        sx={{
                            color: 'text.secondary',
                            flexShrink: 0,
                            position: 'relative',
                            zIndex: 1,
                        }}
                    />
                </CardContent>
            </CardActionArea>
        </Card>
    );
}
