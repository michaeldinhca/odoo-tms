import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getMe, hasValidSession } from "../api/client";
import type { User } from "../api/types";

export type PermissionFlag =
  | "can_manage_connection"
  | "can_manage_warehouses"
  | "can_manage_operation_types"
  | "can_manage_fleet"
  | "can_run_planning"
  | "can_use_load_planning";

interface CurrentUserContextValue {
  user: User | null;
  isAdmin: boolean;
  loading: boolean;
  hasPermission: (flag: PermissionFlag) => boolean;
  refetch: () => void;
}

const CurrentUserContext = createContext<CurrentUserContextValue>({
  user: null,
  isAdmin: false,
  loading: true,
  hasPermission: () => false,
  refetch: () => {},
});

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(() => {
    if (!hasValidSession()) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  function hasPermission(flag: PermissionFlag): boolean {
    return user?.[flag] ?? false;
  }

  return (
    <CurrentUserContext.Provider
      value={{ user, isAdmin: user?.role === "admin", loading, hasPermission, refetch }}
    >
      {children}
    </CurrentUserContext.Provider>
  );
}

/** The logged-in user's own role/permissions, fetched from `/auth/me` —
 * not decoded from the JWT, since a permission change should be reflected
 * as soon as this refetches, not only after the (up to 7-day) token
 * eventually expires (same reasoning as the backend's `get_current_user`,
 * see deps.py). `refetch()` should be called after login/logout and after
 * any change made on the Users page to the *current* user (self-edit). */
export function useCurrentUser(): CurrentUserContextValue {
  return useContext(CurrentUserContext);
}
