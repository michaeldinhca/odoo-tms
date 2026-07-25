import { NavLink, useNavigate } from "react-router-dom";
import { clearSession, hasValidSession } from "../api/client";
import { Button } from "../components/ui";
import { cn } from "../components/ui/cn";
import { useOdooInstance } from "../context/OdooInstanceContext";

const LINKS = [
  { to: "/planning", label: "Run Planning" },
  { to: "/load-planning", label: "Load Planning" },
  { to: "/connection", label: "Odoo Connection" },
  { to: "/operation-types", label: "Operation Types" },
  { to: "/warehouses", label: "Warehouses" },
  { to: "/vehicles", label: "Vehicles" },
  { to: "/drivers", label: "Drivers" },
];

export default function NavBar() {
  const navigate = useNavigate();
  const { refetch } = useOdooInstance();
  const loggedIn = hasValidSession();

  function handleLogout() {
    clearSession();
    refetch();
    navigate("/login");
  }

  if (!loggedIn) return null;

  return (
    <nav className="sticky top-0 z-10 flex items-center gap-1 border-b border-border bg-surface px-4 py-2 shadow-sm">
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors motion-reduce:transition-none",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
              isActive ? "bg-accent/10 text-accent" : "text-text-muted hover:bg-bg hover:text-text",
            )
          }
        >
          {link.label}
        </NavLink>
      ))}
      <Button variant="secondary" size="sm" onClick={handleLogout} className="ml-auto">
        Log out
      </Button>
    </nav>
  );
}
