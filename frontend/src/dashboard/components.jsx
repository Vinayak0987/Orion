import { Icon } from "./icons";

// ---- Status → badge class + tone mapping -------------------------------
const STATUS_TONE = {
  "In Progress": "blue",
  "Completed": "green",
  "Not Started": "gray",
  "Waiting": "gray",
  "Failed": "red",
  "Live": "green",
  "High": "red",
  "Medium": "amber",
  "Low": "green",
};

export function Badge({ children, tone }) {
  const cls = tone ?? STATUS_TONE[children] ?? "gray";
  return <span className={`o-badge o-badge-${cls}`}>{children}</span>;
}

export function Progress({ value }) {
  return (
    <div className="o-progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <i style={{ width: `${value}%` }} />
    </div>
  );
}

// ---- Circular progress ring (inline SVG, no chart lib) -----------------
export function Ring({ value, size = 58, stroke = 5 }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - value / 100);
  return (
    <span className="o-ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--o-panel-3)" strokeWidth={stroke} />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="var(--o-accent)" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={off}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <span className="o-ring-label">{value}%</span>
    </span>
  );
}

// ---- Radial agent network (Dashboard 3.1) ------------------------------
// A center "Orion AI Workforce" node with department nodes evenly placed on a
// ring, connected by lines. Pure inline SVG.
export function AgentNetwork({ nodes }) {
  const W = 380, H = 340, cx = W / 2, cy = H / 2, R = 118;
  const placed = nodes.map((n, i) => {
    const angle = (Math.PI * 2 * i) / nodes.length - Math.PI / 2;
    return { ...n, x: cx + R * Math.cos(angle), y: cy + R * Math.sin(angle) };
  });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="300" role="img" aria-label="Live agent network">
      {placed.map((n) => (
        <line key={`l-${n.id}`} x1={cx} y1={cy} x2={n.x} y2={n.y} stroke="var(--o-border)" strokeWidth="1" />
      ))}
      {placed.map((n) => (
        <g key={n.id}>
          <circle cx={n.x} cy={n.y} r="20" fill="var(--o-panel-3)" stroke="var(--o-border)" strokeWidth="1" />
          <circle cx={n.x} cy={n.y} r="4" fill="var(--o-accent)" />
          <text x={n.x} y={n.y + 34} textAnchor="middle" fontSize="11" fill="var(--o-text-2)">{n.label}</text>
        </g>
      ))}
      <circle cx={cx} cy={cy} r="38" fill="var(--o-bg-2)" stroke="var(--o-accent)" strokeWidth="1.4" />
      <circle cx={cx} cy={cy} r="38" fill="var(--o-accent-dim)" />
      <text x={cx} y={cy - 3} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--o-text)">Orion</text>
      <text x={cx} y={cy + 12} textAnchor="middle" fontSize="9.5" fill="var(--o-text-2)">AI Workforce</text>
    </svg>
  );
}

// ---- Small tinted icon bubble ------------------------------------------
export function IcoBubble({ name, tone = "gray", s = 16 }) {
  const Glyph = Icon[name] ?? Icon.activity;
  const toneColor = {
    green: "var(--o-accent)", red: "var(--o-danger)",
    amber: "var(--o-warn)", blue: "var(--o-accent-2)", gray: "var(--o-text-2)",
  }[tone];
  return (
    <span className="o-list-ico" style={{ color: toneColor }}>
      <Glyph s={s} />
    </span>
  );
}
