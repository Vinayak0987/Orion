import { useState } from "react";
import { Card } from "./ui/Card.jsx";
import {
  LAN_TITLE,
  LAN_CENTER,
  LAN_AGENTS,
  LAN_COLORS,
  LAN_ICONS,
  LAN_LAYOUT,
} from "../data/lanConfig.js";

export const LiveAgentNetwork = () => {
  const [hover, setHover] = useState(null);
  const L = LAN_LAYOUT;

  const items = LAN_AGENTS.map((a, i) => {
    const ang = ((L.startAngle + (360 / LAN_AGENTS.length) * i) * Math.PI) / 180;
    const x = L.cx + L.rx * Math.cos(ang),
      y = L.cy + L.ry * Math.sin(ang);
    const dx = x - L.cx,
      dy = y - L.cy,
      len = Math.hypot(dx, dy);
    const ux = dx / len,
      uy = dy / len;
    const s = L.coreR + 16;
    const e = len - (L.node / 2) / Math.max(Math.abs(ux), Math.abs(uy)) * 0.9 - 6;
    const svg =
      a.icon && a.icon.trim().startsWith("<svg")
        ? a.icon
        : `<svg viewBox="0 0 24 24">${LAN_ICONS[a.icon] || ""}</svg>`;
    return {
      ...a,
      x,
      y,
      svg,
      col: LAN_COLORS[a.color] || LAN_COLORS.blue,
      p1: [L.cx + ux * s, L.cy + uy * s],
      p2: [L.cx + ux * e, L.cy + uy * e],
    };
  });

  return (
    <Card className="col-span-2 p-6 flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-bold text-slate-800">{LAN_TITLE}</h2>
      </div>
      <div className="lan-stage">
        <svg className="lan-lines" viewBox={`0 0 ${L.W} ${L.H}`} aria-hidden="true">
          {items.map((it, i) => (
            <g key={i} className={`lan-ln ${hover === i ? "on" : ""}`}>
              <line x1={it.p1[0]} y1={it.p1[1]} x2={it.p2[0]} y2={it.p2[1]} />
              <circle cx={it.p1[0]} cy={it.p1[1]} r="4.5" />
              <circle cx={it.p2[0]} cy={it.p2[1]} r="4.5" />
            </g>
          ))}
        </svg>

        <div className="lan-core" tabIndex={0}>
          <div className="lan-orb">
            <svg viewBox="0 0 48 48">
              <circle cx="24" cy="23" r="15" />
              <circle cx="24" cy="23" r="6.5" />
              <path d="M33 34l5 5" />
            </svg>
            <b>{LAN_CENTER.name}</b>
            <small>{LAN_CENTER.subtitle}</small>
          </div>
        </div>

        {items.map((it, i) => (
          <div
            key={i}
            className="lan-node"
            tabIndex={0}
            style={{
              left: `${(it.x / L.W) * 100}%`,
              top: `${(it.y / L.H) * 100}%`,
              "--c": it.col.c,
              "--n1": it.col.n1,
              "--n2": it.col.n2,
              "--nb": it.col.nb,
              "--ns": it.col.ns,
            }}
            onMouseEnter={() => setHover(i)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(i)}
            onBlur={() => setHover(null)}
            onClick={it.onClick}
          >
            <span className="lan-ic" dangerouslySetInnerHTML={{ __html: it.svg }} />
            <span className="lan-lb">{it.name}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};
