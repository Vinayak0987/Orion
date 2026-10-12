import { Icon } from "../icons";
import { Badge, AgentNetwork, IcoBubble } from "../components";
import {
  KPIS, AGENT_NETWORK, RECENT_ACTIVITY, KEY_INSIGHTS, PENDING_APPROVALS, GREETING_DATE,
} from "../mockData";

function Kpi({ icon, label, value, delta, up, plain }) {
  const Glyph = Icon[icon] ?? Icon.activity;
  return (
    <div className="o-card o-kpi">
      <div className="o-kpi-top">
        <span className="o-kpi-ico"><Glyph s={17} /></span>
        <span>{label}</span>
      </div>
      <div className="o-kpi-val">{value}</div>
      <div className={`o-kpi-delta ${plain ? "" : up ? "o-up" : "o-down"}`}>
        {plain ? delta : `${delta} vs last week`}
      </div>
    </div>
  );
}

export default function DashboardScreen({ user = "Abhishek" }) {
  return (
    <div className="o-fade">
      {/* Greeting banner */}
      <div className="o-card o-greet" style={{ marginBottom: 16 }}>
        <div>
          <h2>Good morning, {user}!</h2>
          <p>Your AI workforce is active. Here's what's happening today.</p>
        </div>
        <div className="o-date-pill">
          <strong>{GREETING_DATE}</strong>
          Let's build what's next.
        </div>
      </div>

      {/* KPI row */}
      <div className="o-kpis" style={{ marginBottom: 16 }}>
        {KPIS.map((k) => <Kpi key={k.label} {...k} />)}
      </div>

      {/* Middle row: agent network + recent activity */}
      <div className="o-grid" style={{ gridTemplateColumns: "1.4fr 1fr", marginBottom: 16 }}>
        <div className="o-card">
          <div className="o-card-head"><h3>Live Agent Network</h3></div>
          <AgentNetwork nodes={AGENT_NETWORK} />
        </div>

        <div className="o-card">
          <div className="o-card-head">
            <h3>Recent Activity</h3>
            <button className="o-link" type="button">View all →</button>
          </div>
          <div className="o-list">
            {RECENT_ACTIVITY.map((a, i) => (
              <div className="o-list-row" key={i}>
                <IcoBubble name={a.icon} tone={a.tone} />
                <div className="o-list-body">
                  <div className="o-list-title">{a.title}</div>
                  <div className="o-list-sub">{a.sub}</div>
                </div>
                <span className="o-list-time">{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom row: insights + pending approvals */}
      <div className="o-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div className="o-card">
          <div className="o-card-head"><h3>Key Insights</h3></div>
          {KEY_INSIGHTS.map((k, i) => (
            <div className="o-insight" key={i}>
              <IcoBubble name="trend" tone="green" />
              <div>
                <p>{k.text}</p>
                <span>{k.time}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="o-card">
          <div className="o-card-head">
            <h3>Pending Approvals</h3>
            <button className="o-link" type="button">View all →</button>
          </div>
          <div className="o-list">
            {PENDING_APPROVALS.map((p, i) => (
              <div className="o-list-row" key={i}>
                <IcoBubble name="approvals" tone={p.tone} />
                <div className="o-list-body">
                  <div className="o-list-title">{p.title}</div>
                  <div className="o-list-sub">{p.sub}</div>
                </div>
                <Badge tone={p.tone}>{p.level}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
