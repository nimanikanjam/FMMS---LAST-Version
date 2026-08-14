import { useEffect, useState, type ReactNode } from 'react';
import {
  Avatar,
  Box,
  Chip,
  Dialog,
  DialogContent,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import { Close, EmailOutlined, PersonOutline, ShieldOutlined, BadgeOutlined } from '@mui/icons-material';
import { api } from '../../api/client';
import { roleLabel } from '../../app/roles';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import type { AuthUser } from '../../types/fmms';

function profileInitials(user: AuthUser): string {
  const source = user.full_name.trim() || user.username.trim();
  if (!source) return '؟';
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`;
  return source.slice(0, 2);
}

function ProfileRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <Stack
      direction="row"
      alignItems="center"
      sx={{
        gap: 2.5,
        px: 1.5,
        py: 1.35,
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'rgba(243, 246, 244, 0.9)',
        border: '1px solid',
        borderColor: 'rgba(213, 224, 218, 0.55)',
      }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: (t) => t.radius('md'),
          bgcolor: 'rgba(15, 107, 76, 0.1)',
          color: 'primary.dark',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box minWidth={0} flex={1}>
        <Typography variant="caption" color="text.secondary" fontWeight={700} display="block">
          {label}
        </Typography>
        <Typography fontWeight={800} fontSize="0.92rem" noWrap>
          {value}
        </Typography>
      </Box>
    </Stack>
  );
}

export type ProfileModalProps = {
  open: boolean;
  onClose: () => void;
  initialUser?: AuthUser | null;
};

/**
 * Compact profile dialog for `/auth/me/`.
 */
export function ProfileModal({ open, onClose, initialUser = null }: ProfileModalProps) {
  const [user, setUser] = useState<AuthUser | null>(initialUser);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setUser(await api.me());
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : 'خطا در دریافت پروفایل');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    if (initialUser) setUser(initialUser);
    void load();
  }, [open]);

  const displayName = user?.full_name.trim() || user?.username || 'کاربر';
  const roleText = user ? roleLabel(user.role) : '';

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="xs"
      disableScrollLock
      dir="rtl"
      PaperProps={{
        sx: {
          borderRadius: (t) => t.radius('md'),
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(23, 35, 29, 0.18)',
        },
      }}
    >
      <Box sx={{ position: 'relative' }}>
        <IconButton
          size="small"
          onClick={onClose}
          aria-label="بستن"
          sx={{
            position: 'absolute',
            top: 10,
            left: 10,
            zIndex: 1,
            width: 30,
            height: 30,
            bgcolor: 'rgba(255,255,255,0.85)',
            '&:hover': { bgcolor: '#fff' },
          }}
        >
          <Close fontSize="small" />
        </IconButton>

        <Box
          sx={{
            pt: 3.5,
            pb: 2.5,
            px: 2.5,
            background: 'linear-gradient(165deg, rgba(15, 107, 76, 0.16) 0%, rgba(15, 107, 76, 0.04) 55%, #fff 100%)',
            borderBottom: '1px solid',
            borderColor: 'divider',
            textAlign: 'center',
          }}
        >
          {user ? (
            <>
              <Avatar
                sx={{
                  width: 72,
                  height: 72,
                  mx: 'auto',
                  mb: 1.5,
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  fontWeight: 800,
                  fontSize: '1.35rem',
                  boxShadow: '0 10px 24px rgba(15, 107, 76, 0.28)',
                  border: '3px solid #fff',
                }}
              >
                {profileInitials(user)}
              </Avatar>
              <Typography fontWeight={900} fontSize="1.1rem" lineHeight={1.35}>
                {displayName}
              </Typography>
              {user.username && user.full_name.trim() && user.full_name.trim() !== user.username && (
                <Typography variant="body2" color="text.secondary" mt={0.35}>
                  @{user.username}
                </Typography>
              )}
              <Chip
                size="small"
                label={roleText}
                sx={{
                  mt: 1.25,
                  fontWeight: 800,
                  bgcolor: 'rgba(15, 107, 76, 0.12)',
                  color: 'primary.dark',
                  borderRadius: (t) => t.radius('sm'),
                }}
              />
            </>
          ) : (
            <Typography fontWeight={800}>پروفایل</Typography>
          )}
        </Box>
      </Box>

      <DialogContent sx={{ px: 2, py: 2, direction: 'rtl' }}>
        {loading && !user && <LoadingState label="در حال دریافت پروفایل" />}
        {error && !user && <ErrorState message={error} onRetry={load} />}
        {!loading && !error && !user && <EmptyState title="پروفایل یافت نشد" />}
        {user && (
          <Stack spacing={1.1}>
            <ProfileRow
              icon={<BadgeOutlined fontSize="small" />}
              label="نام کاربری"
              value={user.username}
            />
            <ProfileRow
              icon={<PersonOutline fontSize="small" />}
              label="نام کامل"
              value={user.full_name || '—'}
            />
            <ProfileRow
              icon={<EmailOutlined fontSize="small" />}
              label="ایمیل"
              value={user.email || '—'}
            />
            <ProfileRow
              icon={<ShieldOutlined fontSize="small" />}
              label="نقش"
              value={roleText}
            />
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
}
