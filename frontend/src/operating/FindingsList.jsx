// FindingsList - open findings worst-first with severity, kind, anchor cited.
// Every finding must cite an anchor movement; if one doesn't, surface it as a bug.

const SEVERITY_COLORS = {
  critical: "var(--bad)",
  high: "var(--warn)",
  medium: "var(--primary)",
  low: "var(--muted)",
};

function SeverityChip({ severity }) {
  return (
    <span
      className="severity-chip"
      style={{ background: SEVERITY_COLORS[severity] || "var(--muted)", color: "#fff" }}
      aria-label={`severity: ${severity}`}
    >
      {severity.toUpperCase()}
    </span>
  );
}

export default function FindingsList({ findings }) {
  if (!findings || findings.length === 0) {
    return (
      <div className="panel empty">
        No findings. Every claim in this period is supported by a matching anchor movement.
      </div>
    );
  }

  return (
    <div className="findings-list">
      <h3>Open Findings</h3>
      <table className="findings-table" aria-label="Monitor findings">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Kind</th>
            <th>Department</th>
            <th>Anchor</th>
            <th>Delta</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, i) => (
            <tr key={i} className={`finding-row finding-${f.severity}`}>
              <td><SeverityChip severity={f.severity} /></td>
              <td className="finding-kind">{f.kind.replace(/_/g, " ")}</td>
              <td>{f.department}</td>
              <td>
                {f.anchor ? (
                  <span className="anchor-ref">🔒 {f.anchor.replace(/_/g, " ")}</span>
                ) : (
                  <span className="finding-bug" title="Bug: finding has no anchor citation">⚠️ uncited</span>
                )}
              </td>
              <td className={f.anchor_delta < 0 ? "delta-neg" : "delta-pos"}>
                {f.anchor_delta != null ? (f.anchor_delta > 0 ? "+" : "") + f.anchor_delta.toFixed(2) : "—"}
              </td>
              <td className="finding-message">{f.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
