import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import type { AuthUser } from '../types/fmms';

type CurrentUserContextValue = {
  user: AuthUser | null;
  loading: boolean;
  /** VIEWER (ناظر کل) — read-only everywhere; write controls should hide for this role. */
  isViewer: boolean;
};

const CurrentUserContext = createContext<CurrentUserContextValue>({
  user: null,
  loading: true,
  isViewer: false,
});

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void api
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<CurrentUserContextValue>(
    () => ({ user, loading, isViewer: user?.role === 'VIEWER' }),
    [user, loading],
  );

  return <CurrentUserContext.Provider value={value}>{children}</CurrentUserContext.Provider>;
}

export function useCurrentUser(): CurrentUserContextValue {
  return useContext(CurrentUserContext);
}

/** Shorthand for gating write controls: `const canEdit = useCanEdit();` */
export function useCanEdit(): boolean {
  return !useCurrentUser().isViewer;
}
