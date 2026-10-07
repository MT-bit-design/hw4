import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/products", label: "Products" },
  { to: "/about", label: "About Us" },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const close = () => setOpen(false);

  async function handleLogout() {
    close();
    await logout();
    navigate("/");
  }

  return (
    <header className="nav">
      <div className="nav-inner container">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-mark">CC</span>
          <span>Campus Customs</span>
        </Link>

        <button
          className="nav-toggle"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          ☰
        </button>

        <nav className={`nav-links ${open ? "open" : ""}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          {loading ? null : user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name}</span>
              <button className="btn btn-light btn-sm" onClick={handleLogout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Log in
              </NavLink>
              <NavLink to="/signup" className="btn btn-light btn-sm" onClick={close}>
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
