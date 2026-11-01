import { useState, useEffect } from "react";
import { Icon } from "../icons";
import { Badge, Progress } from "../components";
import { missionApi } from "../../missionApi";

const FILTERS = ["Status", "Priority", "Department", "Owner", "Date"];

export default function MissionsScreen({ onOpenMission }) {
  const [activeTab, setActiveTab] = useState(0);
  const [selected, setSelected] = useState(null);
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchMissions() {
      try {
        const data = await missionApi.missions(50);
        setMissions(data.missions || []);
        if (data.missions && data.missions.length > 0) {
          setSelected(data.missions[0]);
        }
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }

    fetchMissions();
  }, []);

  if (loading) {
    return (
      <div className="o-fade" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
        <div style={{ color: "var(--o-text-3)" }}>Loading missions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="o-fade" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
        <div style={{ color: "var(--o-danger)" }}>Error: {error}</div>
      </div>
    );
  }

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
          {["All", "Completed", "In Progress", "Failed"].map((t, i) => (
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
            {missions.map((m) => (
              <tr
                key={m.id}
                className={selected?.id === m.id ? "selected" : ""}
                onClick={() => setSelected(m)}
                onDoubleClick={() => onOpenMission?.(m)}
              >
                <td style={{ color: "var(--o-text-3)" }}>{m.id?.substring(0, 8)}</td>
                <td>
                  <div style={{ fontWeight: 500 }}>{m.title || m.prompt?.substring(0, 50)}</div>
                  <div style={{ fontSize: 12, color: "var(--o-text-3)" }}>{m.prompt?.substring(0, 80)}</div>
                </td>
                <td>{m.type || "N/A"}</td>
                <td>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--o-text-2)" }}>
                    <Icon.agents s={14} /> {m.agent_count || 0}
                  </span>
                </td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Progress value={m.progress || 0} />
                    <span style={{ fontSize: 12, color: "var(--o-text-2)", minWidth: 32 }}>{m.progress || 0}%</span>
                  </div>
                </td>
                <td><Badge>{m.status}</Badge></td>
                <td style={{ color: "var(--o-text-3)" }}>{new Date(m.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer: count + pager */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "14px 0 20px" }}>
        <span style={{ fontSize: 12.5, color: "var(--o-text-3)" }}>Showing {missions.length} missions</span>
      </div>
    </div>
  );
}
