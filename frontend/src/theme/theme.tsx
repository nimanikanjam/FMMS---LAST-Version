import createCache from '@emotion/cache';
import { CacheProvider } from '@emotion/react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import { CssBaseline, GlobalStyles } from '@mui/material';
import {
  createTheme,
  ThemeProvider as MuiThemeProvider,
  type Theme,
} from '@mui/material/styles';
import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { radii } from './radii';

export { radii, radiusPx } from './radii';
export type { Radii, RadiusToken } from './radii';

export type ColorMode = 'light' | 'dark';

const COLOR_MODE_KEY = 'fmms.colorMode';

const cacheRtl = createCache({
  key: 'fmms-rtl',
});

type ColorModeContextValue = {
  mode: ColorMode;
  toggleColorMode: () => void;
  setColorMode: (mode: ColorMode) => void;
};

export const ColorModeContext = createContext<ColorModeContextValue>({
  mode: 'light',
  toggleColorMode: () => undefined,
  setColorMode: () => undefined,
});

export function useColorMode(): ColorModeContextValue {
  return useContext(ColorModeContext);
}

function readStoredMode(): ColorMode {
  try {
    const stored = localStorage.getItem(COLOR_MODE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
  } catch {
    // ignore
  }
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

function attachRadius(theme: Theme): Theme {
  theme.radius = (token) => `${theme.radii[token]}px`;
  return theme;
}

export function createAppTheme(mode: ColorMode): Theme {
  const isDark = mode === 'dark';

  const theme = createTheme({
    direction: 'rtl',
    shape: {
      borderRadius: radii.md,
    },
    radii,
    palette: {
      mode,
      primary: isDark
        ? {
            main: '#2EAD74',
            light: '#1B3D30',
            dark: '#6EE7B0',
            contrastText: '#06140E',
          }
        : {
            main: '#0F6B4C',
            light: '#D8F0E5',
            dark: '#0A4D37',
            contrastText: '#FFFFFF',
          },
      secondary: isDark
        ? {
            main: '#E88978',
            light: '#3F2824',
            dark: '#F4B5A8',
            contrastText: '#1A0C0A',
          }
        : {
            main: '#C4573D',
            light: '#F8E9E5',
            dark: '#8E3428',
            contrastText: '#FFFFFF',
          },
      success: isDark
        ? {
            main: '#3DCF8E',
            light: '#163528',
            dark: '#7EEAB5',
            contrastText: '#06140E',
          }
        : {
            main: '#248A57',
            light: '#D7F3E4',
            dark: '#155F3D',
            contrastText: '#FFFFFF',
          },
      warning: isDark
        ? {
            main: '#E0A03A',
            light: '#3A2E16',
            dark: '#F5C86A',
            contrastText: '#1A1406',
          }
        : {
            main: '#D28A20',
            light: '#FFF1D6',
            dark: '#9A6410',
            contrastText: '#FFFFFF',
          },
      error: isDark
        ? {
            main: '#E05A4E',
            light: '#3A1C19',
            dark: '#F09088',
            contrastText: '#1A0A08',
          }
        : {
            main: '#C94132',
            light: '#FDE4E1',
            dark: '#9F2F27',
            contrastText: '#FFFFFF',
          },
      info: isDark
        ? {
            main: '#4A9BC7',
            light: '#1A3040',
            dark: '#7EC4E8',
            contrastText: '#0A141A',
          }
        : {
            main: '#2D6F95',
            light: '#DCEEF8',
            dark: '#1F5070',
            contrastText: '#FFFFFF',
          },
      background: isDark
        ? {
            default: '#0C1210',
            paper: '#151C18',
          }
        : {
            default: '#F3F6F4',
            paper: '#FFFFFF',
          },
      text: isDark
        ? {
            primary: '#E6EFE9',
            secondary: '#8FA39A',
            disabled: '#5A6B63',
          }
        : {
            primary: '#17231D',
            secondary: '#5A6B63',
            disabled: '#9AABA3',
          },
      divider: isDark ? 'rgba(154, 171, 163, 0.16)' : '#D5E0DA',
      action: isDark
        ? {
            hover: 'rgba(46, 173, 116, 0.10)',
            selected: 'rgba(46, 173, 116, 0.16)',
            disabled: 'rgba(230, 239, 233, 0.30)',
            disabledBackground: '#1A2420',
            focus: 'rgba(46, 173, 116, 0.22)',
          }
        : {
            hover: 'rgba(15, 107, 76, 0.08)',
            selected: 'rgba(15, 107, 76, 0.12)',
            disabled: 'rgba(23, 35, 29, 0.30)',
            disabledBackground: '#EAF0EC',
            focus: 'rgba(15, 107, 76, 0.18)',
          },
    },
    typography: {
      fontFamily:
        'Vazirmatn, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      h1: {
        fontWeight: 800,
        fontSize: '1.55rem',
        lineHeight: 1.3,
        letterSpacing: '-0.02em',
      },
      h2: {
        fontWeight: 700,
        fontSize: '1.30rem',
        lineHeight: 1.35,
        letterSpacing: '-0.01em',
      },
      h3: {
        fontWeight: 700,
        fontSize: '1.10rem',
        lineHeight: 1.45,
      },
      h4: {
        fontWeight: 700,
        fontSize: '1rem',
        lineHeight: 1.5,
      },
      h5: {
        fontWeight: 600,
        fontSize: '.95rem',
        lineHeight: 1.5,
      },
      h6: {
        fontWeight: 600,
        fontSize: '.90rem',
        lineHeight: 1.5,
      },
      body1: {
        fontSize: '.95rem',
        lineHeight: 1.7,
      },
      body2: {
        fontSize: '.875rem',
        lineHeight: 1.65,
      },
      button: {
        fontWeight: 700,
        textTransform: 'none',
      },
      subtitle1: {
        fontWeight: 700,
        fontSize: '.95rem',
      },
      subtitle2: {
        fontWeight: 600,
        fontSize: '.85rem',
      },
      caption: {
        fontSize: '0.78rem',
        lineHeight: 1.5,
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            transition: 'background-color .25s ease, color .2s ease',
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          root: ({ theme: t }) => ({
            borderRadius: t.radii.md,
            textTransform: 'none',
            minHeight: 38,
            fontWeight: 700,
            paddingInline: 18,
            transition: 'all .2s ease',
          }),
          containedPrimary: ({ theme: t }) =>
            t.palette.mode === 'dark'
              ? {
                  background: 'linear-gradient(135deg, #3DCF8E 0%, #2EAD74 55%, #1E8A5A 100%)',
                  color: '#06140E',
                  boxShadow: '0 6px 16px rgba(46, 173, 116, 0.28)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #2EAD74 0%, #1E8A5A 100%)',
                    boxShadow: '0 10px 22px rgba(46, 173, 116, 0.36)',
                  },
                  '&.Mui-disabled': {
                    background: 'rgba(46, 173, 116, 0.14)',
                    color: 'rgba(61, 207, 142, 0.55)',
                    boxShadow: 'none',
                  },
                }
              : {
                  background: 'linear-gradient(135deg, #12865D 0%, #0F6B4C 55%, #0A4D37 100%)',
                  boxShadow: '0 6px 16px rgba(15, 107, 76, 0.26)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #0F6B4C 0%, #0A4D37 100%)',
                    boxShadow: '0 10px 22px rgba(15, 107, 76, 0.32)',
                  },
                  '&.Mui-disabled': {
                    background: 'rgba(15, 107, 76, 0.12)',
                    color: 'rgba(15, 107, 76, 0.55)',
                    boxShadow: 'none',
                  },
                },
          containedSecondary: ({ theme: t }) =>
            t.palette.mode === 'dark'
              ? {
                  background: 'linear-gradient(135deg, #F0A090 0%, #E88978 55%, #C4573D 100%)',
                  color: '#1A0C0A',
                  boxShadow: '0 6px 16px rgba(224, 122, 106, 0.28)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #E88978 0%, #C4573D 100%)',
                    boxShadow: '0 10px 22px rgba(224, 122, 106, 0.36)',
                  },
                  '&.Mui-disabled': {
                    background: 'rgba(224, 122, 106, 0.14)',
                    color: 'rgba(240, 160, 144, 0.55)',
                    boxShadow: 'none',
                  },
                }
              : {
                  background: 'linear-gradient(135deg, #D46B55 0%, #C4573D 55%, #8E3428 100%)',
                  boxShadow: '0 6px 16px rgba(196, 92, 74, 0.26)',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #C4573D 0%, #8E3428 100%)',
                    boxShadow: '0 10px 22px rgba(196, 92, 74, 0.32)',
                  },
                  '&.Mui-disabled': {
                    background: 'rgba(196, 92, 74, 0.12)',
                    color: 'rgba(196, 92, 74, 0.55)',
                    boxShadow: 'none',
                  },
                },
          outlinedPrimary: ({ theme: t }) => ({
            borderColor: t.palette.primary.main,
            color: t.palette.primary.main,
            '&:hover': {
              borderColor: t.palette.primary.dark,
              backgroundColor: t.palette.action.hover,
            },
          }),
          outlinedSecondary: ({ theme: t }) => ({
            borderColor: t.palette.secondary.main,
            color: t.palette.secondary.dark,
            '&:hover': {
              borderColor: t.palette.secondary.dark,
              backgroundColor:
                t.palette.mode === 'dark' ? 'rgba(224, 122, 106, 0.12)' : 'rgba(196, 92, 74, 0.08)',
            },
          }),
        },
      },
      MuiTextField: {
        defaultProps: {
          size: 'small',
          variant: 'outlined',
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          root: {
            right: 14,
            left: 'auto',
            transformOrigin: 'top right',
            textAlign: 'right',
          },
        },
      },
      MuiFormControl: {
        defaultProps: { size: 'small' },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            borderRadius: t.radii.md,
            backgroundColor: t.palette.background.paper,
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: t.palette.primary.main,
              borderWidth: 2,
            },
          }),
          notchedOutline: ({ theme: t }) => ({
            textAlign: 'right',
            borderColor: t.palette.divider,
          }),
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 999,
            fontWeight: 800,
            paddingInline: 6,
            height: 28,
          },
          colorPrimary: ({ theme: t }) => ({
            backgroundColor:
              t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.18)' : 'rgba(15, 107, 76, 0.12)',
            color: t.palette.mode === 'dark' ? t.palette.primary.dark : t.palette.primary.dark,
            border: `1px solid ${
              t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.28)' : 'rgba(15, 107, 76, 0.22)'
            }`,
          }),
          colorSecondary: ({ theme: t }) => ({
            backgroundColor:
              t.palette.mode === 'dark' ? 'rgba(224, 122, 106, 0.18)' : 'rgba(196, 92, 74, 0.14)',
            color: t.palette.secondary.dark,
            border: `1px solid ${
              t.palette.mode === 'dark' ? 'rgba(224, 122, 106, 0.28)' : 'rgba(196, 92, 74, 0.28)'
            }`,
          }),
        },
      },
      MuiTab: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            fontWeight: 700,
            '&.Mui-selected': {
              color: t.palette.primary.main,
            },
          }),
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: ({ theme: t }) => ({
            backgroundColor: t.palette.secondary.main,
            height: 3,
            borderRadius: 999,
          }),
        },
      },
      MuiPagination: {
        defaultProps: {
          color: 'primary',
          shape: 'rounded',
          variant: 'outlined',
        },
      },
      MuiPaginationItem: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            borderRadius: t.radius('sm'),
            fontWeight: 800,
          }),
          outlined: ({ theme: t }) => ({
            borderColor: t.palette.divider,
          }),
          outlinedPrimary: ({ theme: t }) => ({
            '&.Mui-selected': {
              backgroundColor: t.palette.primary.main,
              borderColor: t.palette.primary.main,
              color: t.palette.primary.contrastText,
              '&:hover': {
                backgroundColor: t.palette.primary.dark,
                borderColor: t.palette.primary.dark,
              },
            },
          }),
        },
      },
      MuiDialog: {
        defaultProps: {
          disableScrollLock: true,
        },
        styleOverrides: {
          root: ({ theme: t }) => ({
            '& > .MuiBackdrop-root': {
              backgroundColor:
                t.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.62)' : 'rgba(23, 35, 29, 0.42)',
              backdropFilter: 'blur(0.5px)',
              WebkitBackdropFilter: 'blur(0.5px)',
            },
          }),
          paper: ({ theme: t }) => ({
            borderRadius: t.radii.md,
            boxShadow:
              t.palette.mode === 'dark'
                ? '0 18px 40px rgba(0, 0, 0, 0.45)'
                : '0 18px 40px rgba(15, 107, 76, 0.16)',
            maxHeight: '85vh',
            backgroundImage: 'none',
          }),
        },
      },
      MuiModal: {
        defaultProps: {
          disableScrollLock: true,
        },
      },
      MuiPopover: {
        defaultProps: {
          disableScrollLock: true,
        },
      },
      MuiMenu: {
        defaultProps: {
          disableScrollLock: true,
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            backgroundImage: 'none',
            border: `1px solid ${
              t.palette.mode === 'dark' ? 'rgba(154, 171, 163, 0.12)' : 'rgba(15, 107, 76, 0.10)'
            }`,
            boxShadow:
              t.palette.mode === 'dark'
                ? '0 8px 24px rgba(0, 0, 0, 0.35)'
                : '0 8px 24px rgba(15, 107, 76, 0.05)',
          }),
          rounded: ({ theme: t }) => ({
            borderRadius: t.radii.md,
          }),
          elevation1: ({ theme: t }) => ({
            boxShadow:
              t.palette.mode === 'dark'
                ? '0 6px 18px rgba(0, 0, 0, 0.4)'
                : '0 6px 18px rgba(15, 107, 76, 0.07)',
          }),
        },
      },
      MuiCard: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            borderRadius: t.radii.lg,
            border: `1px solid ${
              t.palette.mode === 'dark' ? 'rgba(154, 171, 163, 0.12)' : 'rgba(15, 107, 76, 0.10)'
            }`,
            boxShadow:
              t.palette.mode === 'dark'
                ? '0 10px 28px rgba(0, 0, 0, 0.35)'
                : '0 10px 28px rgba(15, 107, 76, 0.06)',
            backgroundImage:
              t.palette.mode === 'dark'
                ? 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%)'
                : 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, #ffffff 100%)',
            transition: 'box-shadow .2s ease, transform .15s ease, background-color .2s ease',
          }),
        },
      },
      MuiTable: {
        defaultProps: {
          dir: 'rtl !important',
        },
        styleOverrides: {
          root: { direction: 'rtl' },
        },
      },
      MuiTableContainer: {
        defaultProps: {
          dir: 'inherit',
        },
        styleOverrides: {
          root: { direction: 'rtl' },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            borderBottom: `1px solid ${t.palette.divider}`,
            textAlign: 'right',
            paddingTop: 14,
            paddingBottom: 14,
          }),
          head: ({ theme: t }) => ({
            backgroundColor:
              t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.10)' : '#EAF5EF',
            color: t.palette.mode === 'dark' ? t.palette.primary.dark : '#1F3D32',
            fontWeight: 800,
            borderBottom: `1px solid ${t.palette.divider}`,
          }),
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            transition: '.15s',
            '&:nth-of-type(even) td': {
              backgroundColor:
                t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.04)' : 'rgba(15, 107, 76, 0.03)',
            },
            '&:hover td': {
              backgroundColor:
                t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.09)' : 'rgba(15, 107, 76, 0.07)',
            },
          }),
        },
      },
      MuiTableSortLabel: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            color: t.palette.text.primary,
            fontWeight: 700,
            '&:hover': {
              color: t.palette.primary.main,
              '& .MuiTableSortLabel-icon': {
                opacity: 0.45,
                color: t.palette.text.secondary,
              },
            },
            '&.Mui-active': {
              color: t.palette.primary.main,
              fontWeight: 800,
              '& .MuiTableSortLabel-icon': {
                opacity: 1,
                color: t.palette.primary.main,
              },
            },
          }),
        },
      },
      MuiAlert: {
        defaultProps: {
          iconMapping: {
            success: createElement(CheckCircleIcon, { fontSize: 'inherit' }),
            error: createElement(ErrorIcon, { fontSize: 'inherit' }),
            warning: createElement(WarningIcon, { fontSize: 'inherit' }),
          },
        },
        styleOverrides: {
          standardInfo: ({ theme: t }) => ({
            backgroundColor: t.palette.info.light,
            color: t.palette.info.dark,
            border: `1px solid ${t.palette.info.main}33`,
            '& .MuiAlert-icon': { color: t.palette.info.main },
          }),
          standardError: ({ theme: t }) => ({
            backgroundColor: t.palette.error.light,
            color: t.palette.error.dark,
            border: `1px solid ${t.palette.error.main}40`,
            '& .MuiAlert-icon': { color: t.palette.error.main },
          }),
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: ({ theme: t }) => ({
            backgroundImage: 'none',
            backgroundColor:
              t.palette.mode === 'dark' ? 'rgba(21, 28, 24, 0.88)' : 'rgba(255, 255, 255, 0.86)',
            color: t.palette.text.primary,
          }),
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: ({ theme: t }) => ({
            backgroundColor: t.palette.mode === 'dark' ? '#1F2A24' : '#1F3D32',
            fontWeight: 700,
            fontSize: '0.78rem',
          }),
        },
      },
    },
  });

  return attachRadius(theme);
}

