// 5.3 Agent Builder — built to match the reference design exactly.
// Renders inside the Agents section "Builder" sub-tab (app Sidebar/Topbar reused).
import { useState } from "react";
import {
  Play,
  ChevronDown,
  Plus,
  Minus,
  Maximize2,
  Layers,
  Bot,
  FileText,
  Search,
  BarChart3,
  Newspaper,
  ShoppingBag,
  Send,
  CheckCircle2,
  RefreshCw,
  Sparkles,
  ArrowRight,
} from "lucide-react";

const TOP_TABS = ["Overview", "Instructions", "Tools", "Memory", "Permissions", "Model"];
const CFG_TABS = ["General", "Instructions", "Tools", "Memory", "Permissions"];

const SPECIALISTS = [
  { name: "Content Creator", role: "(Writer)", icon: <Newspaper size={20} strokeWidth={2} />, tint: "ab-ic-dark" },
  { name: "SEO Analyst", role: "(Specialist)", icon: <Bot size={20} strokeWidth={2} />, tint: "ab-ic-light" },
  { name: "Campaign Manager", role: "(Specialist)", icon: <ShoppingBag size={20} strokeWidth={2} />, tint: "ab-ic-indigo" },
];

const TOOLS = [
  { name: "Web Search", role: "(Tool)", icon: <Search size={20} strokeWidth={2} /> },
  { name: "Notion", role: "(Tool)", icon: <FileText size={20} strokeWidth={2} /> },
  { name: "Analytics", role: "(Tool)", icon: <BarChart3 size={20} strokeWidth={2} /> },
];

const RECENT_TESTS = [
  { title: "Create a blog post about AI in business", time: "2 min ago" },
  { title: "Analyze Q3 campaign performance", time: "1 hour ago" },
  { title: "Generate social media content ideas", time: "1 hour ago" },
];

