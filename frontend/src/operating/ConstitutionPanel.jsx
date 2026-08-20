// ConstitutionPanel - read-only display of the 7 hard constraints.
// These are code, not settings, and cannot be edited from the UI.

export default function ConstitutionPanel({ rules }) {
  if (!rules || rules.length === 0) {
    return <div className="panel empty">Constitution not loaded.</div>;
  }

  return (
    <div className="constitution-panel">
      <h3>Constitution</h3>
      <p className="constitution-note">
        These rules are <strong>code, not settings</strong>. They cannot be edited from
        the UI. No approval unlocks them — a hard constraint blocks at execution
        regardless of who approved the decision.
      </p>
      <div className="constitution-rules">
        {rules.map((rule) => (
          <div key={rule.id} className={`constitution-rule severity-${rule.severity}`}>
            <div className="rule-header">
              <code className="rule-id">{rule.id}</code>
              <span className={`rule-severity sev-${rule.severity}`}>{rule.severity}</span>
            </div>
            <p className="rule-description">{rule.description}</p>
            <p className="rule-rationale">{rule.rationale}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
