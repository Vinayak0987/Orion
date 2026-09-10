// AgentRoster - the agents this run would execute, grouped by orchestrator
// stage (design.md §6). Reuses the dept-list/dept classes from the progress
// panel so the two surfaces stay visually comparable.

export default function AgentRoster({ report }) {
  const agents = report.agents ?? [];
  const byStage = new Map();
  for (const agent of agents) {
    const key = `${agent.department}:${agent.department_stage}`;
    if (!byStage.has(key)) byStage.set(key, []);
    byStage.get(key).push(agent);
  }

  return (
    <div className="panel">
      <h3>
        Agent roster
        <span className="badge">
          {agents.length} agents ·{" "}
          {report.routing?.active_departments?.length ?? 0} departments
        </span>
      </h3>
      <p className="hint">
        The exact agents this run would execute, in execution order. Stages run
        sequentially; agents inside a stage run in parallel.
      </p>
      {[...byStage.entries()].map(([key, stageAgents]) => {
        const [department, stageIndex] = key.split(":");
        return (
          <div key={key} style={{ marginTop: 12 }}>
            <div className="dept-status">
              {department} · stage {stageIndex} · {stageAgents[0].execution}
            </div>
            <ul className="dept-list">
              {stageAgents.map((agent) => (
                <li key={agent.agent_id} className="dept">
                  <span className="dept-symbol">•</span>
                  <span className="dept-name">
                    {agent.agent_id.replace(/_/g, " ")}
                  </span>
                  <span className="dept-status">
                    {agent.feature} · {agent.tier}
                  </span>
                  <span className="dept-status">
                    {agent.max_tokens} tokens
                    {agent.grounding
                      ? ` · ${agent.grounding.replace(/_/g, " ")}`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
      {(report.skipped_departments ?? []).length > 0 && (
        <p className="hint" style={{ marginTop: 12 }}>
          Skipped: {report.skipped_departments.join(", ")}.
        </p>
      )}
    </div>
  );
}
