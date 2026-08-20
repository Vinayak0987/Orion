// AuditTrail - per-decision passage through stages, including halts.

export default function AuditTrail({ trail, decisionId }) {
  if (!trail || trail.length === 0) {
    return <div className="panel empty">No audit trail{decisionId ? ` for ${decisionId}` : ""}.</div>;
  }

  return (
    <div className="audit-trail">
      <h3>Audit Trail{decisionId ? `: ${decisionId}` : ""}</h3>
      <table className="audit-table" aria-label="Decision audit trail">
        <thead>
          <tr>
            <th>#</th>
            <th>Stage</th>
            <th>Outcome</th>
            <th>Actor</th>
            <th>Rule</th>
            <th>Detail</th>
            <th>At</th>
          </tr>
        </thead>
        <tbody>
          {trail.map((row, i) => (
            <tr key={i} className={`audit-row audit-${row.outcome}`}>
              <td>{row.seq}</td>
              <td>{row.stage}</td>
              <td className={`audit-outcome outcome-${row.outcome}`}>{row.outcome}</td>
              <td>{row.actor}</td>
              <td>{row.rule_id ? <code>{row.rule_id}</code> : "—"}</td>
              <td>{row.detail || "—"}</td>
              <td className="audit-time">{row.at ? new Date(row.at).toLocaleString() : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
