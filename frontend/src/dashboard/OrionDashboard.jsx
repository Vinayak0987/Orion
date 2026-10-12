import { useState } from "react";

import "./orion.css";
import AppShell from "./AppShell";
import DashboardScreen from "./screens/DashboardScreen";
import CommandCenterScreen from "./screens/CommandCenterScreen";
import MissionsScreen from "./screens/MissionsScreen";
import MissionDetailsScreen from "./screens/MissionDetailsScreen";
import ApprovalsScreen from "./screens/ApprovalsScreen";
import NotificationsScreen from "./screens/NotificationsScreen";

// Simple placeholder for the Workspace nav items that don't have a designed
// screen yet — keeps navigation whole without inventing UI.
function Placeholder({ title }) {
  return (
    <div className="o-fade">
      <div className="o-page-head"><h1>{title}</h1><p>This workspace section is coming soon.</p></div>
      <div className="o-card" style={{ display: "grid", placeItems: "center", minHeight: 260, color: "var(--o-text-3)" }}>
        {title} view — not yet designed.
      </div>
    </div>
  );
}

/**
 * OrionDashboard — the self-contained product UI (six designed screens + shell).
 *
 * Holds its own route state so it can be mounted anywhere (its own route, a
 * preview page, or Storybook-style) without touching the existing generation
 * dashboard. `user` and `onLogout` are optional wiring points.
 */
export default function OrionDashboard({ user = "Abhishek", onLogout }) {
  const [route, setRoute] = useState("dashboard");
  // `missions` list ↔ `mission-details` drill-down is local sub-state.
  const [inMissionDetails, setInMissionDetails] = useState(false);

  function navigate(next) {
    setInMissionDetails(false);
    setRoute(next);
  }

  let screen;
  if (route === "dashboard") screen = <DashboardScreen user={user} />;
  else if (route === "command") screen = <CommandCenterScreen />;
  else if (route === "missions")
    screen = inMissionDetails
      ? <MissionDetailsScreen onBack={() => setInMissionDetails(false)} />
      : <MissionsScreen onOpenMission={() => setInMissionDetails(true)} />;
  else if (route === "approvals") screen = <ApprovalsScreen />;
  else if (route === "notifications") screen = <NotificationsScreen />;
  else screen = <Placeholder title={route.charAt(0).toUpperCase() + route.slice(1)} />;

  return (
    <AppShell route={route} onNavigate={navigate} user={user} onLogout={onLogout}>
      {screen}
    </AppShell>
  );
}
