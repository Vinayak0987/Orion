// landingVisuals — the reference's inline SVG icon sprite as a React component,
// an <Ic> helper that references a symbol by id, and the security shield +
// compliance badge SVGs. Ported 1:1 from orionai-landing.html.

// A single icon: <Ic n="arrow" /> renders <svg class="ic"><use href="#i-arrow"/></svg>
export function Ic({ n, className = "" }) {
  return (
    <svg className={`ic ${className}`.trim()} aria-hidden="true">
      <use href={`#i-${n}`} />
    </svg>
  );
}

// The hidden sprite of all symbols. Rendered once at the top of the page.
export function IconSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="gShield" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" style={{ stopColor: "var(--sh1)" }} />
          <stop offset="1" style={{ stopColor: "var(--sh2)" }} />
        </linearGradient>
      </defs>
      <symbol id="i-logo" viewBox="0 0 24 24"><ellipse cx="12" cy="12" rx="9" ry="3.6" /><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(60 12 12)" /><ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(120 12 12)" /></symbol>
      <symbol id="i-moon" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></symbol>
      <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></symbol>
      <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7" /></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" /></symbol>
      <symbol id="i-chev-r" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6" /></symbol>
      <symbol id="i-chev-d" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6" /></symbol>
      <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7.5" /><path d="m21 21-4.3-4.3" /></symbol>
      <symbol id="i-play-c" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="m10 8 6 4-6 4Z" /></symbol>
      <symbol id="i-play" viewBox="0 0 24 24"><path d="M7 4.5v15l12.5-7.5Z" /></symbol>
      <symbol id="i-doc" viewBox="0 0 24 24"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8" /></symbol>
      <symbol id="i-chart" viewBox="0 0 24 24"><path d="M3 3v18h18M18 17V9M13 17V5M8 17v-3" /></symbol>
      <symbol id="i-plan" viewBox="0 0 24 24"><rect x="8" y="2" width="8" height="4" rx="1" /><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M12 11h4M12 16h4M8 11h.01M8 16h.01" /></symbol>
      <symbol id="i-users" viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></symbol>
      <symbol id="i-trend" viewBox="0 0 24 24"><path d="M22 7 13.5 15.5 8.5 10.5 2 17M16 7h6v6" /></symbol>
      <symbol id="i-shield" viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /></symbol>
      <symbol id="i-shield-check" viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /><path d="m9 12 2 2 4-4" /></symbol>
      <symbol id="i-zap" viewBox="0 0 24 24"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" /></symbol>
      <symbol id="i-bot" viewBox="0 0 24 24"><path d="M12 8V4H8" /><rect width="16" height="12" x="4" y="8" rx="2" /><path d="M2 14h2M20 14h2M15 13v2M9 13v2" /></symbol>
      <symbol id="i-wrench" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></symbol>
      <symbol id="i-gauge" viewBox="0 0 24 24"><path d="m12 14 4-4M3.34 19a10 10 0 1 1 17.32 0" /></symbol>
      <symbol id="i-percent" viewBox="0 0 24 24"><path d="M19 5 5 19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></symbol>
      <symbol id="i-check-c" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" /></symbol>
      <symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></symbol>
      <symbol id="i-bag" viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18M16 10a4 4 0 0 1-8 0" /></symbol>
      <symbol id="i-activity" viewBox="0 0 24 24"><path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" /></symbol>
      <symbol id="i-landmark" viewBox="0 0 24 24"><path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2 20 7H4Z" /></symbol>
      <symbol id="i-home" viewBox="0 0 24 24"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M9 22V12h6v10" /></symbol>
      <symbol id="i-factory" viewBox="0 0 24 24"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z" /><path d="M17 18h1M12 18h1M7 18h1" /></symbol>
      <symbol id="i-cap" viewBox="0 0 24 24"><path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z" /><path d="M22 10v6M6 12.5V16a6 3 0 0 0 12 0v-3.5" /></symbol>
      <symbol id="i-bed" viewBox="0 0 24 24"><path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9" /></symbol>
      <symbol id="i-sparkles" viewBox="0 0 24 24"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /><path d="M19 15v4M17 17h4" /></symbol>
      <symbol id="i-workflow" viewBox="0 0 24 24"><rect width="8" height="8" x="3" y="3" rx="2" /><path d="M7 11v4a2 2 0 0 0 2 2h4" /><rect width="8" height="8" x="13" y="13" rx="2" /></symbol>
      <symbol id="i-todo" viewBox="0 0 24 24"><rect x="3" y="5" width="6" height="6" rx="1" /><path d="m3 17 2 2 4-4M13 6h8M13 12h8M13 18h8" /></symbol>
      <symbol id="i-plug" viewBox="0 0 24 24"><path d="M12 22v-5M9 8V2M15 8V2" /><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" /></symbol>
      <symbol id="i-db" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0" /></symbol>
      <symbol id="i-eye" viewBox="0 0 24 24"><path d="M2.06 12.35a1 1 0 0 1 0-.7 10.75 10.75 0 0 1 19.88 0 1 1 0 0 1 0 .7 10.75 10.75 0 0 1-19.88 0" /><circle cx="12" cy="12" r="3" /></symbol>
      <symbol id="i-layers" viewBox="0 0 24 24"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z" /><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65" /></symbol>
      <symbol id="i-lock" viewBox="0 0 24 24"><rect width="18" height="11" x="3" y="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></symbol>
      <symbol id="i-file-check" viewBox="0 0 24 24"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4M9 15l2 2 4-4" /></symbol>
      <symbol id="i-key" viewBox="0 0 24 24"><circle cx="7.5" cy="15.5" r="5.5" /><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3" /></symbol>
    </svg>
  );
}

