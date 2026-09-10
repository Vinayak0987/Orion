// EstimatesPanel - the quota-honesty line (design.md §4).
// Every number is an upper bound, labelled as one.

export default function EstimatesPanel({ report }) {
  const estimates = report.estimates ?? {};
  return (
    <div className="panel">
      <h3>Estimates (upper bound)</h3>
      <table className="kv">
        <tbody>
          <tr>
            <th>Intent classification calls</th>
            <td>{estimates.intent_llm_calls ?? "—"}</td>
          </tr>
          <tr>
            <th>Agent calls</th>
            <td>{estimates.agent_llm_calls ?? "—"}</td>
          </tr>
          <tr>
            <th>Max completion tokens</th>
            <td>{(estimates.max_completion_tokens ?? 0).toLocaleString()}</td>
          </tr>
        </tbody>
      </table>
      <p className="hint">
        Upper bound, not a prediction. Repair rounds and fallback retries are
        excluded and cost extra. Confirming is free; the run itself spends the
        full pipeline.
      </p>
    </div>
  );
}
