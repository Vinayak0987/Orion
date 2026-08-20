// F48 - live agent progress from the WebSocket stream.

const DEPARTMENTS = ["strategy", "finance", "branding", "marketing", "operations"];

const STAGE_LABEL = {
  strategy: "Stage 1",
  finance: "Stage 2",
  branding: "Stage 2",
  marketing: "Stage 2",
  operations: "Stage 3",
};

const PRE_FLIGHT = {
  session_started: "Starting run",
  intent_resolved: "Intent classified",
  routing_resolved: "Departments selected",
};

function statusOf(department, events) {
  let status = "pending";
  for (const event of events) {
    if (event.department !== department) continue;
    if (event.event === "department_started") status = "running";
    if (event.event === "department_completed") status = "done";
    if (event.event === "department_failed") status = "failed";
  }
  return status;
}

const SYMBOL = { pending: "○", running: "◐", done: "●", failed: "×" };

export default function ProgressPanel({ events, elapsedSeconds, skipped }) {
  const last = events[events.length - 1];
  const completed = last?.completed ?? 0;
  const total = last?.total ?? 5;
  const percent = total ? Math.round((completed / total) * 100) : 0;

  const preFlight = events
    .filter((event) => PRE_FLIGHT[event.event])
    .map((event) => ({ label: PRE_FLIGHT[event.event], detail: event.detail }));

  const active = DEPARTMENTS.filter((department) => !skipped.includes(department));

  return (
    <div className="panel">
      <div className="progress-head">
        <strong>
          Generating — {completed} of {total} departments
        </strong>
        <span className="meta">{elapsedSeconds.toFixed(1)}s elapsed</span>
      </div>

      <div className="progress-track" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>

      <ul className="preflight">
        {preFlight.map((step) => (
          <li key={step.label}>
            <span className="tick">●</span> {step.label}
            {step.detail && <span className="meta"> — {step.detail}</span>}
          </li>
        ))}
      </ul>

      <ul className="dept-list">
        {active.map((department) => {
          const status = statusOf(department, events);
          return (
            <li key={department} className={`dept dept-${status}`}>
              <span className="dept-symbol">{SYMBOL[status]}</span>
              <span className="dept-name">{department}</span>
              <span className="meta">{STAGE_LABEL[department]}</span>
              <span className="dept-status">{status}</span>
            </li>
          );
        })}
        {skipped.map((department) => (
          <li key={department} className="dept dept-skipped">
            <span className="dept-symbol">–</span>
            <span className="dept-name">{department}</span>
            <span className="meta">skipped by dynamic routing</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
