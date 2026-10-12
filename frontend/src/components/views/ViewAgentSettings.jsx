// 5.7 Agent Settings — built to match the reference design.
// Renders in the Agents section "Settings" sub-tab. Indigo accents.
import { useState } from "react";
import {
  Bot,
  ChevronDown,
  Play,
  MoreVertical,
  Lock,
  ArrowRight,
  Copy,
  Upload,
  RotateCcw,
  FileText,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Plus,
} from "lucide-react";

const TABS = ["General", "Access & Permissions", "Runtime", "Notifications", "Versions", "Danger Zone"];

const VERSIONS = [
  { v: "v1.2.0", date: "Sep 28, 2024", note: null, current: true },
  { v: "v1.1.0", date: "Sep 15, 2024", note: "Improved prompts", current: false },
  { v: "v0.0.0", date: "Aug 30, 2024", note: "Initial version", current: false },
];

const QUICK_ACTIONS = [
  { label: "Clone Agent", icon: <Copy size={19} strokeWidth={2} /> },
  { label: "Export Configuration", icon: <Upload size={19} strokeWidth={2} /> },
  { label: "Reset to Default", icon: <RotateCcw size={19} strokeWidth={2} /> },
  { label: "View Audit Logs", icon: <FileText size={19} strokeWidth={2} /> },
];

const Field = ({ label, children }) => (
  <div className="set-field">
    <label className="set-label">{label}</label>
    {children}
  </div>
);

const Select = ({ value }) => (
  <div className="set-select">
    {value}
    <ChevronDown size={18} strokeWidth={2} className="set-select-caret" />
  </div>
);

export const ViewAgentSettings = () => {
  const [tab, setTab] = useState("General");

  return (
    <div className="agent-settings">
      {/* Header */}
      <div className="set-header">
        <div className="set-header-left">
          <div className="set-header-icon"><Bot size={26} strokeWidth={2} /></div>
          <h1>Marketing Agent</h1>
          <span className="set-status"><span className="set-status-dot" /> Active</span>
          <button className="set-version">v1.2.0 <ChevronDown size={15} strokeWidth={2} /></button>
        </div>
        <div className="set-header-actions">
          <button className="set-test-btn"><Play size={16} strokeWidth={2} fill="currentColor" /> Test</button>
          <button className="set-more" aria-label="More"><MoreVertical size={20} strokeWidth={2} /></button>
        </div>
      </div>

      {/* Tabs */}
      <div className="set-tabs">
        {TABS.map((t) => (
          <button key={t} className={`set-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {/* Body */}
      <div className="set-body">
        {/* Left: Basic Information */}
        <div className="set-main card">
          <h2 className="set-section-title">Basic Information</h2>

          <Field label="Agent Name">
            <input className="set-input" defaultValue="Marketing Agent" />
          </Field>

          <Field label="Description">
            <textarea className="set-textarea" rows={2} defaultValue="Creates content, analyzes campaigns, and drives growth across multiple channels." />
          </Field>

          <div className="set-row">
            <Field label="Department"><Select value="Marketing" /></Field>
            <Field label="Agent Type"><Select value="Specialist Agent" /></Field>
          </div>

          <div className="set-row">
            <Field label="Owner"><Select value="Abhishek Mishra" /></Field>
            <Field label="Autonomy Level"><Select value="High" /></Field>
          </div>

          <div className="set-row">
            <Field label="Default Model"><Select value="Claude 3.5 Sonnet" /></Field>
            <Field label="Temperature"><input className="set-input" defaultValue="0.7" /></Field>
          </div>

          <Field label="Tags">
            <div className="set-tags">
              {["Marketing", "Content", "Analysis"].map((t) => (
                <span key={t} className="set-tag">{t}</span>
              ))}
              <button className="set-addtag"><Plus size={16} strokeWidth={2.4} /> Add Tag</button>
            </div>
          </Field>

          <div className="set-field">
            <label className="set-label">Agent Icon</label>
            <div className="set-icon-row">
              <div className="set-icon-preview"><Bot size={56} strokeWidth={2} /></div>
              <button className="set-changeicon"><UploadCloud size={18} strokeWidth={2} /> Change Icon</button>
            </div>
          </div>
        </div>

        {/* Right: Version History + Quick Actions + Danger Zone */}
        <div className="set-side">
          <div className="set-panel card">
            <h2 className="set-section-title">Version History</h2>
            <div className="set-versions">
              {VERSIONS.map((ver) => (
                <div key={ver.v} className="set-version-item">
                  <span className="set-version-lock"><Lock size={18} strokeWidth={2} /></span>
                  <div className="set-version-body">
                    <div className="set-version-v">{ver.v}</div>
                    <div className="set-version-date">{ver.date}</div>
                    {ver.current && <span className="set-version-current">Current version</span>}
                    {ver.note && <div className="set-version-note">{ver.note}</div>}
                  </div>
                  <span className="set-version-avatar">AM</span>
                </div>
              ))}
            </div>
            <button className="set-viewall">View all versions <ArrowRight size={16} strokeWidth={2.2} /></button>
          </div>

          <div className="set-panel card">
            <h2 className="set-section-title">Quick Actions</h2>
            <div className="set-actions">
              {QUICK_ACTIONS.map((a) => (
                <button key={a.label} className="set-action">
                  <span className="set-action-icon">{a.icon}</span>
                  {a.label}
                </button>
              ))}
            </div>
          </div>

          <div className="set-panel card set-danger">
            <h2 className="set-danger-title">Danger Zone</h2>
            <button className="set-danger-btn">
              <ShieldCheck size={19} strokeWidth={2} />
              <span className="set-danger-label">Disable Agent</span>
            </button>
            <button className="set-danger-btn">
              <Trash2 size={19} strokeWidth={2} />
              <span className="set-danger-body">
                <span className="set-danger-label">Delete Agent</span>
                <span className="set-danger-sub">This action cannot be undone.</span>
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
