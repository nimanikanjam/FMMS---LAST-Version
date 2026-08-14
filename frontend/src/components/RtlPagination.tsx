import { Pagination, Stack, Typography, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { toFaNumber } from '../utils/format';

type RtlPaginationProps = {
  page: number;
  count: number;
  onChange: (page: number) => void;
  /** Total rows across all pages — enables «نمایش … از …» summary. */
  totalItems?: number;
  pageSize?: number;
  disabled?: boolean;
};

/**
 * Branded RTL pagination for table footers.
 */
export function RtlPagination({
  page,
  count,
  onChange,
  totalItems,
  pageSize,
  disabled = false,
}: RtlPaginationProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  if (count <= 1) return null;

  const showSummary =
    typeof totalItems === 'number' &&
    totalItems > 0 &&
    typeof pageSize === 'number' &&
    pageSize > 0;

  const rangeStart = showSummary ? (page - 1) * pageSize + 1 : 0;
  const rangeEnd = showSummary ? Math.min(page * pageSize, totalItems) : 0;

  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      alignItems={{ xs: 'stretch', sm: 'center' }}
      justifyContent={showSummary ? 'space-between' : 'center'}
      spacing={1.25}
      sx={{
        pt: 0.5,
        width: '100%',
      }}
    >
      {showSummary && (
        <Typography
          variant="body2"
          color="text.secondary"
          fontWeight={700}
          sx={{
            // In RTL flex row, first item sits on the right edge of the table.
            flexShrink: 0,
            textAlign: { xs: 'right', sm: 'inherit' },
            alignSelf: { xs: 'flex-end', sm: 'center' },
          }}
        >
          نمایش {toFaNumber(rangeStart)} تا {toFaNumber(rangeEnd)} از{' '}
          {toFaNumber(totalItems)}
        </Typography>
      )}

      <Pagination
        color="primary"
        variant="outlined"
        shape="rounded"
        page={page}
        count={count}
        disabled={disabled}
        onChange={(_event, next) => onChange(next)}
        siblingCount={isMobile ? 0 : 1}
        boundaryCount={1}
        showFirstButton={!isMobile}
        showLastButton={!isMobile}
        sx={{
          alignSelf: { xs: 'center', sm: showSummary ? 'flex-start' : 'center' },
          '& .MuiPagination-ul': {
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: 0.5,
          },
          '& .MuiPaginationItem-root': {
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: 36,
            height: 36,
            margin: 0,
            padding: 0,
            lineHeight: 1,
            borderRadius: (t) => t.radius('sm'),
            fontWeight: 800,
            borderColor: 'divider',
            color: 'text.secondary',
            bgcolor: 'background.paper',
            transition:
              'background-color .15s ease, color .15s ease, border-color .15s ease, box-shadow .15s ease',
            '&:hover': {
              bgcolor: 'action.hover',
              borderColor: 'primary.light',
              color: 'primary.dark',
            },
            '&.Mui-selected': {
              bgcolor: 'primary.main',
              borderColor: 'primary.main',
              color: 'primary.contrastText',
              boxShadow: '0 2px 8px rgba(15, 107, 76, 0.22)',
              '&:hover': {
                bgcolor: 'primary.dark',
                borderColor: 'primary.dark',
                color: 'primary.contrastText',
              },
            },
            '&.Mui-disabled': {
              opacity: 0.4,
            },
          },
          '& .MuiPaginationItem-ellipsis': {
            border: 'none',
            bgcolor: 'transparent',
          },
        }}
      />
    </Stack>
  );
}
