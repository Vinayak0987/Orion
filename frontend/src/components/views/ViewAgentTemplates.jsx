// 5.4 Agent Templates — built to match the reference design.
// Renders in the Agents section "Templates" sub-tab. Indigo primary buttons.
import { useState } from "react";
import {
  Search,
  ChevronDown,
  Headphones,
  Megaphone,
  ChartColumnIncreasing,
  Settings,
  IdCard,
  MessagesSquare,
  ShoppingBag,
  Play,
  FileText,
  Bot,
  Gem,
  Circle,
} from "lucide-react";

const CATEGORIES = [
  "All", "Marketing", "Finance", "Operations", "Research", "HR",
  "Customer Support", "Sales", "Product", "Legal", "IT",
];

const TEMPLATES = [
  {
    name: "Marketing Agent",
    desc: "Creates content, analyzes campaigns, and grows brand presence.",
    tags: ["Marketing", "Content"],
    icon: <Megaphone size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-red",
  },
  {
    name: "Financial Analyst",
    desc: "Analyzes financial data and generates insights.",
    tags: ["Finance", "Analysis"],
    icon: <ChartColumnIncreasing size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-green",
  },
  {
    name: "Operations Agent",
    desc: "Streamlines operations and monitor performance.",
    tags: ["Operations", "Automation"],
    icon: <Settings size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-purple",
  },
  {
    name: "HR Assistant",
    desc: "Handles employee queries and manages HR workflows.",
    tags: ["HR", "Support"],
    icon: <IdCard size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-orange",
  },
  {
    name: "Customer Support",
    desc: "Manages customer inquiries and provides proactive.",
    tags: ["Support", "Communication"],
    icon: <MessagesSquare size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-indigo",
  },
  {
    name: "Sales Assistant",
    desc: "Supports sales team with outreach and lead analysis.",
    tags: ["Sales", "Outreach"],
    icon: <ShoppingBag size={24} strokeWidth={2} />,
    iconClass: "tpl-ic-blue",
  },
];

export const ViewAgentTemplates = () => {
  const [activeCat, setActiveCat] = useState("All");

  return (
    <div className="agent-templates">
      {/* Header */}
      <div className="tpl-head">
        <h1>Agent Templates</h1>
        <p>Start with a pre-built agent and customize it.</p>
      </div>

      {/* Search + category dropdown */}
      <div className="tpl-searchrow">
        <div className="tpl-search">
          <Search size={19} strokeWidth={2} className="tpl-search-icon" />
          <input placeholder="Search templates..." />
        </div>
        <button className="tpl-catselect">
          All Categories <ChevronDown size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Category chips */}
      <div className="tpl-chips">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            className={`tpl-chip ${activeCat === c ? "active" : ""}`}
            onClick={() => setActiveCat(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Featured Templates */}
      <div className="tpl-featured-wrap">
        <h2 className="tpl-featured-title">Featured Templates</h2>
        <div className="tpl-featured card">
          <div className="tpl-featured-left">
            <div className="tpl-featured-head">
              <div className="tpl-featured-icon">
                <Headphones size={30} strokeWidth={2} />
              </div>
              <h3>Business Research Agent</h3>
            </div>
            <p className="tpl-featured-desc">
              Conducts market research, analyzes competitors, and generates
              strategic insights.
            </p>
            <div className="tpl-tags">
              {["Research", "Analysis", "Reporting"].map((t) => (
                <span key={t} className="tpl-tag">{t}</span>
              ))}
            </div>
            <div className="tpl-featured-actions">
              <button className="tpl-btn-primary">Use Template</button>
              <button className="tpl-btn-outline">Preview</button>
            </div>
          </div>
          <div className="tpl-featured-art" aria-hidden="true">
            {/* soft lavender blobs */}
            <span className="tpl-blob tpl-blob-1" />
            <span className="tpl-blob tpl-blob-2" />
            <span className="tpl-blob tpl-blob-3" />
            <span className="tpl-blob tpl-blob-4" />
            {/* floating icons */}
            <span className="tpl-art-ic tpl-art-play">
              <Play size={16} strokeWidth={0} fill="#fff" />
            </span>
            <span className="tpl-art-ic tpl-art-doc">
              <FileText size={20} strokeWidth={2} />
            </span>
            <span className="tpl-art-ic tpl-art-chip">
              <Bot size={20} strokeWidth={2} />
            </span>
            <span className="tpl-art-ic tpl-art-gem">
              <Gem size={16} strokeWidth={2} />
            </span>
            <span className="tpl-art-dot tpl-art-dot-1">
              <Circle size={16} strokeWidth={2.4} />
            </span>
            <span className="tpl-art-dot tpl-art-dot-2">
              <Circle size={14} strokeWidth={2.4} />
            </span>
          </div>
        </div>
      </div>

      {/* Template grid */}
      <div className="tpl-grid">
        {TEMPLATES.map((t) => (
          <div key={t.name} className="tpl-card card">
            <div className={`tpl-card-icon ${t.iconClass}`}>{t.icon}</div>
            <h3 className="tpl-card-name">{t.name}</h3>
            <p className="tpl-card-desc">{t.desc}</p>
            <div className="tpl-tags">
              {t.tags.map((tag) => (
                <span key={tag} className="tpl-tag">{tag}</span>
              ))}
            </div>
            <button className="tpl-btn-primary tpl-card-btn">Use Template</button>
          </div>
        ))}
      </div>
    </div>
  );
};
