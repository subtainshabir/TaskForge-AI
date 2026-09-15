import { Menu, Search, Sparkles, LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import Button from "../../components/Button/Button.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import "./Header.css";

function Header({ onToggleSidebar }) {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const initial = user?.name?.trim()?.charAt(0)?.toUpperCase() || "U";

  return (
    <header className="header">
      <button
        type="button"
        className="header__menu-toggle"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation menu"
      >
        <Menu size={20} aria-hidden="true" />
      </button>

      <label className="header__search">
        <Search size={16} aria-hidden="true" />
        <input type="search" placeholder="Search your workspace" aria-label="Search" />
      </label>

      <div className="header__spacer" />

      <div className="header__actions">
        <Button variant="ai" size="sm">
          <Sparkles size={16} aria-hidden="true" />
          Ask AI
        </Button>

        {isAuthenticated ? (
          <>
            <Link to="/settings" className="header__user" title={`${user?.name} — Settings`}>
              <span className="header__avatar" aria-hidden="true">
                {initial}
              </span>
              <span className="header__user-name">{user?.name}</span>
            </Link>
            <button
              type="button"
              className="header__logout"
              onClick={handleLogout}
              aria-label="Log out"
              title="Log out"
            >
              <LogOut size={18} aria-hidden="true" />
            </button>
          </>
        ) : (
          <>
            <Button variant="ghost" size="sm" onClick={() => navigate("/login")}>
              Log in
            </Button>
            <Button variant="secondary" size="sm" onClick={() => navigate("/register")}>
              Sign up
            </Button>
          </>
        )}
      </div>
    </header>
  );
}

export default Header;