/** Default light theme (backward compatible export). */
export const theme = createAppTheme('light');

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ColorMode>(() =>
    typeof window === 'undefined' ? 'light' : readStoredMode(),
  );

  const setColorMode = useCallback((next: ColorMode) => {
    setModeState(next);
    try {
      localStorage.setItem(COLOR_MODE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  const toggleColorMode = useCallback(() => {
    setModeState((prev) => {
      const next: ColorMode = prev === 'light' ? 'dark' : 'light';
      try {
        localStorage.setItem(COLOR_MODE_KEY, next);
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const muiTheme = useMemo(() => createAppTheme(mode), [mode]);

  useEffect(() => {
    document.documentElement.setAttribute('data-color-mode', mode);
    document.documentElement.style.colorScheme = mode;
  }, [mode]);

  const ctx = useMemo(
    () => ({ mode, toggleColorMode, setColorMode }),
    [mode, toggleColorMode, setColorMode],
  );

  return (
    <CacheProvider value={cacheRtl}>
      <ColorModeContext.Provider value={ctx}>
        <MuiThemeProvider theme={muiTheme}>
          <CssBaseline />
          <GlobalStyles
            styles={(t) => ({
              ':root': {
                '--palette-primary-mainChannel':
                  t.palette.mode === 'dark' ? '46 173 116' : '15 107 76',
                '--palette-secondary-mainChannel':
                  t.palette.mode === 'dark' ? '232 137 120' : '196 87 61',
              },
              html: {
                direction: 'rtl',
              },
              body: {
                margin: 0,
                direction: 'rtl',
                background: t.palette.background.default,
                color: t.palette.text.primary,
                fontFamily: t.typography.fontFamily,
                transition: 'background-color .25s ease, color .2s ease',
              },
              '*::-webkit-scrollbar': {
                width: 10,
                height: 10,
              },
              '*::-webkit-scrollbar-track': {
                background: 'transparent',
              },
              '*::-webkit-scrollbar-thumb': {
                background:
                  t.palette.mode === 'dark' ? 'rgba(154, 171, 163, 0.28)' : 'rgba(15, 107, 76, 0.28)',
                borderRadius: 999,
                border: '2px solid transparent',
                backgroundClip: 'padding-box',
              },
              '*::-webkit-scrollbar-thumb:hover': {
                background: t.palette.primary.main,
              },
              '::selection': {
                background:
                  t.palette.mode === 'dark' ? 'rgba(46, 173, 116, 0.35)' : 'rgba(15, 107, 76, 0.22)',
                color: t.palette.text.primary,
              },
            })}
          />
          <div dir="rtl">{children}</div>
        </MuiThemeProvider>
      </ColorModeContext.Provider>
    </CacheProvider>
  );
}
