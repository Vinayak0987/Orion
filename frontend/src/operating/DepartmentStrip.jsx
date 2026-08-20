// DepartmentStrip - five cards with objective, proxy and anchor side by side.

export default function DepartmentStrip({ departments, schedule }) {
  if (!departments || departments.length === 0) {
    return <div className="panel empty">No department data.</div>;
  }

  // Build a lookup from schedule data for last-run info
  const scheduleMap = {};
  if (schedule) {
    for (const s of schedule) {
      scheduleMap[s.loop_id] = s;
    }
  }

  return (
    <div className="department-strip">
      {departments.map((dept) => {
        const sched = scheduleMap[dept.name];
        return (
          <div key={dept.name} className="dept-card">
            <h4 className="dept-name">{dept.name}</h4>
            <p className="dept-objective">{dept.objective}</p>
            <div className="dept-metrics">
              <div className="dept-metric dept-proxy">
                <span className="dept-metric-label">proxy</span>
                <span className="dept-metric-value">
                  {dept.proxy_metric.replace(/_/g, " ")}
                </span>
              </div>
              <div className="dept-metric dept-anchor">
                <span className="dept-metric-label">🔒 anchor</span>
                <span className="dept-metric-value">
                  {dept.serves_anchor.replace(/_/g, " ")}
                </span>
              </div>
            </div>
            {sched && (
              <div className="dept-schedule">
                <span className="dept-last-run">
                  {sched.last_run_at
                    ? `last: ${new Date(sched.last_run_at).toLocaleString()}`
                    : "not yet run"}
                </span>
                <span className="dept-run-count">runs: {sched.run_count}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
