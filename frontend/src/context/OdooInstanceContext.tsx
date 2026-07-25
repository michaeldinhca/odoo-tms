import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getCredential, getTenantId, hasValidSession } from "../api/client";
import type { OdooCredential } from "../api/types";

interface OdooInstanceContextValue {
  instance: OdooCredential | null;
  isActive: boolean;
  loading: boolean;
  refetch: () => void;
}

const OdooInstanceContext = createContext<OdooInstanceContextValue>({
  instance: null,
  isActive: false,
  loading: true,
  refetch: () => {},
});

export function OdooInstanceProvider({ children }: { children: ReactNode }) {
  const [instance, setInstance] = useState<OdooCredential | null>(null);
  const [loading, setLoading] = useState(true);

  const refetch = useCallback(() => {
    const tenantId = getTenantId();
    if (!tenantId || !hasValidSession()) {
      setInstance(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getCredential(tenantId)
      .then(setInstance)
      .catch(() => setInstance(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return (
    <OdooInstanceContext.Provider
      value={{ instance, isActive: instance?.state === "active", loading, refetch }}
    >
      {children}
    </OdooInstanceContext.Provider>
  );
}

/** Whether the tenant has a saved-and-activated Odoo connection, plus the
 * connection record itself. `refetch()` should be called after any action
 * that might change connection state (save/test/select-company/login/
 * logout) — see ConnectionPage and LoginPage/NavBar for call sites. */
export function useOdooInstance(): OdooInstanceContextValue {
  return useContext(OdooInstanceContext);
}
