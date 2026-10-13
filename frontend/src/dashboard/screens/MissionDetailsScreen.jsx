import { useState } from "react";
import { Icon } from "../icons";
import { Badge, Ring } from "../components";
import { MISSION_DETAIL } from "../mockData";

const STATE_COLOR = {
  Completed: "var(--o-accent)",
  "In Progress": "var(--o-accent-2)",
  Waiting: "var(--o-text-3)",
  Failed: "var(--o-danger)",
};

// A compact inline-SVG execution graph: a coordinator node on the left links to
// three phase nodes, each expanding to its child task nodes on the right.
function ExecutionGraph({ groups }) {
  const rowH = 92;
  const H = groups.length * rowH + 30;
  const coordY = H / 2;
  return (
    <svg viewBox={`0 0 640 ${H}`} width="100%" height={H} role="img" aria-label="Live execution graph">
      {/* coordinator */}
      <g>
        <circle cx="60" cy={coordY} r="24" fill="var(--o-panel-3)" stroke="var(--o-accent)" strokeWidth="1.4" />
        <circle cx="60" cy={coordY} r="4" fill="var(--o-accent)" />
        <text x="60" y={coordY + 42} textAnchor="middle" fontSize="10.5" fill="var(--o-text-2)">Orion Planner</text>
        <text x="60" y={coordY + 55} textAnchor="middle" fontSize="9" fill="var(--o-text-3)">Coordinator</text>
      </g>
      {groups.map((g, gi) => {
        const py = 40 + gi * rowH;
        return (
          <g key={g.id}>
            <path d={`M84 ${coordY} C 150 ${coordY}, 150 ${py}, 200 ${py}`} fill="none" stroke="var(--o-border)" strokeWidth="1.2" />
            <rect x="200" y={py - 18} width="150" height="36" rx="9" fill="var(--o-panel-2)" stroke="var(--o-border)" />
            <text x="214" y={py - 2} fontSize="11.5" fill="var(--o-text)">{g.label}</text>
            <text x="214" y={py + 11} fontSize="9.5" fill="var(--o-text-3)">{g.tasks} tasks</text>
            {g.children.map((c, ci) => {
              const cy = py - 26 + ci * 26;
              return (
                <g key={c.label}>
                  <path d={`M350 ${py} C 400 ${py}, 400 ${cy}, 440 ${cy}`} fill="none" stroke="var(--o-border-soft)" strokeWidth="1" />
                  <circle cx="446" cy={cy} r="3.5" fill={STATE_COLOR[c.state]} />
                  <text x="458" y={cy + 4} fontSize="10.5" fill="var(--o-text-2)">{c.label}</text>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

export default function MissionDetailsScreen({ onBack }) {
  const m = MISSION_DETAIL;
  const [tab, setTab] = useState(0);
  const t = m.task;

  return (
    <div className="o-fade">
      {/* Header */}
      <div className="o-card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button className="o-icon-btn" type="button" onClick={onBack}><Icon.chevronLeft s={18} /></button>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ margin: 0, fontSize: 19 }}>{m.title}</h2>
              <Badge>{m.status}</Badge>
            </div>
            <p style={{ margin: "4px 0 0", color: "var(--o-text-2)", fontSize: 13.5 }}>{m.sub}</p>
          </div>
          <Ring value={m.progress} size={62} />
          <button className="o-btn" type="button">Actions <Icon.chevronDown s={15} /></button>
        </div>

        {/* Tabs */}
        <div className="o-tabs" style={{ marginTop: 16, marginBottom: 0 }}>
          {m.tabs.map((label, i) => (
            <button key={label} className={tab === i ? "active" : ""} onClick={() => setTab(i)} type="button">{label}</button>
          ))}
        </div>
      </div>

      {/* Body: execution graph + task details */}
      <div className="o-split o-split-wide">
        <div className="o-card">
          <div className="o-card-head">
            <h3>Execution Graph <span className="o-badge o-badge-green" style={{ marginLeft: 6 }}>● Live</span></h3>
            <div style={{ display: "flex", gap: 6 }}>
              <button className="o-icon-btn" type="button"><Icon.search s={16} /></button>
              <button className="o-icon-btn" type="button"><Icon.more s={16} /></button>
            </div>
          </div>
          <ExecutionGraph groups={m.graph} />

          {/* Timeline legend */}
          <div style={{ borderTop: "1px solid var(--o-border-soft)", marginTop: 12, paddingTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: 12.5, fontWeight: 500 }}>Execution Timeline</span>
              <button className="o-link" type="button">View all →</button>
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 11.5, color: "var(--o-text-2)" }}>
              <Legend color="var(--o-accent)" label="Completed" />
              <Legend color="var(--o-accent-2)" label="In Progress" />
              <Legend color="var(--o-text-3)" label="Waiting" />
              <Legend color="var(--o-danger)" label="Failed" />
            </div>
          </div>
        </div>

        {/* Task details side panel */}
        <div className="o-card">
          <div className="o-card-head">
            <h3>Task Details</h3>
            <Badge>{t.status}</Badge>
          </div>

          <div style={{ fontWeight: 600, marginBottom: 2 }}>{t.name}</div>
          <div style={{ fontSize: 12, color: "var(--o-text-3)", marginBottom: 12 }}>
            {t.agent} · Started {t.started} · {t.percent}% complete
          </div>

          <Section title="Description"><p style={{ margin: 0, fontSize: 13, color: "var(--o-text-2)" }}>{t.description}</p></Section>

          <Section title="Tools Used">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {t.tools.map((tool) => {
                const Glyph = Icon[tool.icon] ?? Icon.tools;
                return <span className="o-tree-node" key={tool.name}><Glyph s={13} /> {tool.name}</span>;
              })}
            </div>
          </Section>

          <Section title="Evidence"><p style={{ margin: 0, fontSize: 13, color: "var(--o-text-2)" }}>{t.evidence}</p></Section>

          <Section title="Current Output"><p style={{ margin: 0, fontSize: 13, color: "var(--o-text-2)" }}>{t.output}</p></Section>

          <Section title="Next Action"><p style={{ margin: 0, fontSize: 13, color: "var(--o-text-2)" }}>{t.next}</p></Section>

          <button className="o-btn o-btn-primary" type="button" style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
            View Full Details
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: "var(--o-text-3)", marginBottom: 6 }}>{title}</div>
      {children}
    </div>
  );
}

function Legend({ color, label }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} /> {label}
    </span>
  );
}
