import { Icon } from "../icons";
import { Progress } from "../components";
import { CHAT_PLAN, RUNNING_AGENTS, QUICK_ACTIONS } from "../mockData";

function TreeNode({ label, meta }) {
  return (
    <div className="o-tree-node">
      <Icon.agents s={14} />
      <span>{label}</span>
      {meta && <small>{meta}</small>}
    </div>
  );
}

export default function CommandCenterScreen() {
  return (
    <div className="o-fade">
      <div className="o-page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Orion Command Center</h1>
          <p>Turn your ideas into real outcomes with AI agents.</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="o-select" type="button">GPT-4o ▾</button>
          <button className="o-btn o-btn-primary" type="button"><Icon.plus s={16} /> New Chat</button>
        </div>
      </div>

      <div className="o-grid" style={{ gridTemplateColumns: "1.3fr 1fr", alignItems: "start" }}>
        {/* Chat column */}
        <div>
          <div className="o-chat">
            <div className="o-msg" style={{ justifyContent: "flex-end" }}>
              <div className="o-msg-bubble" style={{ background: "var(--o-accent-dim)" }}>
                I want to open a cafe in Thane. Research locations, competitors, rent, pricing and create an execution plan.
                <div className="o-msg-time">10:24 AM</div>
              </div>
            </div>

            <div className="o-msg">
              <span className="o-msg-ico" style={{ color: "var(--o-accent)" }}><Icon.command s={17} /></span>
              <div className="o-msg-bubble">
                I'll help you build a comprehensive plan to open a cafe in Thane. Here's what I'll do:
                <ol>
                  {CHAT_PLAN.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
              </div>
            </div>

            {/* Running agents card */}
            <div className="o-agent-run">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <Icon.clock s={16} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>Creating dynamic plan…</div>
                    <div style={{ fontSize: 12, color: "var(--o-text-3)" }}>Deploying specialized agents and gathering real-time data</div>
                  </div>
                </div>
                <button className="o-btn o-btn-ghost" type="button"><Icon.stop s={14} /> Stop</button>
              </div>
              {RUNNING_AGENTS.map((a) => {
                const Glyph = Icon[a.icon] ?? Icon.agents;
                return (
                  <div className="o-agent-row" key={a.name}>
                    <span className="o-msg-ico" style={{ width: 28, height: 28 }}><Glyph s={15} /></span>
                    <div style={{ minWidth: 130 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 500 }}>{a.name}</div>
                      <div style={{ fontSize: 11.5, color: "var(--o-text-3)" }}>{a.status}</div>
                    </div>
                    <Progress value={a.pct} />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Composer */}
          <div className="o-composer" style={{ marginTop: 16 }}>
            <input placeholder="Type your message or objective…" aria-label="Message" />
            <button className="o-icon-btn" type="button"><Icon.paperclip s={17} /></button>
            <button className="o-btn o-btn-primary" type="button" style={{ padding: 9 }}><Icon.send s={16} /></button>
          </div>
          <div className="o-chips">
            {QUICK_ACTIONS.map((c) => <button className="o-chip" key={c} type="button">{c}</button>)}
            <button className="o-chip" type="button"><Icon.plus s={13} /></button>
          </div>
        </div>

        {/* Live agent tree */}
        <div className="o-card">
          <div className="o-card-head">
            <h3>Live Agent Tree <span style={{ color: "var(--o-text-3)", fontWeight: 400, fontSize: 12 }}>(Generating…)</span></h3>
            <button className="o-icon-btn" type="button"><Icon.x s={16} /></button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <span className="o-msg-ico" style={{ color: "var(--o-accent)" }}><Icon.command s={16} /></span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500 }}>Orion Planner</div>
                <div style={{ fontSize: 11.5, color: "var(--o-text-3)" }}>Decomposing objective…</div>
              </div>
            </div>

            <div style={{ paddingLeft: 14, borderLeft: "1px solid var(--o-border)", display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <TreeNode label="Research" meta="3 agents" />
                <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingLeft: 18, marginTop: 8 }}>
                  <TreeNode label="Location Research" />
                  <TreeNode label="Competitor Analysis" />
                  <TreeNode label="Market Analysis" />
                </div>
              </div>
              <div>
                <TreeNode label="Analysis" meta="2 agents" />
                <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingLeft: 18, marginTop: 8 }}>
                  <TreeNode label="Financial Model" />
                  <TreeNode label="Pricing Strategy" />
                  <TreeNode label="Demand Analysis" />
                </div>
              </div>
              <div>
                <TreeNode label="Execution" meta="2 agents" />
                <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingLeft: 18, marginTop: 8 }}>
                  <TreeNode label="Operations Plan" />
                  <TreeNode label="Legal & Compliance" />
                  <TreeNode label="Launch Strategy" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
