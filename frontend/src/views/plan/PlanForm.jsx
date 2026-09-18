// PlanForm - prompt entry for the Planning Report flow.
// Reuses PromptForm's field styling and interaction conventions.

import { useState } from "react";

const MIN = 10;
const MAX = 500;

export default function PlanForm({ onSubmit, building }) {
  const [prompt, setPrompt] = useState("");
  const [forceAll, setForceAll] = useState(false);

  const trimmed = prompt.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN;
  const canSubmit = trimmed.length >= MIN && trimmed.length <= MAX && !building;

  function submit(event) {
    event.preventDefault();
    if (canSubmit) onSubmit(trimmed, forceAll);
  }

  return (
    <form className="panel" onSubmit={submit}>
      <label className="field-label" htmlFor="plan-prompt">
        Describe the business you want to plan
      </label>
      <textarea
        id="plan-prompt"
        className="prompt-input"
        rows={3}
        maxLength={MAX}
        value={prompt}
        disabled={building}
        placeholder="e.g. Ice cream shop in Andheri West, ₹15L budget"
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          // Enter submits; Shift+Enter adds a newline (PromptForm convention).
          if (event.key === "Enter" && !event.shiftKey) submit(event);
        }}
        aria-describedby="plan-prompt-help"
      />
      <div className="prompt-row">
        <span id="plan-prompt-help" className={tooShort ? "hint hint-warn" : "hint"}>
          {tooShort
            ? `At least ${MIN} characters — add a location and budget if you can.`
            : "Building the report costs at most one classification call."}
        </span>
      </div>
      <div className="prompt-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={forceAll}
            disabled={building}
            onChange={(event) => setForceAll(event.target.checked)}
          />
          Plan all five departments
          <span className="hint"> (disables dynamic routing — the RQ2 control arm)</span>
        </label>
        <button type="submit" className="primary" disabled={!canSubmit}>
          {building ? "Building report…" : "Build planning report"}
        </button>
      </div>
    </form>
  );
}
