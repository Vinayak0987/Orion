// Tools · Tool Details (ViewToolDetails.jsx)
// Reusable drill-down for any tool/integration. Accepts a `tool` record
// (see toolsData.js) and an optional `onBack`. Scoped under `.tools-page`.
import { useState } from "react";
import {
  Pencil,
  ClipboardList,
  Settings,
  User,
  LineChart,
  Hexagon,
  ArrowLeft,
} from "lucide-react";
import { getTool } from "./toolsData.js";

const SUBNAV = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "configuration", label: "Configuration", icon: Settings },
  { id: "permissions", label: "Permissions", icon: User },
  { id: "usage", label: "Usage & Analytics", icon: LineChart },
  { id: "logs", label: "Logs", icon: Hexagon },
];

const CustomToolLogo = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="2" y="2" width="20" height="20" rx="6" fill="#eef1fe" />
    <path
      d="M14.8 7.2a3 3 0 0 0-3.9 3.6l-4 4a1.4 1.4 0 0 0 2 2l4-4a3 3 0 0 0 3.6-3.9l-1.8 1.8-1.6-.4-.4-1.6z"
      fill="#4f46e5"
    />
  </svg>
);

const StatusBadge = ({ status }) =>
  status === "not-configured" ? (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Not Configured</span>
  ) : (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  );

const Row = ({ label, children, last }) => (
  <div className={`td-row ${last ? "last" : ""}`}>
    <div className="td-row-label">{label}</div>
    <div className="td-row-value">{children}</div>
  </div>
);

export const ViewToolDetails = ({ tool: toolProp, toolKey = "google-drive", onBack }) => {
  const tool = toolProp || getTool(toolKey) || getTool("google-drive");
  const [tab, setTab] = useState("overview");
  const Logo = tool.Logo;
  const s = tool.stats;

  const STAT_CARDS = [
    { label: "Total Requests", value: s.totalRequests, trend: s.trends.requests, good: true },
    { label: "Success Rate", value: s.successRate, trend: s.trends.success, good: true },
    { label: "Avg Response Time", value: s.avgResponse, trend: s.trends.response, good: true },
    { label: "Errors", value: s.errors, trend: s.trends.errors, good: true },
  ];

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            {onBack && (
              <button className="td-back" onClick={onBack}>
                <ArrowLeft size={16} strokeWidth={2.4} /> Back
              </button>
            )}
            <h1>Tool Details</h1>
            <p className="tools-subtitle">View and manage tool configuration, usage, and permissions.</p>
          </div>
          <button className="tools-primary">
            <Pencil size={17} strokeWidth={2.4} /> Edit Tool
          </button>
        </div>

        <div className="td-layout">
          {/* Left column */}
          <aside className="td-side">
            <div className="td-profile card">
              <div className="td-profile-top">
                <div className="td-logo">{Logo ? <Logo /> : <CustomToolLogo />}</div>
                <StatusBadge status={tool.status} />
              </div>
              <h2 className="td-name">{tool.name}</h2>
              <p className="td-tagline">{tool.tagline}</p>
              <div className="td-tags">
                {tool.tags.map((t) => (
                  <span key={t} className="td-tag">{t}</span>
                ))}
              </div>
              <button className="tools-primary td-open">Open Tool</button>
              <button className="td-test">Test Connection</button>
            </div>

            <nav className="td-subnav card">
              {SUBNAV.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    className={`td-subnav-item ${tab === item.id ? "active" : ""}`}
                    onClick={() => setTab(item.id)}
                  >
                    <Icon size={19} strokeWidth={2} />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </aside>

          {/* Right column */}
          <div className="td-main">
            <div className="td-overview card">
              <h2 className="td-panel-title">Overview</h2>
              <p className="td-panel-sub">General information about this tool.</p>

              <Row label="Name">{tool.name}</Row>
              <Row label="Description">{tool.description}</Row>
              <Row label="Category">{tool.category}</Row>
              <Row label="Status"><StatusBadge status={tool.status} /></Row>
              <Row label="Version">{tool.version}</Row>
              <Row label="Added On">{tool.addedOn}</Row>
              <Row label="Last Used" last>{tool.lastUsed}</Row>
            </div>

            <div className="td-stats card">
              <h2 className="td-panel-title">Quick Stats (Last 30 days)</h2>
              <div className="td-stats-grid">
                {STAT_CARDS.map((c) => (
                  <div key={c.label} className="td-stat">
                    <div className="td-stat-label">{c.label}</div>
                    <div className="td-stat-value">{c.value}</div>
                    <span className="td-stat-trend">{c.trend}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
