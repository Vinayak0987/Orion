// F47 - single-prompt input. One field, no forms, no dropdowns.

import { useState } from "react";

const MIN = 10;
const MAX = 500;

const EXAMPLES = [
  "Ice cream shop in Andheri West, ₹15L budget",
  "Unisex salon in Bandra with 12 lakh investment",
  "Start an online tutoring platform for CBSE students",
  "Dental clinic near Dadar station, ₹25L",
];

export default function PromptForm({ onGenerate, running, forceAll, onForceAllChange }) {
  const [prompt, setPrompt] = useState("");

  const trimmed = prompt.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < MIN;
  const canSubmit = trimmed.length >= MIN && trimmed.length <= MAX && !running;

  function submit(event) {
    event.preventDefault();
    if (canSubmit) onGenerate(trimmed);
  }

  return (
    <form className="panel prompt-form" onSubmit={submit}>
      <label className="field-label" htmlFor="prompt">
        Describe the business you want to start
      </label>

      <textarea
        id="prompt"
        className="prompt-input"
        rows={3}
        maxLength={MAX}
        value={prompt}
        disabled={running}
        placeholder="e.g. Ice cream shop in Andheri West, ₹15L budget"
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          // Enter submits; Shift+Enter adds a newline.
          if (event.key === "Enter" && !event.shiftKey) submit(event);
        }}
        aria-describedby="prompt-help"
      />

      <div className="prompt-row">
        <span id="prompt-help" className={tooShort ? "hint hint-warn" : "hint"}>
          {tooShort
            ? `At least ${MIN} characters — add a location and budget if you can.`
            : "Include a location and a budget for the most accurate plan."}
        </span>
        <span className={trimmed.length > MAX - 50 ? "counter counter-warn" : "counter"}>
          {trimmed.length}/{MAX}
        </span>
      </div>

      <div className="prompt-row">
        <label className="checkbox">
          <input
            type="checkbox"
            checked={forceAll}
            disabled={running}
            onChange={(event) => onForceAllChange(event.target.checked)}
          />
          Run all five departments
          <span className="hint"> (disables dynamic routing — the RQ2 control arm)</span>
        </label>

        <button type="submit" className="primary" disabled={!canSubmit}>
          {running ? "Generating…" : "Generate business plan"}
        </button>
      </div>

      {!running && trimmed.length === 0 && (
        <div className="examples">
          <span className="hint">Try:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="chip"
              onClick={() => setPrompt(example)}
            >
              {example}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
