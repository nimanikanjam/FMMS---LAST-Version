import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Checkbox,
  FormControlLabel,
  InputAdornment,
  Stack,
  Typography,
} from '@mui/material';
import { Analytics, Lock, Person, PrecisionManufacturing, Visibility, VisibilityOff } from '@mui/icons-material';
import { DirectionsCar, Sync } from '../../components/icons3d/Icons3D';
import { api, ApiError } from '../../api/client';
import { Button } from '../../components/Button';
import { RtlTextField } from '../../components/RtlTextField';
import { ThemeModeToggle } from '../../components/ThemeModeToggle';

const featureItems = [
  { label: 'کنترل وضعیت ناوگان و خودروهای عملیاتی', icon: DirectionsCar },
  { label: 'همگام‌سازی زمان‌بندی‌شده با SAP', icon: Sync },
  { label: 'ثبت پیمایش، خرابی و تعمیرات روزانه', icon: PrecisionManufacturing },
  { label: 'داشبورد تحلیلی برای تصمیم‌گیری سریع', icon: Analytics },
];

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (api.getAccessToken()) return <Navigate to="/dashboard" replace />;

  const submit = async () => {
    setError('');
    setSubmitting(true);
    try {
      const response = await api.login(username, password);
      api.setAuthSession(response);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('نام کاربری یا رمز عبور صحیح نیست.');
      } else {
        setError(err instanceof Error ? err.message : 'ورود انجام نشد.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        bgcolor: 'background.default',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Ambient background blobs */}
      <Box
        sx={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          background: (theme) =>
            theme.palette.mode === 'dark'
              ? 'radial-gradient(ellipse 50% 40% at 85% 10%, rgba(46,173,116,0.12) 0%, transparent 55%), radial-gradient(ellipse 40% 35% at 10% 90%, rgba(224,122,106,0.10) 0%, transparent 50%)'
              : 'radial-gradient(ellipse 50% 40% at 85% 10%, rgba(15,107,76,0.12) 0%, transparent 55%), radial-gradient(ellipse 40% 35% at 10% 90%, rgba(196,92,74,0.10) 0%, transparent 50%)',
          zIndex: 0,
        }}
      />

      {/* Brand panel (desktop) */}
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flex: '1 1 52%',
          minHeight: '100vh',
          position: 'relative',
          background: (theme) =>
            [
              'radial-gradient(ellipse 70% 60% at 18% 12%, rgba(255,255,255,0.85) 0%, transparent 58%)',
              'radial-gradient(ellipse 45% 40% at 90% 85%, rgba(196,92,74,0.22) 0%, transparent 55%)',
              `linear-gradient(160deg, #FFFFFF 0%, ${theme.palette.primary.light} 28%, ${theme.palette.primary.main} 72%, ${theme.palette.primary.dark} 100%)`,
            ].join(', '),
          color: 'primary.dark',
          alignItems: 'center',
          justifyContent: 'center',
          px: { md: 5, lg: 8 },
          py: 6,
          overflow: 'hidden',
          zIndex: 1,
        }}
      >
        {/* Decorative grid */}
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            opacity: 0.07,
            backgroundImage:
              'linear-gradient(rgba(15,107,76,0.9) 1px, transparent 1px), linear-gradient(90deg, rgba(15,107,76,0.9) 1px, transparent 1px)',
            backgroundSize: '48px 48px',
            pointerEvents: 'none',
            maskImage: 'linear-gradient(180deg, rgba(0,0,0,0.55) 0%, transparent 90%)',
          }}
        />

        <Stack
          spacing={4.5}
          alignItems="flex-start"
          sx={{
            width: '100%',
            maxWidth: 560,
            position: 'relative',
            zIndex: 1,
            textAlign: 'right',
            mr: 0,
          }}
        >
          {/* Logo + brand */}
          <Stack direction="row" alignItems="center" spacing={2} sx={{ width: '100%' }}>
            <Box
              component="img"
              src="/logo-golestan.webp"
              alt="لوگوی گلستان"
              sx={{
                width: { md: 72, lg: 88 },
                height: { md: 72, lg: 88 },
                objectFit: 'contain',
                filter: 'drop-shadow(0 8px 20px rgba(15,107,76,0.28))',
                flexShrink: 0,
                ml: 2,
              }}
            />
            <Box sx={{ minWidth: 0 }}>
              <Typography
                sx={{
                  fontWeight: 900,
                  fontSize: { md: '1.15rem', lg: '1.35rem' },
                  color: 'primary.dark',
                  letterSpacing: '-0.02em',
                }}
              >
                گروه صنعتی گلستان
              </Typography>
              <Typography sx={{ color: 'primary.dark', opacity: 0.7, fontWeight: 700, fontSize: '0.9rem' }}>
                سامانه مدیریت نگهداری ناوگان (FMMS)
              </Typography>
            </Box>
          </Stack>

          <Stack spacing={1.5} sx={{ width: '100%' }}>
            <Typography
              sx={{
                fontSize: { md: '1.5rem', lg: '2rem' },
                fontWeight: 900,
                lineHeight: 1.4,
                color: 'primary.dark',
                whiteSpace: { md: 'nowrap' },
              }}
            >
              پلتفرم مدیریت هوشمند{' '}
              <Box component="span" sx={{ color: 'secondary.dark' }}>
                نگهداری ناوگان
              </Box>
            </Typography>
            <Typography
              sx={{
                color: 'primary.dark',
                fontSize: '1.02rem',
                lineHeight: 1.9,
                opacity: 0.82,
                maxWidth: 480,
              }}
            >
              کنترل خودروها، پیمایش روزانه، خرابی‌ها و تعمیرات با یک جریان متمرکز و قابل اتصال به SAP
            </Typography>
          </Stack>

          <Stack spacing={1.5} sx={{ width: '100%' }}>
            {featureItems.map((item) => {
              const Icon = item.icon;
              return (
                <Stack
                  key={item.label}
                  direction="row"
                  alignItems="center"
                  spacing={1.75}
                  sx={{
                    width: '100%',
                    px: 1.5,
                    py: 1.15,
                    borderRadius: (t) => t.radius('lg'),
                    bgcolor: 'rgba(255,255,255,0.28)',
                    border: '1px solid rgba(255,255,255,0.45)',
                    backdropFilter: 'blur(10px)',
                    boxShadow: '0 4px 16px rgba(15,107,76,0.08)',
                  }}
                >
                  <Box
                    sx={{
                      width: 40,
                      height: 40,
                      borderRadius: (t) => t.radius('md'),
                      background:
                        'linear-gradient(145deg, rgba(255,255,255,0.55) 0%, rgba(15,107,76,0.85) 100%)',
                      color: '#fff',
                      display: 'grid',
                      placeItems: 'center',
                      flexShrink: 0,
                      boxShadow:
                        '0 4px 12px rgba(15,107,76,0.25), inset 0 1px 0 rgba(255,255,255,0.4)',
                      '& svg': { filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))' },
                    }}
                  >
                    <Icon fontSize="small" />
                  </Box>
                  <Typography sx={{ color: 'primary.dark', fontWeight: 800, fontSize: '0.95rem', pr: 0.5 }}>
                    {item.label}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>
        </Stack>
      </Box>

      {/* Form panel */}
      <Box
        sx={{
          flex: { xs: '1 1 100%', md: '1 1 48%' },
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          px: { xs: 2.5, sm: 4 },
          py: { xs: 4, md: 6 },
          position: 'relative',
          zIndex: 1,
        }}
      >
        <Box sx={{ position: 'absolute', top: 16, left: 16, zIndex: 2 }}>
          <ThemeModeToggle />
        </Box>
        <Box
          sx={{
            width: '100%',
            maxWidth: 420,
            p: { xs: 2.5, sm: 3.5 },
            borderRadius: (t) => t.radius('xl'),
            bgcolor: (theme) =>
              theme.palette.mode === 'dark' ? 'rgba(21, 28, 24, 0.92)' : 'rgba(255,255,255,0.92)',
            border: '1px solid',
            borderColor: 'divider',
            boxShadow: (theme) =>
              theme.palette.mode === 'dark'
                ? '0 24px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)'
                : '0 24px 60px rgba(15,107,76,0.12), 0 4px 16px rgba(23,35,29,0.06), inset 0 1px 0 rgba(255,255,255,0.9)',
            backdropFilter: 'blur(16px)',
            position: 'relative',
            overflow: 'hidden',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 4,
              background: (theme) =>
                `linear-gradient(90deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            },
          }}
        >
          {/* Mobile logo */}
          <Stack
            alignItems="center"
            spacing={1.25}
            sx={{ display: { xs: 'flex', md: 'none' }, mb: 3 }}
          >
            <Box
              component="img"
              src="/logo-golestan.webp"
              alt="لوگوی گلستان"
              sx={{
                width: 72,
                height: 72,
                objectFit: 'contain',
                filter: 'drop-shadow(0 6px 16px rgba(15,107,76,0.22))',
              }}
            />
            <Typography fontWeight={900} color="primary.dark" fontSize="1.05rem">
              گروه صنعتی گلستان
            </Typography>
          </Stack>

          <Stack spacing={0.5} mb={3} sx={{ textAlign: 'right' }}>
            <Typography variant="h1" sx={{ fontSize: { xs: '1.45rem', sm: '1.65rem' }, fontWeight: 900 }}>
              ورود به سامانه
            </Typography>
            <Typography color="text.secondary" fontWeight={600} fontSize="0.9rem">
              لطفاً نام کاربری و رمز عبور سازمانی خود را وارد کنید
            </Typography>
          </Stack>

          <Stack
            component="form"
            spacing={2}
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
          >
            {error ? (
              <Alert severity="error" sx={{ borderRadius: (t) => t.radius('md'), fontWeight: 700 }}>
                {error}
              </Alert>
            ) : null}

            <RtlTextField
              label="نام کاربری"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              fullWidth
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Person fontSize="small" color="action" />
                  </InputAdornment>
                ),
              }}
            />

            <RtlTextField
              label="رمز عبور"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              fullWidth
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock fontSize="small" color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <Box
                      component="button"
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? 'مخفی کردن رمز' : 'نمایش رمز'}
                      sx={{
                        border: 0,
                        background: 'transparent',
                        cursor: 'pointer',
                        display: 'grid',
                        placeItems: 'center',
                        color: 'text.secondary',
                        p: 0.5,
                        '&:hover': { color: 'primary.main' },
                      }}
                    >
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </Box>
                  </InputAdornment>
                ),
              }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  size="small"
                  color="primary"
                />
              }
              label={
                <Typography fontWeight={700} fontSize="0.875rem" color="text.secondary">
                  مرا به خاطر بسپار
                </Typography>
              }
              sx={{ m: 0, alignSelf: 'flex-start' }}
            />

            <Button
              type="submit"
              variant="contained"
              color="primary"
              size="large"
              loading={submitting}
              disabled={!username.trim() || !password}
              fullWidth
              sx={{
                mt: 0.5,
                minHeight: 48,
                fontSize: '1rem',
                fontWeight: 900,
                borderRadius: (t) => t.radius('md'),
                background: (theme) =>
                  `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                boxShadow: '0 10px 24px rgba(15,107,76,0.28)',
                '&:hover': {
                  background: (theme) =>
                    `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, #083528 100%)`,
                  boxShadow: '0 12px 28px rgba(15,107,76,0.36)',
                },
              }}
            >
              ورود به سامانه
            </Button>
          </Stack>

          <Typography
            variant="caption"
            color="text.disabled"
            fontWeight={700}
            display="block"
            textAlign="center"
            mt={3}
          >
            © گروه صنعتی گلستان — FMMS
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
