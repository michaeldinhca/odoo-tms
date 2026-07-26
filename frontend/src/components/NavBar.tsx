import { NavLink, useNavigate } from "react-router-dom";
import { clearSession, hasValidSession } from "../api/client";
import { Button } from "../components/ui";
import { cn } from "../components/ui/cn";
import { useCurrentUser, type PermissionFlag } from "../context/CurrentUserContext";
import { useOdooInstance } from "../context/OdooInstanceContext";
import { NavDropdown } from "./NavDropdown";

interface NavLinkDef {
  to: string;
  label: string;
  permission?: PermissionFlag;
  adminOnly?: boolean;
}

/** A top-level nav slot is either one link, or a labeled group of links
 * rendered as a dropdown (`NavDropdown`) — add new screens to an existing
 * group's `items`, or add a new `{ kind: "group", ... }` entry for an
 * unrelated cluster of screens, rather than growing the flat link list. */
type NavEntry = ({ kind: "link" } & NavLinkDef) | { kind: "group"; label: string; items: NavLinkDef[] };

// Ordered by workflow stage, not alphabetically or by permission: connect
// Odoo and configure its sync/location/fleet screens (grouped under
// "Setup", since these are visited once up front and rarely after), then
// the two day-to-day operational screens, with user administration last.
const NAV: NavEntry[] = [
  {
    kind: "group",
    label: "Setup",
    items: [
      { to: "/connection", label: "Odoo Connection", permission: "can_manage_connection" },
      { to: "/operation-types", label: "Operation Types", permission: "can_manage_operation_types" },
      { to: "/warehouses", label: "Warehouses", permission: "can_manage_warehouses" },
      { to: "/destinations", label: "Destinations", permission: "can_manage_warehouses" },
      { to: "/warehouse-routes", label: "Routes", permission: "can_manage_warehouses" },
      { to: "/vehicles", label: "Vehicles", permission: "can_manage_fleet" },
      { to: "/drivers", label: "Drivers", permission: "can_manage_fleet" },
    ],
  },
  { kind: "link", to: "/planning", label: "Run Planning", permission: "can_run_planning" },
  { kind: "link", to: "/load-planning", label: "Load Planning", permission: "can_use_load_planning" },
  { kind: "link", to: "/users", label: "Users", adminOnly: true },
];

const LINK_CLASSES = ({ isActive }: { isActive: boolean }) =>
  cn(
    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors motion-reduce:transition-none",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
    isActive ? "bg-accent/10 text-accent" : "text-text-muted hover:bg-bg hover:text-text",
  );

export default function NavBar() {
  const navigate = useNavigate();
  const { refetch: refetchOdoo } = useOdooInstance();
  const { refetch: refetchMe, isAdmin, hasPermission, loading } = useCurrentUser();
  const loggedIn = hasValidSession();

  function handleLogout() {
    clearSession();
    refetchOdoo();
    refetchMe();
    navigate("/login");
  }

  if (!loggedIn) return null;

  function isVisible(link: NavLinkDef): boolean {
    if (link.adminOnly) return isAdmin;
    if (link.permission) return hasPermission(link.permission);
    return true;
  }

  // While CurrentUserContext is still loading, show nothing rather than
  // every entry (which would just flash and disappear once permissions
  // resolve) or none (equally jarring for a fully-permitted admin). A
  // group collapses entirely if none of its items are visible; otherwise
  // it keeps only the items the current user can actually reach.
  const visibleNav: NavEntry[] = loading
    ? []
    : NAV.flatMap((entry): NavEntry[] => {
        if (entry.kind === "link") return isVisible(entry) ? [entry] : [];
        const items = entry.items.filter(isVisible);
        return items.length > 0 ? [{ ...entry, items }] : [];
      });

  return (
    <nav className="sticky top-0 z-10 flex items-center gap-1 border-b border-border bg-surface px-4 py-2 shadow-sm">
      {visibleNav.map((entry) =>
        entry.kind === "group" ? (
          <NavDropdown key={entry.label} label={entry.label} items={entry.items} />
        ) : (
          <NavLink key={entry.to} to={entry.to} className={LINK_CLASSES}>
            {entry.label}
          </NavLink>
        ),
      )}
      <NavLink to="/account" className={LINK_CLASSES}>
        Account
      </NavLink>
      <Button variant="secondary" size="sm" onClick={handleLogout} className="ml-auto">
        Log out
      </Button>
    </nav>
  );
}
