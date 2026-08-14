import { useState } from 'react';
import { Box, Fade, IconButton, Stack } from '@mui/material';
import { ArrowDropDown, ChevronLeft, ChevronRight } from '@mui/icons-material';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFnsJalali } from '@mui/x-date-pickers/AdapterDateFnsJalali';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { usePickerAdapter, usePickerTranslations } from '@mui/x-date-pickers/hooks';
import type { PickersCalendarHeaderProps } from '@mui/x-date-pickers/PickersCalendarHeader';
import { faIR as pickersFaIR } from '@mui/x-date-pickers/locales';
import { faIR as jalaliFaIR } from 'date-fns-jalali/locale/fa-IR';
import { format, isValid, parseISO } from 'date-fns';
import type { SxProps, Theme } from '@mui/material/styles';

export type JalaliDateTimeFieldProps = {
  label: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
  fullWidth?: boolean;
  sx?: SxProps<Theme>;
  minDateTime?: string;
  maxDateTime?: string;
  error?: boolean;
  helperText?: string;
};

const jalaliLocaleText = {
  ...pickersFaIR.components.MuiLocalizationProvider.defaultProps.localeText,
  fieldYearPlaceholder: () => 'سال',
  fieldMonthPlaceholder: () => 'ماه',
  fieldDayPlaceholder: () => 'روز',
};

/** شنبه → جمعه — بدون اعداد locale short مثل «1ش» */
function formatPersianWeekday(date: Date): string {
  return jalaliFaIR.localize.day(date.getDay() as 0 | 1 | 2 | 3 | 4 | 5 | 6, {
    width: 'narrow',
  });
}

/** value is a local (naive) datetime string, e.g. `2024-01-01T10:30`, matching `<input type="datetime-local">` shape. */
function toDate(value?: string): Date | null {
  if (!value) return null;
  const parsed = parseISO(value);
  return isValid(parsed) ? parsed : null;
}

function toLocalDateTime(value: Date | null): string {
  if (!value || !isValid(value)) return '';
  return format(value, "yyyy-MM-dd'T'HH:mm");
}

/**
 * Header layout (RTL): previous — month/year — next
 */
function JalaliCalendarHeader(props: PickersCalendarHeaderProps) {
  const {
    currentMonth,
    disabled,
    views,
    view,
    onViewChange,
    onMonthChange,
    reduceAnimations,
    labelId,
    format: headerFormat,
  } = props;
  const adapter = usePickerAdapter();
  const translations = usePickerTranslations();

  if (views.length === 1 && views[0] === 'year') {
    return null;
  }

  const labelFormat = headerFormat ?? `${adapter.formats.month} ${adapter.formats.year}`;
  const label = adapter.formatByString(currentMonth, labelFormat);
  const showArrows = view === 'day';

  const goPrevious = () => onMonthChange(adapter.addMonths(currentMonth, -1));
  const goNext = () => onMonthChange(adapter.addMonths(currentMonth, 1));

  const toggleView = () => {
    if (views.length === 1 || !onViewChange || disabled) return;
    if (views.length === 2) {
      onViewChange(views.find((item) => item !== view) || views[0]);
      return;
    }
    const nextIndex = views.indexOf(view) !== 0 ? 0 : 1;
    onViewChange(views[nextIndex]);
  };

  return (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="space-between"
      dir="rtl"
      sx={{
        px: 0.75,
        py: 1.25,
        minHeight: 44,
        bgcolor: 'rgba(15, 107, 76, 0.1)',
        borderBottom: '1px solid',
        borderColor: 'rgba(15, 107, 76, 0.16)',
      }}
    >
      <Fade in={showArrows} appear={!reduceAnimations}>
        <IconButton
          size="small"
          onClick={goPrevious}
          disabled={disabled || !showArrows}
          aria-label={translations.previousMonth}
          sx={{
            color: 'primary.main',
            visibility: showArrows ? 'visible' : 'hidden',
            '&:hover': { bgcolor: 'rgba(15, 107, 76, 0.14)' },
          }}
        >
          <ChevronRight />
        </IconButton>
      </Fade>

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="center"
        onClick={toggleView}
        sx={{
          cursor: views.length > 1 && !disabled ? 'pointer' : 'default',
          userSelect: 'none',
          gap: 0.25,
          minWidth: 0,
        }}
      >
        <Box
          id={labelId}
          component="span"
          dir="rtl"
          sx={{ fontWeight: 800, color: 'primary.dark', fontSize: '0.95rem', whiteSpace: 'nowrap' }}
        >
          {label}
        </Box>
        {views.length > 1 && !disabled && (
          <ArrowDropDown
            sx={{
              color: 'primary.main',
              transform: view === 'year' ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s ease',
            }}
          />
        )}
      </Stack>

      <Fade in={showArrows} appear={!reduceAnimations}>
        <IconButton
          size="small"
          onClick={goNext}
          disabled={disabled || !showArrows}
          aria-label={translations.nextMonth}
          sx={{
            color: 'primary.main',
            visibility: showArrows ? 'visible' : 'hidden',
            '&:hover': { bgcolor: 'rgba(15, 107, 76, 0.14)' },
          }}
        >
          <ChevronLeft />
        </IconButton>
      </Fade>
    </Stack>
  );
}

/**
 * Shamsi (Jalali) date+time picker.
 *
 * `value` / `onChange` use a naive local datetime string (`YYYY-MM-DDTHH:mm`) —
 * the same shape `<input type="datetime-local">` produces — so it's a drop-in
 * replacement wherever that was used.
 */
