import { Link, useNavigate } from "react-router-dom";
import { clearSession, getToken } from "../api/client";

export default function NavBar() {
  const navigate = useNavigate();
  const loggedIn = Boolean(getToken());

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  if (!loggedIn) return null;

  return (
    <nav className="navbar">
      <Link to="/planning">Run Planning</Link>
      <Link to="/connection">Odoo Connection</Link>
      <button onClick={handleLogout}>Log out</button>
    </nav>
  );
}
