import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  StickyNote,
  Search,
  Sparkles,
  BarChart3,
  Settings,
} from "lucide-react";
import "./Sidebar.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderKanban },
  { to: "/tasks", label: "Tasks", icon: CheckSquare },
  { to: "/notes", label: "Notes", icon: StickyNote },
  { to: "/search", label: "Search", icon: Search },
  { to: "/chat", label: "AI Chat", icon: Sparkles },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

function Sidebar({ open, onNavigate }) {
  return (
    <>
      <aside className="sidebar" data-open={open} aria-label="Primary">
        <div className="sidebar__brand">
          <span className="sidebar__brand-mark" aria-hidden="true">
            TF
          </span>
          <span className="sidebar__brand-name">TaskForge AI</span>
        </div>
        <nav className="sidebar__nav">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onNavigate}
              className="sidebar__link"
            >
              <span className="sidebar__link-icon">
                <Icon size={18} aria-hidden="true" />
              </span>
              <span className="sidebar__link-label">{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div
        className="sidebar-backdrop"
        data-open={open}
        onClick={onNavigate}
        aria-hidden="true"
      />
    </>
  );
}

export default Sidebar;