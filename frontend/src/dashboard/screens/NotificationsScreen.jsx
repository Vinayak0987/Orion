import { useState } from "react";
import { Icon } from "../icons";
import { IcoBubble } from "../components";
import { NOTIFICATIONS, NOTIF_TABS, NOTIF_DETAIL } from "../mockData";

export default function NotificationsScreen() {
  const [tab, setTab] = useState(0);
  const [sel, setSel] = useState(NOTIFICATIONS[0]);
  const d = NOTIF_DETAIL;

  return (
    <div className="o-fade">
      <div className="o-page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Notifications</h1>
          <p>Stay updated with your missions and system activity.</p>
        </div>
        <button className="o-btn o-btn-ghost" type="button"><Icon.check s={16} /> Mark all as read</button>
      </div>

      <div className="o-filter-tabs" style={{ marginBottom: 16 }}>
        {NOTIF_TABS.map((t, i) => (
          <button key={t} className={`o-tab${tab === i ? " active" : ""}`} onClick={() => setTab(i)} type="button">{t}</button>
        ))}
      </div>

      <div className="o-split o-split-wide">
        {/* List */}
        <div className="o-card" style={{ padding: 6 }}>
          <div className="o-list">
            {NOTIFICATIONS.map((n) => (
              <button
                key={n.id}
                className="o-list-row"
                onClick={() => setSel(n)}
                type="button"
                style={{
                  background: sel?.id === n.id ? "var(--o-panel-2)" : "none",
                  border: 0, width: "100%", textAlign: "left", borderRadius: 10, cursor: "pointer",
                }}
              >
                <IcoBubble name={n.icon} tone={n.tone} />
                <div className="o-list-body">
                  <div className="o-list-title" style={{ display: "flex", alignItems: "center", gap: 7 }}>
                    {n.title}
                    {n.unread && <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--o-accent-2)" }} />}
                  </div>
                  <div className="o-list-sub">{n.sub}</div>
                </div>
                <span className="o-list-time">{n.time}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Detail */}
        <div className="o-card">
          <div className="o-card-head">
            <h3>Notification Details</h3>
            <button className="o-link" type="button">Mark as unread</button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <IcoBubble name="missions" tone="blue" s={18} />
            <div>
              <div style={{ fontWeight: 600 }}>{d.title}</div>
              <div style={{ fontSize: 12, color: "var(--o-text-3)" }}>{d.time}</div>
            </div>
          </div>

          <p style={{ fontSize: 13, color: "var(--o-text-2)", marginTop: 0 }}>{d.body}</p>

          <div style={{ margin: "14px 0" }}>
            {d.meta.map(([k, v]) => (
              <div className="o-def" key={k}><span>{k}</span><strong>{v}</strong></div>
            ))}
          </div>

          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: "var(--o-text-3)", marginBottom: 6 }}>Details</div>
          <p style={{ fontSize: 13, color: "var(--o-text-2)", marginTop: 0 }}>{d.detail}</p>

          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.6, color: "var(--o-text-3)", margin: "16px 0 4px" }}>Task Progress</div>
          {d.bars.map((b) => (
            <div className="o-bar-row" key={b.label}>
              <div className="o-bar-head"><span>{b.label}</span><span>{b.pct}%</span></div>
              <div className="o-progress"><i style={{ width: `${b.pct}%` }} /></div>
            </div>
          ))}

          <button className="o-btn o-btn-primary" type="button" style={{ width: "100%", justifyContent: "center", marginTop: 14 }}>
            View Mission <Icon.chevronRight s={15} />
          </button>
        </div>
      </div>
    </div>
  );
}
