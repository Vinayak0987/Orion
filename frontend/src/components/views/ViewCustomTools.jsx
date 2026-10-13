// Tools · Custom Tools (ViewCustomTools.jsx)
// Renders in the Tools section "Custom Tools" sub-tab. Indigo primary buttons
// (consistent with the rest of the app). Scoped under `.tools-page`.
import { Plus, Search, ChevronDown, Bot, FileText, Target, Radar, MessageSquareText, FileText as FileTextAlt, MoreVertical } from "lucide-react";

const TOOLS = [
  {
    name: "Research Assistant",
    desc: "Web research and content analysis tool.",
    tag: "Research",
    status: "active",
    icon: <Bot size={26} strokeWidth={2} />,
    iconClass: "ct-ic-indigo",
  },
  {
    name: "PDF Analyzer",
    desc: "Extract and analyze content from PDFs.",
    tag: "Document",
    status: "active",
    icon: <FileText size={24} strokeWidth={2} />,
    iconClass: "ct-ic-blue",
  },
  {
    name: "Competitor Tracker",
    desc: "Track competitor websites and analyze changes.",
    tag: "Analytics",
    status: "draft",
    icon: <Target size={24} strokeWidth={2} />,
    iconClass: "ct-ic-purple",
  },
  {
    name: "Social Media Monitor",
    desc: "Monitor social media mentions and sentiment.",
    tag: "Marketing",
    status: "active",
    icon: <Radar size={24} strokeWidth={2} />,
    iconClass: "ct-ic-sky",
  },
  {
    name: "Data Cleaner",
    desc: "Clean and preprocess datasets.",
    tag: "Data",
    status: "active",
    icon: <MessageSquareText size={24} strokeWidth={2} />,
    iconClass: "ct-ic-cyan",
  },
];

const StatusBadge = ({ status }) =>
  status === "draft" ? (
    <span className="tools-badge amber"><span className="tools-badge-dot" /> Draft</span>
  ) : (
    <span className="tools-badge green"><span className="tools-badge-dot" /> Active</span>
  );

export const ViewCustomTools = () => (
  <div className="tools-page">
    <section className="tools-content">
      {/* Header */}
      <div className="tools-head">
        <div>
          <h1>Custom Tools</h1>
          <p className="tools-subtitle">Create and manage your own tools.</p>
        </div>
        <button className="tools-primary">
          <Plus size={18} strokeWidth={2.6} /> Create Custom Tool
        </button>
      </div>

      {/* Toolbar */}
      <div className="tools-toolbar">
        <div className="tools-search">
          <Search size={18} strokeWidth={2} className="tools-search-icon" />
          <input placeholder="Search custom tools..." />
        </div>
        <button className="tools-select">
          All Categories <ChevronDown size={18} strokeWidth={2} />
        </button>
        <button className="tools-select">
          All Status <ChevronDown size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Custom tool list */}
      <div className="ct-list">
        {TOOLS.map((t) => (
          <div key={t.name} className="ct-card card">
            <div className={`ct-icon ${t.iconClass}`}>{t.icon}</div>
            <div className="ct-info">
              <h3 className="ct-name">{t.name}</h3>
              <p className="ct-desc">{t.desc}</p>
              <span className="ct-tag">{t.tag}</span>
            </div>
            <div className="ct-status">
              <StatusBadge status={t.status} />
            </div>
            <div className="ct-actions">
              <button className="ct-edit-btn">Edit</button>
              <button className="tools-more-btn" aria-label="More actions">
                <MoreVertical size={16} strokeWidth={2} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Need ideas callout */}
      <div className="ct-ideas card">
        <div className="ct-ideas-icon"><FileTextAlt size={22} strokeWidth={2} /></div>
        <div className="ct-ideas-body">
          <h3>Need ideas?</h3>
          <p>Check out our templates or documentation to get started.</p>
        </div>
        <button className="tools-primary ct-ideas-btn">
          <FileTextAlt size={17} strokeWidth={2} /> View Templates
        </button>
      </div>
    </section>
  </div>
);
