import { useState } from "react";
import { Icon } from "../icons";
import { Badge } from "../components";
import { APPROVAL_REQUESTS } from "../mockData";

const TABS = ["Pending (5)", "Approved (12)", "Rejected (2)", "All (19)"];

function RequestRow({ r, active, onClick }) {
  const Glyph = Icon[r.icon] ?? Icon.approvals;
  return (
    <button className={`o-req${active ? " active" : ""}`} onClick={onClick} type="button">
      <span className="o-list-ico" style={{ color: `var(--o-${r.tone === "amber" ? "warn" : r.tone === "red" ? "danger" : "accent"})` }}>
        <Glyph s={16} />
      </span>
      <div className="o-list-body">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <span className="o-list-title">{r.title}</span>
          <Badge tone={r.tone}>{r.level}</Badge>
        </div>
        <div className="o-list-sub">{r.agent}</div>
        <div className="o-list-sub">{r.context}</div>
      </div>
    </button>
  );
}

export default function ApprovalsScreen() {
  const [tab, setTab] = useState(0);
  const [sel, setSel] = useState(APPROVAL_REQUESTS[0]);

  return (
    <div className="o-fade">
      <div className="o-page-head">
        <h1>Approvals</h1>
        <p>Review and manage action requests from your AI agents.</p>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, gap: 12 }}>
        <div className="o-filter-tabs">
          {TABS.map((t, i) => (
            <button key={t} className={`o-tab${tab === i ? " active" : ""}`} onClick={() => setTab(i)} type="button">{t}</button>
          ))}
        </div>
        <button className="o-select" type="button">Filter ▾</button>
      </div>

      <div className="o-split">
        {/* Request list */}
        <div>
          {APPROVAL_REQUESTS.map((r) => (
            <RequestRow key={r.id} r={r} active={sel?.id === r.id} onClick={() => setSel(r)} />
          ))}
        </div>

        {/* Detail panel */}
        <div className="o-card">
          <div className="o-card-head">
            <h3>Approval Details</h3>
            <Badge tone={sel.tone}>{sel.level} Priority</Badge>
          </div>

          <div style={{ fontWeight: 600, fontSize: 15 }}>{sel.title}</div>
          <div style={{ fontSize: 12.5, color: "var(--o-text-3)", marginBottom: 16 }}>{sel.agent} · {sel.time}</div>

          <Block title="Business Context">
            <p style={{ margin: 0, fontSize: 13, color: "var(--o-text-2)" }}>{sel.context}</p>
          </Block>

          {sel.actions.length > 0 && (
            <Block title="Proposed Action">
              {sel.actions.map((a) => (
                <div className="o-def" key={a.label}><span>{a.label}</span><strong>{a.value}</strong></div>
              ))}
            </Block>
          )}

          {sel.impact.length > 0 && (
            <Block title="Expected Impact">
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--o-text-2)" }}>
                {sel.impact.map((i) => <li key={i} style={{ marginBottom: 4 }}>{i}</li>)}
              </ul>
            </Block>
          )}

          {sel.evidence.length > 0 && (
            <Block title="Supporting Evidence">
              {sel.evidence.map((e) => (
                <div className="o-file" key={e.name}>
                  <Icon.doc s={16} />
                  <span>{e.name}</span>
                  <small>{e.size}</small>
                </div>
              ))}
            </Block>
          )}

          <div className="o-actions-row">
            <button className="o-btn o-btn-danger" type="button" style={{ flex: 1, justifyContent: "center" }}>Reject</button>
            <button className="o-btn o-btn-ghost" type="button" style={{ flex: 1, justifyContent: "center" }}>Request Changes</button>
            <button className="o-btn o-btn-primary" type="button" style={{ flex: 1, justifyContent: "center" }}><Icon.check s={16} /> Approve</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Block({ title, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: "var(--o-text-3)", marginBottom: 8 }}>{title}</div>
      {children}
    </div>
  );
}
