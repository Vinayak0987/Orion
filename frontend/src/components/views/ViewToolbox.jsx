// Tools · Toolbox Overview — built to match the reference mockup exactly.
// Renders in the Tools section "Overview" sub-tab. Black primary buttons.
// All styling is scoped under the `.tools-page` wrapper (see index.css).
import { useState } from "react";
import { Plus, Search, ChevronDown, Settings, Wrench, MoreVertical, ChevronRight } from "lucide-react";
import {
  GoogleDriveLogo,
  NotionLogo,
  SlackLogo,
  GitHubLogo,
  OpenAILogo,
  StripeLogo,
  TwilioLogo,
} from "./brandLogos.jsx";

// Custom (non-brand) tool badge.
const CustomToolLogo = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <rect x="2" y="2" width="20" height="20" rx="6" fill="#eef1fe" />
    <path
      d="M14.8 7.2a3 3 0 0 0-3.9 3.6l-4 4a1.4 1.4 0 0 0 2 2l4-4a3 3 0 0 0 3.6-3.9l-1.8 1.8-1.6-.4-.4-1.6z"
      fill="#4f46e5"
    />
  </svg>
);

const ROWS = [
  { n: 1, key: "google-drive", name: "Google Drive", logo: <GoogleDriveLogo />, category: "Storage", status: "active", last: "2 min ago" },
  { n: 2, key: "notion", name: "Notion", logo: <NotionLogo />, category: "Knowledge", status: "active", last: "12 min ago" },
  { n: 3, key: "slack", name: "Slack", logo: <SlackLogo />, category: "Communication", status: "active", last: "1 hour ago" },
  { n: 4, key: "github", name: "GitHub", logo: <GitHubLogo />, category: "Development", status: "active", last: "2 hours ago" },
  { n: 5, key: "openai", name: "OpenAI", logo: <OpenAILogo />, category: "AI/LLM", status: "active", last: "3 hours ago" },
  { n: 6, key: "stripe", name: "Stripe", logo: <StripeLogo />, category: "Payments", status: "not-configured", last: "—" },
  { n: 7, key: "twilio", name: "Twilio", logo: <TwilioLogo />, category: "Communication", status: "active", last: "1 day ago" },
  { n: 8, key: "custom-research-tool", name: "Custom Research Tool", logo: <CustomToolLogo />, category: "Custom", status: "active", last: "2 days ago" },
];

const StatusBadge = ({ status }) => {
  if (status === "not-configured") {
    return (
      <span className="tools-badge amber">
        <span className="tools-badge-dot" /> Not Configured
      </span>
    );
  }
  return (
    <span className="tools-badge green">
      <span className="tools-badge-dot" /> Active
    </span>
  );
};

export const ViewToolbox = ({ onOpenTool }) => {
  const [page, setPage] = useState(1);

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>Toolbox Overview</h1>
            <p className="tools-subtitle">All available tools (search, maps, APIs, etc.)</p>
          </div>
          <button className="tools-primary">
            <Plus size={18} strokeWidth={2.6} /> Add Tool
          </button>
        </div>

        {/* Stat cards */}
        <div className="tools-stats">
          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Settings size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Total Tools</div>
              <div className="tools-stat-value">
                24 <span className="tools-stat-trend">▲12%</span>
              </div>
            </div>
          </div>

          <div className="tools-stat card">
            <div className="tools-stat-ic green"><span className="tools-stat-dot green" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Active</div>
              <div className="tools-stat-value">18</div>
            </div>
          </div>

          <div className="tools-stat card">
            <div className="tools-stat-ic amber"><span className="tools-stat-dot amber" /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Not Configured</div>
              <div className="tools-stat-value">4</div>
            </div>
          </div>

          <div className="tools-stat card">
            <div className="tools-stat-ic indigo"><Wrench size={20} strokeWidth={2} /></div>
            <div className="tools-stat-body">
              <div className="tools-stat-label">Custom Tools</div>
              <div className="tools-stat-value">6</div>
            </div>
          </div>
        </div>

        {/* Toolbar + table panel */}
        <div className="tools-panel card">
          <div className="tools-toolbar">
            <div className="tools-search">
              <Search size={18} strokeWidth={2} className="tools-search-icon" />
              <input placeholder="Search tools..." />
            </div>
            <button className="tools-select">
              All Categories <ChevronDown size={18} strokeWidth={2} />
            </button>
            <button className="tools-select">
              All Status <ChevronDown size={18} strokeWidth={2} />
            </button>
          </div>

          <div className="tools-table-wrap">
            <table className="tools-table">
              <thead>
                <tr>
                  <th className="tcol-num">#</th>
                  <th>Tool / Integration</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Last Used</th>
                  <th className="tcol-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.n}>
                    <td className="tcol-num">{row.n}</td>
                    <td>
                      <div className="tools-name-cell">
                        <span className="tools-logo">{row.logo}</span>
                        <span className="tools-name">{row.name}</span>
                      </div>
                    </td>
                    <td className="tools-category">{row.category}</td>
                    <td><StatusBadge status={row.status} /></td>
                    <td className="tools-last">{row.last}</td>
                    <td className="tcol-actions">
                      <div className="tools-actions">
                        <button className="tools-open-btn" onClick={() => onOpenTool?.(row.key)}>Open</button>
                        <button className="tools-more-btn" aria-label="More actions">
                          <MoreVertical size={16} strokeWidth={2} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer: count + pagination */}
        <div className="tools-footer">
          <div className="tools-count">Showing 1–8 of 24 tools</div>
          <div className="tools-pager">
            <button className="tools-page-btn" aria-label="Previous" onClick={() => setPage((p) => Math.max(1, p - 1))}>
              <ChevronRight size={16} strokeWidth={2.4} style={{ transform: "rotate(180deg)" }} />
            </button>
            {[1, 2, 3].map((p) => (
              <button
                key={p}
                className={`tools-page-btn ${page === p ? "active" : ""}`}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            ))}
            <button className="tools-page-btn" aria-label="Next" onClick={() => setPage((p) => Math.min(3, p + 1))}>
              <ChevronRight size={16} strokeWidth={2.4} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
