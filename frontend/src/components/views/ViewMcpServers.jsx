// Tools · MCP Servers (ViewMcpServers.jsx)
// Renders in the Tools section "MCP Servers" sub-tab. Indigo primary buttons
// (consistent with the rest of the app). Scoped under `.tools-page`.
import { Plus, Search, ChevronDown, Server, ShieldCheck, MoreVertical, Folder, Shield } from "lucide-react";
import { NotionLogo, BraveLogo } from "./brandLogos.jsx";

const SERVERS = [
  {
    name: "Filesystem MCP",
    desc: "Access and manage local files and directories.",
    versions: ["v1.0.3", "v1.1"],
    icon: <Folder size={30} strokeWidth={2} color="#2563eb" fill="#bfdbfe" />,
    iconClass: "mcp-ic-blue",
    status: "active",
    last: "5 min ago",
  },
  {
    name: "Notion MCP",
    desc: "Connect to Notion workspace via MCP.",
    versions: ["v1.4.6", "v1.2.0"],
    icon: <NotionLogo />,
    iconClass: "mcp-ic-plain",
    status: "active",
    last: "12 min ago",
  },
  {
    name: "Brave Search MCP",
    desc: "Web search using Brave Search API.",
    versions: ["v0.8.1", "v0.9.1"],
    icon: <BraveLogo />,
    iconClass: "mcp-ic-plain",
    status: "inactive",
    last: "1 day ago",
  },
];

const StatusBadge = ({ status }) =>
  status === "inactive" ? (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Inactive</span>
  ) : (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  );

export const ViewMcpServers = () => (
  <div className="tools-page">
    <section className="tools-content">
      {/* Header */}
      <div className="tools-head">
        <div>
          <h1>MCP Servers</h1>
          <p className="tools-subtitle">Manage MCP connections to extend Orion's capabilities.</p>
        </div>
        <button className="tools-primary">
          <Plus size={18} strokeWidth={2.6} /> Add MCP Server
        </button>
      </div>

      {/* Stat cards */}
      <div className="tools-stats">
        <div className="tools-stat card">
          <div className="tools-stat-ic indigo"><Server size={20} strokeWidth={2} /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Total Servers</div>
            <div className="tools-stat-value">3</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic green"><span className="tools-stat-dot green" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Active</div>
            <div className="tools-stat-value">2</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic red"><span className="tools-stat-dot red" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Inactive</div>
            <div className="tools-stat-value">1</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic green"><ShieldCheck size={20} strokeWidth={2} color="#16a34a" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Success Rate</div>
            <div className="tools-stat-value">98%</div>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="tools-toolbar mcp-toolbar">
        <div className="tools-search">
          <Search size={18} strokeWidth={2} className="tools-search-icon" />
          <input placeholder="Search Servers..." />
        </div>
        <button className="tools-select">
          All Status <ChevronDown size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Server list */}
      <div className="mcp-list">
        {SERVERS.map((s) => (
          <div key={s.name} className="mcp-card card">
            <div className={`mcp-icon ${s.iconClass}`}>{s.icon}</div>

            <div className="mcp-info">
              <h3 className="mcp-name">{s.name}</h3>
              <p className="mcp-desc">{s.desc}</p>
              <div className="mcp-versions">
                {s.versions.map((v) => (
                  <span key={v} className="mcp-version">{v}</span>
                ))}
              </div>
            </div>

            <div className="mcp-status">
              <StatusBadge status={s.status} />
              <span className="mcp-last">{s.last}</span>
            </div>

            <div className="mcp-actions">
              <button className="mcp-test-btn">Test</button>
              <button className="tools-more-btn" aria-label="More actions">
                <MoreVertical size={16} strokeWidth={2} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Configuration Help */}
      <h2 className="mcp-help-title">Configuration Help</h2>
      <div className="mcp-help card">
        <div className="mcp-help-icon"><Shield size={22} strokeWidth={2} fill="#bfdbfe" /></div>
        <div className="mcp-help-body">
          <h3>Need help setting up MCP servers?</h3>
          <p>Check out our documentation for step-by-step guides.</p>
        </div>
        <button className="tools-primary mcp-help-btn">View Documentation</button>
      </div>
    </section>
  </div>
);
