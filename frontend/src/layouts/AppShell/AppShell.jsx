import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "../Sidebar/Sidebar.jsx";
import Header from "../Header/Header.jsx";
import "./AppShell.css";

function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <Sidebar open={mobileNavOpen} onNavigate={() => setMobileNavOpen(false)} />
      <div className="app-shell__main">
        <Header onToggleSidebar={() => setMobileNavOpen((open) => !open)} />
        <main id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AppShell;