// Tools · API Keys & Credentials (ViewApiKeys.jsx)
// Renders in the Tools section "API Keys" sub-tab. Indigo primary buttons
// (consistent with the rest of the app). Scoped under `.tools-page`.
import { useState } from "react";
import { Plus, Search, ChevronDown, Lock, MoreVertical } from "lucide-react";
import { OpenAILogo, GoogleLogo, StripeLogo, TwilioLogo } from "./brandLogos.jsx";

const CustomLogo = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3 4 8v8l8 5 8-5V8z" fill="none" stroke="#4f6bed" strokeWidth="2" strokeLinejoin="round" />
    <path d="M12 8v5M9.5 9.5 12 13l2.5-3.5" fill="none" stroke="#4f6bed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const TABS = ["API Keys", "Environment Variables", "Credential Store"];

const KEYS = [
  { n: 1, name: "OpenAI API Key", service: "OpenAI", logo: <OpenAILogo />, status: "active", created: "Jan 10, 2024" },
  { n: 2, name: "Google Maps API", service: "Google", logo: <GoogleLogo />, status: "active", created: "Jan 12, 2024" },
  { n: 3, name: "Stripe Secret Key", service: "Stripe", logo: <StripeLogo />, status: "active", created: "Jan 15, 2024" },
  { n: 4, name: "Twilio API Key", service: "Twilio", logo: <TwilioLogo />, status: "inactive", created: "Jan 16, 2024" },
  { n: 5, name: "Custom Tool Key", service: "Custom", logo: <CustomLogo />, status: "active", created: "Jan 20, 2024" },
];

const StatusBadge = ({ status }) =>
  status === "inactive" ? (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Inactive</span>
  ) : (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  );

export const ViewApiKeys = () => {
  const [activeTab, setActiveTab] = useState("API Keys");

  return (
    <div className="tools-page">
      <section className="tools-content">
        {/* Header */}
        <div className="tools-head">
          <div>
            <h1>API Keys &amp; Credentials</h1>
            <p className="tools-subtitle">Manage API tokens securely.</p>
          </div>
          <button className="tools-primary">
            <Plus size={18} strokeWidth={2.6} /> Add API Key
          </button>
        </div>

        {/* Panel: tabs + toolbar + table */}
        <div className="tools-panel card">
          <div className="tools-tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={`tools-tab ${activeTab === t ? "active" : ""}`}
                onClick={() => setActiveTab(t)}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="tools-toolbar">
            <div className="tools-search">
              <Search size={18} strokeWidth={2} className="tools-search-icon" />
              <input placeholder="Search API keys..." />
            </div>
            <button className="tools-select">
              All Status <ChevronDown size={18} strokeWidth={2} />
            </button>
            <button className="tools-select">
              All Services <ChevronDown size={18} strokeWidth={2} />
            </button>
          </div>

          <div className="tools-table-wrap">
            <table className="tools-table">
              <thead>
                <tr>
                  <th className="tcol-num">#</th>
                  <th>Name</th>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th className="tcol-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {KEYS.map((k) => (
                  <tr key={k.n}>
                    <td className="tcol-num">{k.n}</td>
                    <td><span className="tools-name">{k.name}</span></td>
                    <td>
                      <div className="ak-service">
                        <span className="ak-logo">{k.logo}</span>
                        <span className="ak-service-name">{k.service}</span>
                      </div>
                    </td>
                    <td><StatusBadge status={k.status} /></td>
                    <td className="tools-last">{k.created}</td>
                    <td className="tcol-actions">
                      <div className="tools-actions">
                        <button className="tools-open-btn">View</button>
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

        {/* Keep your keys secure callout */}
        <div className="ak-secure card">
          <div className="ak-secure-icon"><Lock size={24} strokeWidth={2} /></div>
          <div className="ak-secure-body">
            <h3>Keep your keys secure</h3>
            <p>API keys are encrypted and stored securely. Never share your keys in public repositories.</p>
          </div>
          <button className="tools-primary ak-secure-btn">View Security Guide</button>
        </div>
      </section>
    </div>
  );
};
