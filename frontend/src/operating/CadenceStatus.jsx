// CadenceStatus - per-loop schedule state: cadence, last run, run count, in-flight.

export default function CadenceStatus({ schedule }) {
  if (!schedule || schedule.length === 0) {
    return <div className="panel empty">No schedule data.</div>;
  }

  function formatCadence(seconds) {
    if (!seconds) return "event-driven";
    if (seconds >= 86400 * 7) return `${Math.round(seconds / 86400 / 7)}w`;
    if (seconds >= 86400) return `${Math.round(seconds / 86400)}d`;
    if (seconds >= 3600) return `${Math.round(seconds / 3600)}h`;
    return `${seconds}s`;
  }

  return (
    <div className="cadence-status">
      <h3>Cadence Status</h3>
      <table className="cadence-table" aria-label="Loop cadence status">
        <thead>
          <tr>
            <th>Loop</th>
            <th>Kind</th>
            <th>Cadence</th>
            <th>Last Run</th>
            <th>Runs</th>
            <th>Handler</th>
            <th>In Flight</th>
          </tr>
        </thead>
        <tbody>
          {schedule.map((s) => (
            <tr key={s.loop_id} className={s.in_flight ? "loop-in-flight" : ""}>
              <td className="loop-id">{s.loop_id}</td>
              <td>{s.kind}</td>
              <td>{formatCadence(s.cadence_seconds)}</td>
              <td>{s.last_run_at ? new Date(s.last_run_at).toLocaleString() : "—"}</td>
              <td>{s.run_count}</td>
              <td>{s.has_handler ? "✓" : "✗"}</td>
              <td>{s.in_flight ? "⚡ running" : "idle"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