export const ViewAgentBuilder = () => {
  const [topTab, setTopTab] = useState("Overview");
  const [cfgTab, setCfgTab] = useState("General");

  return (
    <div className="agent-builder">
      {/* Top tabs */}
      <div className="ab-toptabs">
        {TOP_TABS.map((t) => (
          <button
            key={t}
            className={`ab-toptab ${topTab === t ? "active" : ""}`}
            onClick={() => setTopTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Agent header */}
      <div className="ab-header card">
        <div className="ab-header-icon">
          <Bot size={26} strokeWidth={2} />
        </div>
        <div className="ab-header-info">
          <div className="ab-header-titlerow">
            <h2>Marketing Agent</h2>
            <span className="ab-status">
              <span className="ab-status-dot" /> Active
            </span>
            <button className="ab-version">
              v1.2.0 <ChevronDown size={15} strokeWidth={2} />
            </button>
          </div>
          <p>Create content, analyze campaigns, and drive growth.</p>
        </div>
        <button className="ab-test-btn">
          <Play size={16} strokeWidth={2} fill="currentColor" /> Test
        </button>
      </div>

      {/* Node graph canvas */}
      <div className="ab-canvas card">
        <div className="ab-canvas-controls">
          <button aria-label="Zoom in"><Plus size={18} strokeWidth={2.4} /></button>
          <button aria-label="Zoom out"><Minus size={18} strokeWidth={2.4} /></button>
        </div>
        <div className="ab-canvas-controls ab-canvas-controls-2">
          <button aria-label="Fit"><Maximize2 size={17} strokeWidth={2} /></button>
        </div>
        <div className="ab-canvas-controls ab-canvas-controls-3">
          <button aria-label="Layers"><Layers size={17} strokeWidth={2} /></button>
        </div>

        {/* Orchestrator */}
        <div className="ab-graph">
          <div className="ab-orch">
            <div className="ab-orch-ring">
              <div className="ab-orch-icon">
                <Bot size={30} strokeWidth={2} />
              </div>
            </div>
            <h3>Marketing Agent</h3>
            <span className="ab-node-role">(Orchestration)</span>
          </div>

          {/* Connectors: orchestrator -> specialists */}
          <svg className="ab-lines ab-lines-1" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true">
            <path d="M450 4 L450 30" />
            <path d="M150 116 L150 60 Q150 44 166 44 L734 44 Q750 44 750 60 L750 116" />
            <path d="M450 44 L450 116" />
            <circle cx="150" cy="116" r="4" className="ab-dot" />
            <circle cx="450" cy="116" r="4" className="ab-dot" />
            <circle cx="750" cy="116" r="4" className="ab-dot" />
          </svg>

          {/* Specialists row */}
          <div className="ab-row">
            {SPECIALISTS.map((s) => (
              <div key={s.name} className="ab-node">
                <div className={`ab-node-icon ${s.tint}`}>{s.icon}</div>
                <h4>{s.name}</h4>
                <span className="ab-node-role">{s.role}</span>
              </div>
            ))}
          </div>

          {/* Connectors: specialists -> tools */}
          <svg className="ab-lines ab-lines-2" viewBox="0 0 900 120" preserveAspectRatio="none" aria-hidden="true">
            <path d="M150 4 L150 30" />
            <path d="M150 30 L150 44 Q150 60 166 60 L734 60 Q750 60 750 44 L750 30" />
            <path d="M150 60 L150 116" />
            <path d="M450 60 L450 116" />
            <path d="M750 60 L750 116" />
            <circle cx="150" cy="116" r="4" className="ab-dot" />
            <circle cx="450" cy="116" r="4" className="ab-dot" />
            <circle cx="750" cy="116" r="4" className="ab-dot" />
          </svg>

          {/* Tools row */}
          <div className="ab-row">
            {TOOLS.map((t) => (
              <div key={t.name} className="ab-node">
                <div className="ab-node-icon ab-ic-dark">{t.icon}</div>
                <h4>{t.name}</h4>
                <span className="ab-node-role">{t.role}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom two-column area */}
      <div className="ab-bottom">
        {/* Node Configuration */}
        <div className="ab-config card">
          <h3 className="ab-panel-title">Node Configuration</h3>
          <div className="ab-cfg-tabs">
            {CFG_TABS.map((t) => (
              <button
                key={t}
                className={`ab-cfg-tab ${cfgTab === t ? "active" : ""}`}
                onClick={() => setCfgTab(t)}
              >
                {t}
              </button>
            ))}
          </div>

          <label className="ab-label">Node Name</label>
          <input className="ab-input" defaultValue="Content Creator" />

          <label className="ab-label">Node Type</label>
          <div className="ab-select">
            Specialist Agent
            <ChevronDown size={18} strokeWidth={2} className="ab-select-caret" />
          </div>

          <label className="ab-label">Description</label>
          <textarea
            className="ab-textarea"
            rows={2}
            defaultValue="Creates engaging content for various channels, including blogs, social media, and marketing materials."
          />

          <label className="ab-label">System Prompt</label>
          <div className="ab-prompt-wrap">
            <textarea
              className="ab-textarea ab-prompt"
              rows={3}
              defaultValue="You are a content creation specialist with expertise in digital marketing and brand communication..."
            />
            <span className="ab-charcount">0/4000</span>
          </div>
        </div>

        {/* Test Agent + Recent Tests */}
        <div className="ab-right">
          <div className="ab-test card">
            <h3 className="ab-panel-title">Test Agent</h3>
            <div className="ab-test-input">
              <textarea placeholder="Send a test message..." rows={2} />
              <button className="ab-send" aria-label="Send">
                <Send size={16} strokeWidth={2} />
              </button>
            </div>
          </div>

          <div className="ab-recent card">
            <h3 className="ab-panel-title">Recent Tests</h3>
            <ul className="ab-recent-list">
              {RECENT_TESTS.map((r) => (
                <li key={r.title}>
                  <CheckCircle2 size={20} className="ab-check" strokeWidth={2} />
                  <div className="ab-recent-body">
                    <p className="ab-recent-title">{r.title}</p>
                    <div className="ab-recent-meta">
                      <span className="ab-success">Success</span>
                      <span className="ab-recent-time">{r.time}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
            <button className="ab-viewall">
              View all tests <ArrowRight size={15} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="ab-footer">
        <div className="ab-footer-left">
          <button className="ab-btn-outline">
            <RefreshCw size={17} strokeWidth={2} /> Regenerate
          </button>
          <button className="ab-btn-outline">
            <FileText size={17} strokeWidth={2} /> Save as Template
          </button>
        </div>
        <button className="ab-btn-primary">
          <Sparkles size={17} strokeWidth={2} /> Create Agent
          <ArrowRight size={17} strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
};
