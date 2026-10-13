import { Icon } from "./icons";
import { Sidebar as DistSidebar } from "../components/layout/Sidebar.jsx";

// Map OrionDashboard route ids ↔ dist Sidebar view ids.
const TO_DIST = { command: "command-center" };
const FROM_DIST = { "command-center": "command" };

export function Sidebar({ route, onNavigate }) {
  const activeView = TO_DIST[route] || route;
  return (
    <DistSidebar
      activeView={activeView}
      viewingDetails={false}
      onNavClick={(id) => onNavigate(FROM_DIST[id] || id)}
      agentsTab="overview"
      onAgentsTabClick={() => onNavigate("agents")}
      toolsTab="overview"
      onToolsTabClick={() => onNavigate("tools")}
      settingsOpen={false}
    />
  );
}

export function Topbar({ user = "Abhishek", onLogout }) {
  const initials = user.slice(0, 2).toUpperCase();
  return (
    <header className="o-topbar">
      <div className="o-search">
        <Icon.search s={17} />
        <input placeholder="Search or type a command…" aria-label="Search" />
        <span className="o-kbd">Ctrl K</span>
      </div>
      <div className="o-topbar-spacer" />
      <button className="o-icon-btn" title="Theme" type="button"><Icon.sun s={18} /></button>
      <button className="o-icon-btn" title="Notifications" type="button">
        <Icon.bell s={18} />
        <span className="o-dot" />
      </button>
      <button className="o-user-chip" type="button" onClick={onLogout} title="Account">
        <span className="o-avatar">{initials}</span>
        <span className="o-user-name">{user}</span>
        <Icon.chevronDown s={15} />
      </button>
    </header>
  );
}

// The full shell: sidebar + (topbar over a scrolling content region).
export default function AppShell({ route, onNavigate, user, onLogout, children }) {
  return (
    <div className="orion-app" style={{ background: "#F8FAFC" }}>
      <Sidebar route={route} onNavigate={onNavigate} />
      <div className="o-main">
        <Topbar user={user} onLogout={onLogout} />
        <div className="o-scroll">{children}</div>
      </div>
    </div>
  );
}
