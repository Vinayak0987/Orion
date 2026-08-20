// F51 - session history. Backed by SQLite via /sessions.

const STATUS_CLASS = {
  completed: "pill pill-ok",
  partial: "pill pill-warn",
  timeout: "pill pill-warn",
  failed: "pill pill-bad",
  running: "pill",
  pending: "pill",
};

function whenLabel(iso) {
  if (!iso) return "";
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return "";
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h ago`;
  return then.toLocaleDateString();
}

export default function HistoryList({ sessions, activeId, loading, error, onOpen, onDelete, onRefresh }) {
  return (
    <aside className="panel sidebar">
      <div className="sidebar-head">
        <strong>History</strong>
        <button type="button" className="link" onClick={onRefresh}>
          Refresh
        </button>
      </div>

      {error && <p className="hint hint-warn">{error}</p>}
      {loading && <p className="hint">Loading…</p>}
      {!loading && !error && sessions.length === 0 && (
        <p className="hint">No runs yet. Generate a plan to see it here.</p>
      )}

      <ul className="history">
        {sessions.map((session) => (
          <li key={session.id} className={session.id === activeId ? "history-item active" : "history-item"}>
            <button type="button" className="history-open" onClick={() => onOpen(session.id)}>
              <span className="history-prompt">{session.raw_prompt}</span>
              <span className="history-meta">
                <span className={STATUS_CLASS[session.status] ?? "pill"}>{session.status}</span>
                {session.completeness_score != null && (
                  <span className="meta">{session.completeness_score}%</span>
                )}
                <span className="meta">{whenLabel(session.created_at)}</span>
              </span>
            </button>
            <button
              type="button"
              className="history-delete"
              title="Delete this run"
              aria-label={`Delete run: ${session.raw_prompt}`}
              onClick={() => onDelete(session.id)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
