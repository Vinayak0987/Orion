// ReadinessBanner - the stop/proceed verdict (design.md §7).
// blocked = stop + blocker list; ready = proceed; expired = rebuild.
// Reuses the existing callout classes - no new visual language.

export default function ReadinessBanner({ report }) {
  if (report.status === "blocked") {
    return (
      <div className="callout callout-bad" role="alert">
        <strong>Blocked — this plan cannot run yet.</strong>
        <ul className="bullets">
          {report.blockers.map((blocker) => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
        <p className="hint">
          Fix the blocker above, then build a new report. The full plan below
          shows what is being gated and why.
        </p>
      </div>
    );
  }
  if (report.status === "ready") {
    return (
      <div className="callout callout-ok">
        <strong>Ready.</strong> No hard blockers. Confirm below to hand off to
        the run.
      </div>
    );
  }
  if (report.status === "expired") {
    return (
      <div className="callout callout-warn" role="alert">
        <strong>Expired.</strong> This report is older than 24 hours. Build a
        new report before running.
      </div>
    );
  }
  return (
    <div className="callout callout-info">
      <strong>Status: {report.status}.</strong>
      {report.status === "executed" && report.executed_session_id && (
        <span className="meta"> Session {report.executed_session_id} ran this plan.</span>
      )}
    </div>
  );
}
