import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { useCurrentUser, type PermissionFlag } from "../context/CurrentUserContext";

interface RequirePermissionProps {
  /** One of the six can_* flags, or several — an array means "any one of
   * these is enough" (used by the combined Warehouses & Operation Types
   * page, reachable with either can_manage_warehouses or
   * can_manage_operation_types; the page itself hides whichever section
   * the current user actually lacks). Omit and pass `adminOnly` instead
   * for the Users page's hard role gate. */
  permission?: PermissionFlag | PermissionFlag[];
  /** Users page only — `role`, not a boolean, is the gate there (see
   * DECISIONS.md "Role vs. boolean permissions"). */
  adminOnly?: boolean;
  children: ReactElement;
}

/** Route guard for a specific permission (or, with `adminOnly`, the
 * Users page). Waits for `CurrentUserContext` to finish loading before
 * deciding anything — redirecting while the fetch is still in flight
 * would bounce a permitted user; rendering the children before knowing
 * would flash gated content at one who isn't permitted. */
export default function RequirePermission({
  permission,
  adminOnly,
  children,
}: RequirePermissionProps) {
  const { loading, isAdmin, hasPermission } = useCurrentUser();

  if (loading) return null;

  const allowed = adminOnly
    ? isAdmin
    : Array.isArray(permission)
      ? permission.some(hasPermission)
      : permission
        ? hasPermission(permission)
        : true;
  if (!allowed) return <Navigate to="/planning" replace />;

  return children;
}
