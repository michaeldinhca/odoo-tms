import { NavLink, useNavigate } from "react-router-dom";
import { clearSession, hasValidSession } from "../api/client";
import { Button } from "../components/ui";
import { cn } from "../components/ui/cn";
import { useCurrentUser, type PermissionFlag } from "../context/CurrentUserContext";
import { useOdooInstance } from "../context/OdooInstanceContext";

interface NavLinkDef {
  to: string;
  label: string;
  permission?: PermissionFlag;
  adminOnly?: boolean;
}

const LINKS: NavLinkDef[] = [
  { to: "/planning", label: "Run Planning", permission: "can_run_planning" },
  { to: "/load-planning", label: "Load Planning", permission: "can_use_load_planning" },
  { to: "/connection", label: "Odoo Connection", permission: "can_manage_connection" },
  { to: "/operation-types", label: "Operation Types", permission: "can_manage_operation_types" },
  { to: "/warehouses", label: "Warehouses", permission: "can_manage_warehouses" },
  { to: "/destinations", label: "Destinations", permission: "can_manage_warehouses" },
  { to: "/vehicles", label: "Vehicles", permission: "can_manage_fleet" },
  { to: "/drivers", label: "Drivers", permission: "can_manage_fleet" },
  { to: "/users", label: "Users", adminOnly: true },
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

  // While CurrentUserContext is still loading, show nothing rather than
  // every link (which would just flash and disappear once permissions
  // resolve) or no links (equally jarring for a fully-permitted admin).
  const visibleLinks = loading
    ? []
    : LINKS.filter((link) => {
        if (link.adminOnly) return isAdmin;
        if (link.permission) return hasPermission(link.permission);
        return true;
      });

  return (
    <nav className="sticky top-0 z-10 flex items-center gap-1 border-b border-border bg-surface px-4 py-2 shadow-sm">
      {visibleLinks.map((link) => (
        <NavLink key={link.to} to={link.to} className={LINK_CLASSES}>
          {link.label}
        </NavLink>
      ))}
      <NavLink to="/account" className={LINK_CLASSES}>
        Account
      </NavLink>
      <Button variant="secondary" size="sm" onClick={handleLogout} className="ml-auto">
        Log out
      </Button>
    </nav>
  );
}
