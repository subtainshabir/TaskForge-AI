import { Menu, Search, Sparkles } from "lucide-react";
import Button from "../../components/Button/Button.jsx";
import "./Header.css";

function Header({ onToggleSidebar }) {
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
        <span className="header__avatar" aria-hidden="true">
          U
        </span>
      </div>
    </header>
  );
}

export default Header;