// Security shield with layered lock (ported from the reference).
export function Shield() {
  return (
    <svg className="shield" viewBox="0 0 200 224" role="img" aria-label="Shield with a lock">
      <path d="M100 10 L176 38 V104 C176 154 144 192 100 212 C56 192 24 154 24 104 V38 Z" fill="url(#gShield)" stroke="var(--sh-stroke)" strokeWidth="1.5" />
      <path d="M100 26 L162 48 V104 C162 146 136 178 100 196 C64 178 38 146 38 104 V48 Z" fill="none" stroke="var(--sh-stroke)" strokeWidth="1" opacity=".55" />
      <rect x="74" y="98" width="52" height="42" rx="8" fill="#fff" fillOpacity=".92" />
      <path d="M84 98 V86 a16 16 0 0 1 32 0 V98" fill="none" stroke="#fff" strokeOpacity=".92" strokeWidth="7" strokeLinecap="round" />
      <circle cx="100" cy="116" r="5" style={{ fill: "var(--sh2)" }} />
      <rect x="98" y="118" width="4" height="12" rx="2" style={{ fill: "var(--sh2)" }} />
    </svg>
  );
}

// Compliance badges (SOC 2 / GDPR / ISO), ported from the reference.
export function Badges() {
  return (
    <div className="badges">
      <div className="badge">
        <svg viewBox="0 0 46 46" aria-hidden="true">
          <circle cx="23" cy="23" r="21" style={{ fill: "var(--soc-bg)" }} />
          <text x="23" y="27" textAnchor="middle" fontSize="11" fontWeight="700" fontFamily="Inter,sans-serif" style={{ fill: "var(--soc-fg)" }}>SOC</text>
        </svg>
        <b>SOC 2</b><small>Type II</small>
      </div>
      <div className="badge">
        <svg viewBox="0 0 46 46" aria-hidden="true">
          <circle cx="23" cy="23" r="21" fill="none" style={{ stroke: "var(--border2)" }} strokeWidth="1.5" />
          <circle cx="23" cy="23" r="14" fill="none" style={{ stroke: "var(--accent)" }} strokeWidth="3" strokeLinecap="round" strokeDasharray="0 7.33" />
          <circle cx="23" cy="23" r="7" fill="none" style={{ stroke: "var(--accent)" }} strokeWidth="1.3" />
        </svg>
        <b>GDPR</b><small>Compliant</small>
      </div>
      <div className="badge">
        <svg viewBox="0 0 46 46" aria-hidden="true">
          <circle cx="23" cy="23" r="21" fill="none" style={{ stroke: "var(--border2)" }} strokeWidth="1.5" />
          <circle cx="23" cy="23" r="15" fill="none" style={{ stroke: "var(--accent)" }} strokeWidth="2.5" />
          <circle cx="23" cy="23" r="6" style={{ fill: "var(--accent)" }} />
        </svg>
        <b>ISO</b><small>27001</small>
      </div>
    </div>
  );
}


// --------------------------------------------------------------------------- //
// CircuitWires — faint decorative "circuit board" traces + node dots used to
// fill section backgrounds (matching the wireframe's techy backdrop). Purely
// decorative; theme colour comes from --ring / --accent. `variant` picks a
// preset trace layout for different sections.
// --------------------------------------------------------------------------- //
const WIRE_VARIANTS = {
  // top-right corner traces (How It Works, Security)
  corner: {
    viewBox: "0 0 600 400",
    lines: [
      "M600 40 H470 Q450 40 450 60 V150",
      "M600 110 H520 Q505 110 505 125 V210",
      "M540 0 V70 Q540 90 560 90 H600",
    ],
    dots: [[450, 150], [505, 210], [560, 90], [470, 40]],
  },
  // symmetric side traces fanning from both edges (Hero)
  fan: {
    viewBox: "0 0 1200 500",
    lines: [
      "M0 120 H180 Q210 120 210 150 V250",
      "M1200 100 H1010 Q980 100 980 130 V230",
      "M0 380 H140 Q170 380 170 350 V280",
      "M1200 400 H1040 Q1010 400 1010 370 V300",
    ],
    dots: [[210, 250], [980, 230], [170, 280], [1010, 300]],
  },
  // arcs + nodes around a central circle (About orb)
  halo: {
    viewBox: "0 0 500 500",
    lines: [
      "M250 40 A210 210 0 0 1 460 250",
      "M250 460 A210 210 0 0 1 40 250",
      "M70 90 L140 160",
      "M430 410 L360 340",
    ],
    dots: [[250, 40], [460, 250], [40, 250], [250, 460], [140, 160], [360, 340]],
  },
};

export function CircuitWires({ variant = "corner", className = "" }) {
  const v = WIRE_VARIANTS[variant] || WIRE_VARIANTS.corner;
  return (
    <svg
      className={`lp-wires ${className}`.trim()}
      viewBox={v.viewBox}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      {v.lines.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="var(--ring)" strokeWidth="1" />
      ))}
      {v.dots.map(([cx, cy], i) => (
        <circle key={`d${i}`} cx={cx} cy={cy} r="3" fill="var(--accent)" opacity="0.5" />
      ))}
    </svg>
  );
}

