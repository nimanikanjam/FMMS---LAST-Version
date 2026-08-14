import { Autocomplete } from '@mui/material';
import type { AutocompleteProps } from '@mui/material';
import { RtlTextField } from './RtlTextField';

export type RtlAutocompleteProps<
  T,
  Multiple extends boolean | undefined = false,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false,
> = Omit<
  AutocompleteProps<T, Multiple, DisableClearable, FreeSolo>,
  'renderInput'
> & {
  label: string;
  error?: boolean;
  helperText?: string;
  placeholder?: string;
  size?: 'small' | 'medium';
};

/**
 * Branded RTL autocomplete — the dropdown (popup) and clear (×) icons sit
 * on the left of the field, matching RtlSelectField's icon placement.
 */
export function RtlAutocomplete<
  T,
  Multiple extends boolean | undefined = false,
  DisableClearable extends boolean | undefined = false,
  FreeSolo extends boolean | undefined = false,
>({
  label,
  error,
  helperText,
  placeholder,
  size = 'small',
  sx,
  ...props
}: RtlAutocompleteProps<T, Multiple, DisableClearable, FreeSolo>) {
  return (
    <Autocomplete
      {...props}
      size={size}
      renderInput={(params) => (
        <RtlTextField
          {...params}
          label={label}
          placeholder={placeholder}
          error={error}
          helperText={helperText}
        />
      )}
      sx={{
        direction: 'rtl',
        // MUI reserves the icons' space with paddingRight (LTR assumption).
        // Flip it: free up the right side, reserve room on the left instead
        // — wide enough for both the popup arrow and the clear (×) button.
        '& .MuiOutlinedInput-root.MuiAutocomplete-inputRoot': {
          paddingLeft: '56px !important',
          paddingRight: '9px !important',
        },
        '& .MuiAutocomplete-input': {
          textAlign: 'right',
          paddingRight: '4px',
          paddingLeft: '5px',
        },
        // MUI's own rule is scoped as ".MuiOutlinedInput-root .MuiAutocomplete-endAdornment"
        // (higher specificity than a bare class selector) — match it so this wins.
        '& .MuiOutlinedInput-root .MuiAutocomplete-endAdornment': {
          left: '9px !important',
          right: 'auto !important',
        },
        '& .MuiAutocomplete-popupIndicator': {
          color: 'text.secondary',
        },
        '& .MuiAutocomplete-clearIndicator': {
          color: 'text.secondary',
        },
        ...sx,
      }}
      slotProps={{
        ...props.slotProps,
        paper: {
          ...props.slotProps?.paper,
          sx: {
            direction: 'rtl',
            textAlign: 'right',
            borderRadius: (t) => t.radius('md'),
            ...(props.slotProps?.paper as { sx?: object } | undefined)?.sx,
          },
        },
        listbox: {
          ...props.slotProps?.listbox,
          sx: {
            direction: 'rtl',
            textAlign: 'right',
            ...(props.slotProps?.listbox as { sx?: object } | undefined)?.sx,
          },
        },
      }}
    />
  );
}
