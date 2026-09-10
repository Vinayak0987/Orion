// InferencesPanel - the §6 provenance array: how each key intent field was
// derived, and which fields still need operator confirmation.

const STATUS_LABELS = {
  confirmed: "confirmed",
  inferred: "inferred",
  "needs-confirmation": "needs confirmation",
};

export default function InferencesPanel({ report }) {
  const inferences = report.inferences ?? [];
  if (inferences.length === 0) return null;

  return (
    <div className="panel">
      <h3>Intent inferences</h3>
      <p className="hint">
        How each key field was derived. Fields marked “needs confirmation” carry
        a matching warning above.
      </p>
      <table className="kv">
        <tbody>
          {inferences.map((entry) => (
            <tr key={entry.label}>
              <th>{entry.label.replace(/_/g, " ")}</th>
              <td>
                <strong>{entry.value ?? "—"}</strong>{" "}
                <span className="meta">
                  ({STATUS_LABELS[entry.status] ?? entry.status})
                </span>
                <div className="hint">
                  {entry.rationale}
                  {entry.sourceLabels.length > 0 &&
                    ` — via ${entry.sourceLabels.join(", ")}`}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
