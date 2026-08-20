// RunLog - loop run history, expandable JSON result payload.

import { useState } from "react";

const STATUS_ICON = {
  completed: "✓",
  failed: "✗",
  skipped_in_flight: "⏸",
  skipped_no_handler: "—",
};

export default function RunLog({ runs }) {
  if (!runs || runs.length === 0) {
    return <div className="panel empty">No loop runs recorded.</div>;
  }

  return (
    <div className="run-log">
      <h3>Loop Run Log</h3>
      <div className="run-list">
        {runs.map((run, i) => (
          <RunEntry key={i} run={run} />
        ))}
      </div>
    </div>
  );
}

function RunEntry({ run }) {
  const [expanded, setExpanded] = useState(false);
  const icon = STATUS_ICON[run.status] || "?";
  const statusClass = `run-status-${run.status}`;

  return (
    <div className={`run-entry ${statusClass}`}>
      <div className="run-header" onClick={() => setExpanded(!expanded)} role="button" tabIndex={0}
           onKeyDown={(e) => e.key === "Enter" && setExpanded(!expanded)}
           aria-expanded={expanded}>
        <span className="run-icon">{icon}</span>
        <span className="run-loop">{run.loop_id}</span>
        <span className={`run-badge ${statusClass}`}>{run.status}</span>
        <span className="run-duration">{run.duration_ms}ms</span>
        <span className="run-time">{run.started_at ? new Date(run.started_at).toLocaleString() : ""}</span>
      </div>
      {run.detail && <div className="run-detail">{run.detail}</div>}
      {expanded && run.result_json && (
        <pre className="run-result">{
          typeof run.result_json === "string"
            ? JSON.stringify(JSON.parse(run.result_json), null, 2)
            : JSON.stringify(run.result_json, null, 2)
        }</pre>
      )}
    </div>
  );
}
