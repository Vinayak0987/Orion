// LoopGraph - inline SVG node-graph of the control topology.
// Shows that every cycle terminates at an anchor or human.
// Colour + shape legend; never relies on hue alone.

import { useMemo } from "react";

const KIND_STYLES = {
  execution: { fill: "#4a90d9", label: "Execution", shape: "circle" },
  monitor:   { fill: "#e6a23c", label: "Monitor", shape: "circle" },
  learning:  { fill: "#67c23a", label: "Learning", shape: "circle" },
  anchor:    { fill: "#1f3a5f", label: "Anchor 🔒", shape: "diamond" },
  human:     { fill: "#9b59b6", label: "Human", shape: "square" },
};

const W = 800, H = 500, R = 22;

function layoutNodes(loops) {
  // Arrange nodes in a circular layout
  const nodes = {};
  const n = loops.length;
  const cx = W / 2, cy = H / 2, radius = Math.min(W, H) * 0.35;
  loops.forEach((loop, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    nodes[loop.id] = {
      ...loop,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  });
  return nodes;
}

function NodeShape({ node }) {
  const style = KIND_STYLES[node.kind] || KIND_STYLES.execution;
  const { x, y } = node;

  if (style.shape === "diamond") {
    const d = R * 0.9;
    return (
      <polygon
        points={`${x},${y - d} ${x + d},${y} ${x},${y + d} ${x - d},${y}`}
        fill={style.fill}
        stroke="#fff"
        strokeWidth="2"
      />
    );
  }
  if (style.shape === "square") {
    const s = R * 0.75;
    return (
      <rect
        x={x - s} y={y - s} width={s * 2} height={s * 2}
        fill={style.fill} stroke="#fff" strokeWidth="2" rx="3"
      />
    );
  }
  return (
    <circle cx={x} cy={y} r={R} fill={style.fill} stroke="#fff" strokeWidth="2" />
  );
}

function Edge({ from, to, dashed, bad }) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const startX = from.x + (dx / dist) * R;
  const startY = from.y + (dy / dist) * R;
  const endX = to.x - (dx / dist) * (R + 6);
  const endY = to.y - (dy / dist) * (R + 6);

  return (
    <line
      x1={startX} y1={startY} x2={endX} y2={endY}
      stroke={bad ? "var(--bad)" : "var(--ink)"}
      strokeWidth={bad ? 2.5 : 1.5}
      strokeDasharray={dashed ? "6 4" : "none"}
      markerEnd="url(#arrowhead)"
      opacity={0.7}
    />
  );
}

export default function LoopGraph({ topology }) {
  const nodes = useMemo(() => {
    if (!topology?.loops) return {};
    return layoutNodes(topology.loops);
  }, [topology]);

  if (!topology || !topology.loops) {
    return <div className="panel empty">No topology data.</div>;
  }

  const unterminatedEdges = new Set();
  if (topology.unterminated_cycles?.length > 0) {
    for (const cycle of topology.unterminated_cycles) {
      for (let i = 0; i < cycle.length; i++) {
        unterminatedEdges.add(`${cycle[i]}->${cycle[(i + 1) % cycle.length]}`);
      }
    }
  }

  const edges = [];
  for (const loop of topology.loops) {
    const from = nodes[loop.id];
    if (!from) continue;
    for (const target of loop.sends_to || []) {
      const to = nodes[target];
      if (!to) continue;
      const key = `${loop.id}->${target}`;
      const isBad = unterminatedEdges.has(key);
      edges.push({ from, to, key, dashed: false, bad: isBad });
    }
    // Monitor edges (dashed)
    for (const target of loop.monitors || []) {
      const to = nodes[target];
      if (!to) continue;
      edges.push({ from, to, key: `${loop.id}~>${target}`, dashed: true, bad: false });
    }
  }

  return (
    <div className="loop-graph">
      <h3>Control Topology</h3>
      {topology.unterminated_cycles?.length > 0 && (
        <div className="callout callout-bad">
          ⚠️ <strong>Invalid topology:</strong> {topology.unterminated_cycles.length} unterminated
          cycle(s) detected. Every cycle must pass through an anchor or a human node.
        </div>
      )}
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby="loop-graph-title" className="loop-svg">
        <title id="loop-graph-title">Operating layer control topology</title>
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="var(--ink)" opacity="0.7" />
          </marker>
        </defs>
        {/* Edges */}
        {edges.map((e) => (
          <Edge key={e.key} from={e.from} to={e.to} dashed={e.dashed} bad={e.bad} />
        ))}
        {/* Nodes */}
        {Object.values(nodes).map((node) => (
          <g key={node.id}>
            <NodeShape node={node} />
            <text
              x={node.x} y={node.y + R + 14}
              textAnchor="middle"
              className="loop-label"
              fontSize="10"
            >
              {node.id}
            </text>
          </g>
        ))}
      </svg>
      {/* Legend */}
      <div className="loop-legend">
        {Object.entries(KIND_STYLES).map(([kind, style]) => (
          <span key={kind} className="loop-legend-item">
            <span
              className="loop-legend-swatch"
              style={{ background: style.fill, width: 14, height: 14, display: "inline-block", borderRadius: style.shape === "circle" ? "50%" : "2px", marginRight: 4 }}
            />
            {style.label}
          </span>
        ))}
        <span className="loop-legend-item">
          <span style={{ display: "inline-block", width: 20, borderTop: "2px solid var(--ink)", marginRight: 4 }} />
          work/data flow
        </span>
        <span className="loop-legend-item">
          <span style={{ display: "inline-block", width: 20, borderTop: "2px dashed var(--ink)", marginRight: 4 }} />
          monitors
        </span>
      </div>
      {topology.valid && (
        <p className="loop-valid">✓ All cycles terminate at an anchor or human node. Topology is valid.</p>
      )}
    </div>
  );
}
