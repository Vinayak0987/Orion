// 5.2 Create New Agent — built to match the reference design exactly.
// Renders inside the app's existing Sidebar/Topbar (content area only).
import { useState } from "react";
import {
  Paperclip,
  ChevronRight,
  Globe,
  FileText,
  Target,
  Plus,
  ChevronDown,
  Check,
  RefreshCw,
  Sparkles,
  ArrowRight,
} from "lucide-react";

/* ---- Brand / tool icons (exact logos) ---- */
const NotionLogo = () => (
  <svg viewBox="0 0 24 24" className="tool-logo" aria-hidden="true">
    <rect x="3" y="2.5" width="18" height="19" rx="2.5" fill="#fff" stroke="#111" strokeWidth="1.4" />
    <path d="M8 7.5v9M8 7.5l7.5 9M15.5 7.5v9" fill="none" stroke="#111" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SlackLogo = () => (
  <svg viewBox="0 0 24 24" className="tool-logo" aria-hidden="true">
    <path d="M6 15a2 2 0 1 1-2-2h2v2z" fill="#E01E5A" />
    <path d="M7 15a2 2 0 1 1 4 0v5a2 2 0 1 1-4 0v-5z" fill="#E01E5A" />
    <path d="M9 6a2 2 0 1 1 2 2H9V6z" fill="#36C5F0" />
    <path d="M9 7a2 2 0 1 1 0 4H4a2 2 0 1 1 0-4h5z" fill="#36C5F0" />
    <path d="M18 9a2 2 0 1 1 2 2h-2V9z" fill="#2EB67D" />
    <path d="M17 9a2 2 0 1 1-4 0V4a2 2 0 1 1 4 0v5z" fill="#2EB67D" />
    <path d="M15 18a2 2 0 1 1-2-2h2v2z" fill="#ECB22E" />
    <path d="M15 17a2 2 0 1 1 0-4h5a2 2 0 1 1 0 4h-5z" fill="#ECB22E" />
  </svg>
);

const GoogleDriveLogo = () => (
  <svg viewBox="0 0 24 24" className="tool-logo" aria-hidden="true">
    <path d="M8.4 3h7.2l7.2 12.4h-7.2z" fill="#FFCF3E" />
    <path d="M8.4 3 1.2 15.4 4.8 21 12 8.6z" fill="#0F9D58" />
    <path d="M4.8 21h14.4l3.6-5.6H8.4z" fill="#4285F4" />
  </svg>
);

const RobotAvatar = () => (
  <svg viewBox="0 0 64 64" className="robot-svg" aria-hidden="true">
    {/* antenna */}
    <circle cx="32" cy="10" r="3" fill="#4f46e5" />
    <rect x="31" y="12" width="2" height="6" rx="1" fill="#4f46e5" />
    {/* head */}
    <rect x="16" y="18" width="32" height="26" rx="9" fill="#4f46e5" />
    {/* eyes */}
    <circle cx="26" cy="29" r="3.4" fill="#fff" />
    <circle cx="38" cy="29" r="3.4" fill="#fff" />
    {/* mouth */}
    <rect x="24" y="36" width="16" height="5" rx="2.5" fill="#fff" />
    {/* ears */}
    <rect x="12" y="27" width="4" height="8" rx="2" fill="#4f46e5" />
    <rect x="48" y="27" width="4" height="8" rx="2" fill="#4f46e5" />
  </svg>
);

const RESPONSIBILITIES = [
  "Research and analyze market trends",
  "Collect and process data from multiple sources",
  "Generate actionable insights",
  "Create reports and visualizations",
  "Monitor competitor activity",
];

const SUGGESTED_TOOLS = [
  { label: "Web Search", icon: <Globe size={15} strokeWidth={2} className="tool-lucide" /> },
  { label: "Notion", icon: <NotionLogo /> },
  { label: "Slack", icon: <SlackLogo /> },
  { label: "Google Drive", icon: <GoogleDriveLogo /> },
];

const KNOWLEDGE_SOURCES = [
  { label: "Market Reports", icon: <FileText size={15} strokeWidth={2} className="tool-lucide" /> },
  { label: "Competitor Data", icon: <Target size={15} strokeWidth={2} className="tool-lucide" /> },
  { label: "Industry News", icon: <FileText size={15} strokeWidth={2} className="tool-lucide" /> },
];

const PERMISSIONS = ["Read data", "Write reports", "Use external tools"];

const PREVIEW_TAGS = ["Research", "Analyze", "Report", "Visualize"];

export const ViewCreateAgent = () => {
  const [mode, setMode] = useState("ai"); // "ai" | "manual"

  return (
    <div className="create-agent-page">
      {/* Page header */}
      <div className="ca-head">
        <h1>Create New Agent</h1>
        <p>Choose how you want to create your agent.</p>
      </div>

      {/* AI-assisted / Manual toggle */}
      <div className="ca-mode">
        <button
          className={`ca-mode-btn ${mode === "ai" ? "active" : ""}`}
          onClick={() => setMode("ai")}
        >
          AI-assisted
        </button>
        <button
          className={`ca-mode-btn ${mode === "manual" ? "active" : ""}`}
          onClick={() => setMode("manual")}
        >
          Manual
        </button>
      </div>

      {/* Describe box */}
      <div className="ca-describe card">
        <h3>Describe what you want this agent to do</h3>
        <div className="ca-prompt">
          <textarea
            placeholder="E.g. Create a research agent that analyzes market trends and generates business reports..."
            rows={2}
          />
          <div className="ca-prompt-actions">
            <button className="ca-attach" aria-label="Attach">
              <Paperclip size={20} strokeWidth={1.8} />
            </button>
            <button className="ca-send" aria-label="Generate">
              <ChevronRight size={20} strokeWidth={2.6} />
            </button>
          </div>
        </div>
      </div>

      {/* Two-column body */}
      <div className="ca-body">
        {/* Generated Preview */}
        <div className="ca-generated card">
          <h2>Generated Preview</h2>

          <label className="ca-label">Agent Name</label>
          <input className="ca-input" defaultValue="Market Research Agent" />

          <h4 className="ca-section-title">Purpose</h4>
          <p className="ca-purpose">
            Analyze market trends, collect insights, and generate comprehensive
            research reports for business decisions.
          </p>

          <h4 className="ca-section-title">Responsibilities</h4>
          <ul className="ca-resp">
            {RESPONSIBILITIES.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>

          <h4 className="ca-section-title">Suggested Tools</h4>
          <div className="ca-chips">
            {SUGGESTED_TOOLS.map((t) => (
              <span key={t.label} className="ca-chip">
                {t.icon}
                {t.label}
                <span className="ca-chip-x" aria-hidden="true">×</span>
              </span>
            ))}
          </div>

          <h4 className="ca-section-title">Knowledge Sources</h4>
          <div className="ca-chips">
            {KNOWLEDGE_SOURCES.map((k) => (
              <span key={k.label} className="ca-chip">
                {k.icon}
                {k.label}
                <span className="ca-chip-x" aria-hidden="true">×</span>
              </span>
            ))}
          </div>
          <button className="ca-add-source">
            <Plus size={16} strokeWidth={2.4} /> Add Source
          </button>

          <h4 className="ca-section-title">Memory</h4>
          <div className="ca-select">
            Long-term (90 days)
            <ChevronDown size={18} strokeWidth={2} className="ca-select-caret" />
          </div>

          <h4 className="ca-section-title">Permissions</h4>
          <div className="ca-perms">
            {PERMISSIONS.map((p) => (
              <label key={p} className="ca-perm">
                <span className="ca-check">
                  <Check size={13} strokeWidth={3.2} />
                </span>
                {p}
              </label>
            ))}
          </div>
        </div>

        {/* Agent Preview */}
        <div className="ca-preview card">
          <h2>Agent Preview</h2>
          <div className="ca-preview-inner">
            <div className="ca-robot">
              <RobotAvatar />
            </div>
            <h3 className="ca-robot-name">
              Market
              <br />
              Research Agent
            </h3>
            <p className="ca-robot-desc">
              Analyzes trends. Finds insights. Delivers results.
            </p>
            <div className="ca-preview-tags">
              {PREVIEW_TAGS.map((tag) => (
                <span key={tag} className="ca-preview-tag">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Footer actions */}
      <div className="ca-footer">
        <div className="ca-footer-left">
          <button className="ca-btn-outline">
            <RefreshCw size={17} strokeWidth={2} /> Regenerate
          </button>
          <button className="ca-btn-outline">
            <FileText size={17} strokeWidth={2} /> Save as Template
          </button>
        </div>
        <button className="ca-btn-primary">
          <Sparkles size={17} strokeWidth={2} /> Create Agent
          <ArrowRight size={17} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
};
