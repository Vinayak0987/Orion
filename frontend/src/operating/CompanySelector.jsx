// CompanySelector - lets visitors pick which company to inspect.
// Also provides a "seed the demo" button that triggers the manual tick endpoint.

import { useCallback, useState } from "react";
import { api } from "../api";

const DEFAULT_COMPANY = "demo-icecream-andheri";

export default function CompanySelector({ companyId, onChange }) {
  const [input, setInput] = useState(companyId || DEFAULT_COMPANY);
  const [ticking, setTicking] = useState(false);
  const [tickResult, setTickResult] = useState(null);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (input.trim()) onChange(input.trim());
  }, [input, onChange]);

  const handleTick = useCallback(async () => {
    setTicking(true);
    setTickResult(null);
    try {
      const runs = await api.operating.tick(companyId || DEFAULT_COMPANY);
      setTickResult(`${runs.length} loop(s) fired`);
    } catch (err) {
      setTickResult(`Error: ${err.message}`);
    } finally {
      setTicking(false);
    }
  }, [companyId]);

  return (
    <div className="company-selector">
      <form onSubmit={handleSubmit} className="company-form">
        <label htmlFor="company-id" className="company-label">Company:</label>
        <input
          id="company-id"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="company-input"
          placeholder="e.g. demo-icecream-andheri"
        />
        <button type="submit" className="btn">Load</button>
        <button
          type="button"
          onClick={handleTick}
          disabled={ticking}
          className="btn"
          title="Run due loops once (manual tick for demonstrations)"
        >
          {ticking ? "Ticking…" : "⏩ Manual Tick"}
        </button>
        {tickResult && <span className="tick-result">{tickResult}</span>}
      </form>
      <p className="company-hint">
        Seed data with: <code>python -m scripts.autonomy_demo --days 90</code>
      </p>
    </div>
  );
}

export { DEFAULT_COMPANY };
