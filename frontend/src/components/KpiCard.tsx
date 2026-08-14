import { Box, Card, CardContent, Typography } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';
import type { TypographyVariant } from '@mui/material/styles';
import { IconWell, type IconWellTone } from './IconWell';

export function KpiCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = 'primary',
  valueVariant = 'h2',
  valueNoWrap = true,
}: {
  label: string;
  value: string | number;
  helper?: string;
  icon: SvgIconComponent;
  tone?: IconWellTone;
  valueVariant?: TypographyVariant;
  valueNoWrap?: boolean;
}) {
  return (
    <Card
      sx={{
        overflow: 'visible',
        transition: 'transform .18s ease, box-shadow .2s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
        },
      }}
    >
      <CardContent sx={{ p: { xs: 1.5, md: 1.75 }, '&:last-child': { pb: { xs: 1.5, md: 1.75 } } }}>
        <Box
          display="flex"
          alignItems="center"
          justifyContent="space-between"
          gap={1.5}
          style={{ direction: 'rtl' }}
        >
          <Box minWidth={0} style={{ textAlign: 'right', direction: 'rtl' }}>
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              mb={0.75}
              fontWeight={800}
            >
              {label}
            </Typography>
            <Typography variant={valueVariant} color="text.primary" noWrap={valueNoWrap} fontWeight={900}>
              {value}
            </Typography>
            {helper && (
              <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                {helper}
              </Typography>
            )}
          </Box>
          <IconWell tone={tone} size={46}>
            <Icon />
          </IconWell>
        </Box>
      </CardContent>
    </Card>
  );
}
