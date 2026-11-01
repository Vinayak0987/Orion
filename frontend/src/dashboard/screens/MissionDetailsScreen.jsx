import { useState, useEffect } from "react";
import { Icon } from "../icons";
import { Badge, Ring } from "../components";

export default function MissionDetailsScreen({ onBack, missionId }) {
  const [mission, setMission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    if (!missionId) {
      setError("No mission ID provided");
      setLoading(false);
      return;
    }

    async function fetchMission() {
      try {
        console.log("Fetching mission:", missionId);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
        
        const response = await fetch(`http://localhost:8081/missions/${missionId}`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log("Response status:", response.status);
        if (!response.ok) {
          throw new Error(`Failed to fetch mission: ${response.statusText}`);
        }
        const data = await response.json();
        console.log("Mission data:", data);
        setMission(data);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching mission:", err);
        setError(err.message);
        setLoading(false);
      }
    }

    fetchMission();
  }, [missionId]);

  if (loading) {
    return (
      <div className="o-fade" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 400 }}>
        <div style={{ color: "var(--o-text-3)" }}>Loading mission...</div>
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

  const m = mission;
  const t = m.tasks?.[0] || { name: "No tasks", agent: "N/A", status: "N/A", started: "N/A", percent: 0, description: "No tasks available", tools: [], evidence: "N/A", output: "N/A", next: "N/A" };

  return (
    <div className="o-fade">
      {/* Header */}
      <div className="o-card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <button className="o-icon-btn" type="button" onClick={onBack}><Icon.chevronLeft s={18} /></button>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h2 style={{ margin: 0, fontSize: 19 }}>{m.title || m.prompt}</h2>
              <Badge>{m.status}</Badge>
            </div>
            <p style={{ margin: "4px 0 0", color: "var(--o-text-2)", fontSize: 13.5 }}>{m.prompt}</p>
          </div>
          <Ring value={m.progress || 0} size={62} />
          <button className="o-btn" type="button">Actions <Icon.chevronDown s={15} /></button>
        </div>

        {/* Tabs */}
        <div className="o-tabs" style={{ marginTop: 16, marginBottom: 0 }}>
          {["Overview", "Tasks", "Agents", "Tools", "Evidence", "Results", "Trace"].map((label, i) => (
            <button key={label} className={tab === i ? "active" : ""} onClick={() => setTab(i)} type="button">{label}</button>
          ))}
        </div>
      </div>

      {/* Body: task list */}
      <div className="o-card">
        <div className="o-card-head">
          <h3>Tasks ({m.tasks?.length || 0})</h3>
        </div>
        {m.tasks && m.tasks.length > 0 ? (
          <table className="o-table">
            <thead>
              <tr>
                <th style={{ width: 30 }}>#</th>
                <th>Task</th>
                <th>Agent Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {m.tasks.map((task, idx) => (
                <tr key={task.id}>
                  <td style={{ color: "var(--o-text-3)" }}>{idx + 1}</td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{task.title}</div>
                  </td>
                  <td>{task.agent_type}</td>
                  <td><Badge>{task.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: 40, textAlign: "center", color: "var(--o-text-3)" }}>
            No tasks found for this mission
          </div>
        )}
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