export function JalaliDateTimeField({
  label,
  value = '',
  onChange,
  disabled = false,
  size = 'small',
  fullWidth = false,
  sx,
  minDateTime,
  maxDateTime,
  error = false,
  helperText,
}: JalaliDateTimeFieldProps) {
  const [open, setOpen] = useState(false);

  return (
    <Box
      sx={{
        display: 'inline-flex',
        width: fullWidth ? '100%' : undefined,
        ...((sx as object) ?? {}),
      }}
    >
      <LocalizationProvider
        dateAdapter={AdapterDateFnsJalali}
        adapterLocale={jalaliFaIR}
        localeText={jalaliLocaleText}
      >
        <DateTimePicker
          label={label}
          value={toDate(value)}
          disabled={disabled}
          open={open}
          onOpen={() => setOpen(true)}
          onClose={() => setOpen(false)}
          closeOnSelect={false}
          minDateTime={toDate(minDateTime) ?? undefined}
          maxDateTime={toDate(maxDateTime) ?? undefined}
          onChange={(next) => {
            onChange?.(toLocalDateTime(next));
          }}
          onAccept={() => setOpen(false)}
          format="yyyy/MM/dd HH:mm"
          views={['year', 'month', 'day', 'hours', 'minutes']}
          openTo="day"
          ampm={false}
          dayOfWeekFormatter={formatPersianWeekday}
          slots={{
            calendarHeader: JalaliCalendarHeader,
          }}
          slotProps={{
            textField: {
              size,
              fullWidth: true,
              error,
              helperText,
              onClick: () => {
                if (!disabled) setOpen(true);
              },
              sx: {
                width: '100%',
                direction: 'rtl',
                cursor: disabled ? 'default' : 'pointer',
                '& .MuiPickersInputBase-root, & .MuiPickersOutlinedInput-root': {
                  cursor: disabled ? 'default' : 'pointer',
                  bgcolor: open ? 'rgba(15, 107, 76, 0.04)' : 'background.paper',
                  transition: 'background-color 0.15s ease, border-color 0.15s ease',
                  paddingRight: '16px',
                  paddingLeft: '4px',
                },
                '& .MuiPickersOutlinedInput-notchedOutline': {
                  textAlign: 'right',
                },
                '& .MuiInputLabel-root': {
                  right: 22,
                  left: 'auto',
                  transformOrigin: 'top right',
                  textAlign: 'right',
                  '&.MuiInputLabel-shrink': {
                    right: 14,
                    transformOrigin: 'top right',
                  },
                },
                '& .MuiPickersSectionList-root, & .MuiPickersInputBase-sectionsContainer': {
                  direction: 'ltr',
                  justifyContent: 'flex-end',
                  cursor: disabled ? 'default' : 'pointer',
                  paddingRight: '2px',
                },
                '& .MuiInputAdornment-root': {
                  marginLeft: 0,
                  marginRight: 0,
                },
                '& .MuiInputAdornment-root .MuiIconButton-root': {
                  color: open ? 'primary.main' : 'text.secondary',
                  padding: '4px',
                  marginLeft: 0,
                  marginRight: 0,
                },
              },
              slotProps: {
                inputLabel: {
                  shrink: open || Boolean(value) || undefined,
                },
              },
            },
            openPickerButton: {
              edge: 'end',
              color: open ? 'primary' : 'default',
            },
            desktopPaper: {
              sx: {
                mt: 1,
                borderRadius: (t) => t.radius('md'),
                overflow: 'hidden',
                border: '1px solid',
                borderColor: 'rgba(15, 107, 76, 0.22)',
                boxShadow: '0 16px 40px rgba(15, 107, 76, 0.16)',
                direction: 'rtl',
                backgroundImage:
                  'linear-gradient(180deg, rgba(15, 107, 76, 0.06) 0%, rgba(255,255,255,0) 48px)',
                '& .MuiDayCalendar-header': {
                  bgcolor: 'rgba(15, 107, 76, 0.04)',
                },
                '& .MuiDayCalendar-weekDayLabel': {
                  color: 'primary.dark',
                  fontWeight: 800,
                  fontSize: '0.8rem',
                },
                '& .MuiPickersDay-root': {
                  fontWeight: 700,
                  fontFamily: 'Vazirmatn, system-ui, sans-serif',
                  '&:hover': {
                    bgcolor: 'rgba(15, 107, 76, 0.14)',
                  },
                  '&.MuiPickersDay-today': {
                    border: '1.5px solid',
                    borderColor: 'primary.main',
                    color: 'primary.dark',
                    fontWeight: 800,
                  },
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: '#ffffff',
                    fontWeight: 800,
                    boxShadow: '0 4px 12px rgba(15, 107, 76, 0.35)',
                    '&:hover': {
                      bgcolor: 'primary.dark',
                    },
                    '&:focus': {
                      bgcolor: 'primary.main',
                    },
                  },
                },
                '& .MuiPickersYear-yearButton.Mui-selected, & .MuiPickersMonth-monthButton.Mui-selected':
                  {
                    bgcolor: 'primary.main',
                    color: '#ffffff',
                    fontWeight: 800,
                  },
                '& .MuiMultiSectionDigitalClock-root': {
                  direction: 'ltr',
                },
                '& .MuiMultiSectionDigitalClockSection-item.Mui-selected': {
                  bgcolor: 'primary.main',
                  color: '#ffffff',
                  fontWeight: 800,
                  '&:hover': {
                    bgcolor: 'primary.dark',
                  },
                },
              },
            },
            layout: {
              sx: {
                direction: 'rtl',
              },
            },
          }}
        />
      </LocalizationProvider>
    </Box>
  );
}
