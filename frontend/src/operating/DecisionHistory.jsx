// DecisionHistory - all decisions with state, risk, who decided, and blocking rule ids.

export default function DecisionHistory({ decisions }) {
  if (!decisions || decisions.length === 0) {
    return <div className="panel empty">No decision history.</div>;
  }

  return (
    <div className="decision-history">
      <h3>Decision History</h3>
      <table className="decision-table" aria-label="Decision history">
        <thead>
          <tr>
            <th>ID</th>
            <th>Department</th>
            <th>Kind</th>
            <th>State</th>
            <th>Risk</th>
            <th>Decided by</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          {decisions.map((d) => (
            <tr key={d.id} className={`decision-row decision-${d.state}`}>
              <td className="decision-id">{d.id}</td>
              <td>{d.department}</td>
              <td>{d.action_kind}</td>
              <td>
                <span className={`state-badge state-${d.state}`}>{d.state}</span>
              </td>
              <td className={`risk-${d.risk}`}>{d.risk}</td>
              <td>{d.decided_by || "—"}</td>
              <td className="decision-reason">{d.reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
