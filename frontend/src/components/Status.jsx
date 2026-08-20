// F52 - error, degradation and partial-result surfaces.
//
// Three distinct situations, deliberately shown differently:
//   backend unreachable   nothing will work; say so plainly
//   backend degraded      it will work but with weaker grounding
//   run failed            keep whatever completed, offer a retry

export function HealthBanner({ health, error }) {
  if (error) {
    return (
      <div className="callout callout-bad">
        <strong>Cannot reach the backend.</strong> {error}
        <div className="hint">
          Start it with <code>uvicorn app.main:app --port 8080</code> from the{" "}
          <code>backend</code> directory, or <code>docker compose up</code>.
        </div>
      </div>
    );
  }
  if (!health) return null;

  const notes = [];
  const grounding = health.grounding ?? {};
  if (grounding.competitor_source === "llm_inferred") {
    notes.push("Competitors will be recalled by the model, not verified against a places database.");
  } else if (grounding.competitor_source === "openstreetmap") {
    notes.push("Competitors come from OpenStreetMap, which carries no ratings or review counts.");
  }
  if (grounding.market_research_source === "llm_inferred") {
    notes.push("Market research will be model recall rather than live web search.");
  }
  if (health.pdf_export && !health.pdf_export.available) {
    notes.push("PDF export is unavailable; use the HTML report and print to PDF.");
  }
  if (!health.knowledge_cache?.enabled) {
    notes.push("Result caching is off, so repeat runs will re-query the external APIs.");
  }

  const providers = Object.entries(health.llm_providers ?? {})
    .filter(([, info]) => info.available)
    .map(([name]) => name);

  return (
    <div className={notes.length ? "callout callout-info" : "callout callout-ok"}>
      <strong>Backend {health.status}</strong>
      <span className="meta">
        {" "}
        · LLM: {providers.join(", ") || "none available"} · competitors:{" "}
        {(grounding.competitor_source ?? "—").replace(/_/g, " ")} · RQ3 arm: {grounding.rq3_arm ?? "—"}
      </span>
      {notes.length > 0 && (
        <ul className="bullets">
          {notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ErrorState({ message, kind, onRetry, partial }) {
  const title =
    kind === "validation"
      ? "That prompt needs a little more detail"
      : kind === "transport"
        ? "Connection problem"
        : "Generation failed";

  return (
    <div className={kind === "validation" ? "callout callout-warn" : "callout callout-bad"}>
      <strong>{title}</strong>
      <p>{message}</p>
      {partial && (
        <p className="hint">
          Partial results from the departments that finished are shown below.
        </p>
      )}
      {onRetry && kind !== "validation" && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
