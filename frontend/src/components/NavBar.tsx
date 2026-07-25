import { Link, useNavigate } from "react-router-dom";
import { clearSession, hasValidSession } from "../api/client";
import { useOdooInstance } from "../context/OdooInstanceContext";

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
    <nav className="navbar">
      <Link to="/planning">Run Planning</Link>
      <Link to="/connection">Odoo Connection</Link>
      <Link to="/operation-types">Operation Types</Link>
      <Link to="/warehouses">Warehouses</Link>
      <Link to="/vehicles">Vehicles</Link>
      <Link to="/drivers">Drivers</Link>
      <button onClick={handleLogout}>Log out</button>
    </nav>
  );
}
