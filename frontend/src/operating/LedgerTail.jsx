// LedgerTail - newest-first ledger entries. States visibly that this is append-only.

export default function LedgerTail({ entries }) {
  if (!entries || entries.length === 0) {
    return <div className="panel empty">No ledger entries. The company has not recorded any events.</div>;
  }

  return (
    <div className="ledger-tail">
      <h3>Ledger</h3>
      <p className="ledger-note">
        This ledger is <strong>append-only</strong>. Entries cannot be edited or deleted —
        the database enforces this with triggers, not with application code.
      </p>
      <table className="ledger-table" aria-label="Append-only ledger entries">
        <thead>
          <tr>
            <th>Seq</th>
            <th>Kind</th>
            <th>Department</th>
            <th>Actor</th>
            <th>Amount / Qty</th>
            <th>Memo</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.seq} className={`ledger-row ledger-${e.kind}`}>
              <td className="ledger-seq">{e.seq}</td>
              <td>{e.kind.replace(/_/g, " ")}</td>
              <td>{e.department}</td>
              <td>{e.actor}</td>
              <td className="ledger-amount">
                {e.amount_minor > 0
                  ? `₹${(e.amount_minor / 100).toLocaleString("en-IN")}`
                  : e.quantity > 0
                  ? e.quantity
                  : "—"}
              </td>
              <td className="ledger-memo">{e.memo || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
