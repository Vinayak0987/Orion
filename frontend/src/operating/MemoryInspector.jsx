// MemoryInspector - pick a department, see its four typed stores.
// Makes the isolation legible: a department's store shows only its own entries.

import { useCallback, useState } from "react";
import { api } from "../api";

const DEPARTMENTS = ["strategy", "finance", "branding", "marketing", "operations"];

export default function MemoryInspector({ companyId }) {
  const [dept, setDept] = useState("marketing");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (department) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.operating.memory(companyId, department);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  const handleChange = useCallback((e) => {
    const d = e.target.value;
    setDept(d);
    load(d);
  }, [load]);

  // Load on first render
  useState(() => { load(dept); });

  return (
    <div className="memory-inspector">
      <h3>Memory Inspector</h3>
      <p className="memory-note">
        Each department sees <strong>only its own</strong> memory. Isolation is enforced in
        the SQL — there is no code path by which one department's query can surface
        another's entries.
      </p>
      <div className="memory-controls">
        <label htmlFor="memory-dept">Department: </label>
        <select id="memory-dept" value={dept} onChange={handleChange}>
          {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {loading && <div className="loading">Loading…</div>}
      {error && <div className="error-msg">{error}</div>}

      {data && (
        <>
          <div className="memory-counts">
            <h4>Counts by type</h4>
            {Object.keys(data.counts).length === 0 ? (
              <p className="meta">No memories stored yet.</p>
            ) : (
              <ul className="memory-count-list">
                {Object.entries(data.counts).map(([type, count]) => (
                  <li key={type}><strong>{type}:</strong> {count}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="memory-entries">
            <h4>Recent entries</h4>
            {(!data.entries || data.entries.length === 0) ? (
              <p className="meta">No entries.</p>
            ) : (
              <table className="memory-table" aria-label={`${dept} memory entries`}>
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Content</th>
                    <th>Confidence</th>
                    <th>Retrievals</th>
                  </tr>
                </thead>
                <tbody>
                  {data.entries.map((entry, i) => (
                    <tr key={i}>
                      <td>{entry.memory_type}</td>
                      <td className="memory-content">{entry.content}</td>
                      <td>{entry.confidence?.toFixed(2) ?? "—"}</td>
                      <td>{entry.retrieval_count ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
