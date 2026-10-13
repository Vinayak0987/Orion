// Tools · Integrations (ViewIntegrations.jsx)
// Renders in the Tools section "Integrations" sub-tab. Indigo primary buttons
// (consistent with the rest of the app). Scoped under `.tools-page`.
import { Plus, Search, ChevronDown, Boxes, ShieldCheck, MoreVertical } from "lucide-react";
import {
  GoogleDriveLogo,
  SlackLogo,
  NotionLogo,
  ShopifyLogo,
  GitHubLogo,
  TwilioLogo,
  StripeLogo,
  ZapierLogo,
} from "./brandLogos.jsx";

const INTEGRATIONS = [
  { key: "google-drive", name: "Google Drive", desc: "File storage & documents", logo: <GoogleDriveLogo />, status: "connected" },
  { key: "slack", name: "Slack", desc: "Team communication", logo: <SlackLogo />, status: "connected" },
  { key: "notion", name: "Notion", desc: "Knowledge base", logo: <NotionLogo />, status: "connected" },
  { key: "shopify", name: "Shopify", desc: "E-commerce platform", logo: <ShopifyLogo />, status: "disconnected" },
  { key: "github", name: "GitHub", desc: "Code repository", logo: <GitHubLogo />, status: "connected" },
  { key: "twilio", name: "Twilio", desc: "SMS & communication", logo: <TwilioLogo />, status: "connected" },
  { key: "stripe", name: "Stripe", desc: "Payments & billing", logo: <StripeLogo />, status: "disconnected" },
  { key: "zapier", name: "Zapier", desc: "Workflow automation", logo: <ZapierLogo />, status: "connected" },
];

const StatusBadge = ({ status }) =>
  status === "disconnected" ? (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Disconnected</span>
  ) : (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Connected</span>
  );

export const ViewIntegrations = ({ onOpenTool }) => (
  <div className="tools-page">
    <section className="tools-content">
      {/* Header */}
      <div className="tools-head">
        <div>
          <h1>Integrations</h1>
          <p className="tools-subtitle">Connect external systems (Google, Shopify, etc.)</p>
        </div>
        <button className="tools-primary">
          <Plus size={18} strokeWidth={2.6} /> Add Integration
        </button>
      </div>

      {/* Stat cards */}
      <div className="tools-stats">
        <div className="tools-stat card">
          <div className="tools-stat-ic indigo"><Boxes size={20} strokeWidth={2} /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Total Integrations</div>
            <div className="tools-stat-value">12</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic green"><span className="tools-stat-dot green" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Connected</div>
            <div className="tools-stat-value">8</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic red"><span className="tools-stat-dot red" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Disconnected</div>
            <div className="tools-stat-value">4</div>
          </div>
        </div>
        <div className="tools-stat card">
          <div className="tools-stat-ic green"><ShieldCheck size={20} strokeWidth={2} color="#16a34a" /></div>
          <div className="tools-stat-body">
            <div className="tools-stat-label">Success Rate</div>
            <div className="tools-stat-value">96%</div>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="tools-toolbar">
        <div className="tools-search">
          <Search size={18} strokeWidth={2} className="tools-search-icon" />
          <input placeholder="Search integrations..." />
        </div>
        <button className="tools-select">
          All Categories <ChevronDown size={18} strokeWidth={2} />
        </button>
        <button className="tools-select">
          All Status <ChevronDown size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Integration grid */}
      <div className="intg-grid">
        {INTEGRATIONS.map((it) => (
          <div key={it.name} className="intg-card card">
            <div className="intg-logo">{it.logo}</div>
            <h3 className="intg-name">{it.name}</h3>
            <p className="intg-desc">{it.desc}</p>
            <StatusBadge status={it.status} />
            <div className="intg-actions">
              <button className="intg-btn" onClick={() => onOpenTool?.(it.key)}>
                {it.status === "disconnected" ? "Connect" : "Configure"}
              </button>
              <button className="tools-more-btn" aria-label="More actions">
                <MoreVertical size={16} strokeWidth={2} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  </div>
);
