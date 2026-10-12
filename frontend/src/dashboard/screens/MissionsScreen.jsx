import { useState } from "react";
import { Icon } from "../icons";
import { Badge, Progress } from "../components";
import { MISSIONS, MISSION_TABS } from "../mockData";

const FILTERS = ["Status", "Priority", "Department", "Owner", "Date"];

export default function MissionsScreen({ onOpenMission }) {
  const [activeTab, setActiveTab] = useState(0);
  const [selected, setSelected] = useState(MISSIONS[0]);

  return (
    <div className="o-fade">
      <div className="o-page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Missions</h1>
          <p>Plan, track, and manage all your missions.</p>
        </div>
        <button className="o-btn o-btn-primary" type="button"><Icon.plus s={16} /> New Mission</button>
      </div>

      {/* Category tabs + search */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, gap: 12 }}>
        <div className="o-filter-tabs">
          {MISSION_TABS.map((t, i) => (
            <button key={t} className={`o-tab${activeTab === i ? " active" : ""}`} onClick={() => setActiveTab(i)} type="button">{t}</button>
          ))}
        </div>
        <div className="o-search" style={{ maxWidth: 220, height: 34 }}>
          <Icon.search s={15} />
          <input placeholder="Search missions…" aria-label="Search missions" />
        </div>
      </div>

      {/* Column filters */}
      <div className="o-filter-tabs" style={{ marginBottom: 14 }}>
        {FILTERS.map((f) => (
          <button key={f} className="o-select" type="button">{f} ▾</button>
        ))}
      </div>

      {/* Table */}
      <div className="o-card" style={{ padding: 4 }}>
        <table className="o-table">
          <thead>
            <tr>
              <th style={{ width: 30 }}>#</th>
              <th>Mission / Objective</th>
              <th>Type</th>
              <th>Agents</th>
              <th>Progress</th>
              <th>Status</th>
              <th>Last Activity</th>
            </tr>
          </thead>
          <tbody>
            {MISSIONS.map((m) => (
              <tr
                key={m.id}
                className={selected?.id === m.id ? "selected" : ""}
                onClick={() => setSelected(m)}
                onDoubleClick={() => onOpenMission?.(m)}
              >
                <td style={{ color: "var(--o-text-3)" }}>{m.id}</td>
                <td>
                  <div style={{ fontWeight: 500 }}>{m.name}</div>
                  <div style={{ fontSize: 12, color: "var(--o-text-3)" }}>{m.sub}</div>
                </td>
                <td>{m.type}</td>
                <td>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--o-text-2)" }}>
                    <Icon.agents s={14} /> {m.agents}
                  </span>
                </td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Progress value={m.progress} />
                    <span style={{ fontSize: 12, color: "var(--o-text-2)", minWidth: 32 }}>{m.progress}%</span>
                  </div>
                </td>
                <td><Badge>{m.status}</Badge></td>
                <td style={{ color: "var(--o-text-3)" }}>{m.last}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer: count + pager */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "14px 0 20px" }}>
        <span style={{ fontSize: 12.5, color: "var(--o-text-3)" }}>Showing 1-8 of 12 missions</span>
        <div className="o-pager">
          <button type="button"><Icon.chevronLeft s={15} /></button>
          <button type="button" className="active">1</button>
          <button type="button">2</button>
          <button type="button">3</button>
          <button type="button"><Icon.chevronRight s={15} /></button>
        </div>
      </div>

      {/* Selected mission preview flow */}
      <div className="o-card">
        <div className="o-card-head"><h3>Selected Mission Preview</h3></div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <div className="o-tree-node"><Icon.command s={14} /> Orion</div>
          <Icon.chevronRight s={15} />
          <FlowStep icon="missions" label="Research" tasks="3 tasks" />
          <Icon.chevronRight s={15} />
          <FlowStep icon="trend" label="Analysis" tasks="4 tasks" />
          <Icon.chevronRight s={15} />
          <FlowStep icon="rocket" label="Execution" tasks="3 tasks" />
        </div>
      </div>
    </div>
  );
}

function FlowStep({ icon, label, tasks }) {
  const Glyph = Icon[icon] ?? Icon.agents;
  return (
    <div style={{ textAlign: "center" }}>
      <div className="o-tree-node" style={{ flexDirection: "column", padding: "10px 16px", gap: 4 }}>
        <Glyph s={18} />
        <span style={{ fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ fontSize: 11.5, color: "var(--o-text-3)", marginTop: 5 }}>{tasks}</div>
    </div>
  );
}
