// ConfirmBar - the explicit confirm step that precedes any run (design.md §4).
// Confirming is free (no LLM call); it then hands off to #/generate carrying
// planning_report_id, where the operator starts the actual run.

export default function ConfirmBar({ report, confirming, onConfirm, error }) {
  if (report.status !== "ready") {
    return (
      <div className="panel">
        <h3>Run</h3>
        <p className="hint">
          {report.status === "blocked"
            ? "Confirm is unavailable while the plan is blocked."
            : `This report is ${report.status}; build a new report to run.`}
        </p>
      </div>
    );
  }
  return (
    <div className="panel">
      <h3>Run</h3>
      <p className="hint">
        Confirming is free (no LLM call). The run itself spends the full
        pipeline.
      </p>
      <button
        type="button"
        className="primary"
        disabled={confirming}
        onClick={onConfirm}
      >
        {confirming ? "Confirming…" : "Confirm and go to Generate"}
      </button>
      {error && <p className="hint hint-warn">{error}</p>}
    </div>
  );
}
