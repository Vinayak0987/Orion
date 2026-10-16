import { useEffect, useMemo, useRef, useState } from "react";
import { X, ZoomIn, ZoomOut, Maximize2, Boxes, Check, AlertCircle } from "lucide-react";

// Agent-type colors (kept in sync with the inline tree).
const COLOR = {
  research: "#16a34a", analysis: "#7c3aed", finance: "#7c3aed", writing: "#4f46e5",
  marketing: "#ec4899", operations: "#f97316", hr: "#2563eb", general: "#64748b",
};
const colorOf = (t) => COLOR[t] || COLOR.general;

const NODE_W = 180;
const NODE_H = 64;
const COL_GAP = 70;   // horizontal gap between nodes in a level
const ROW_GAP = 110;  // vertical gap between levels
const ROOT_ID = "__root__";

// Build dependency levels + initial x/y layout for every task + the planner root.
function buildLayout(tasks) {
  const byTitle = new Map(tasks.map((t) => [t.title, t]));
  const levelOf = new Map();
  const compute = (t, seen = new Set()) => {
    if (levelOf.has(t.title)) return levelOf.get(t.title);
    if (seen.has(t.title)) return 0;
    seen.add(t.title);
    const deps = (t.depends_on || []).filter((d) => byTitle.has(d) && d !== t.title);
    const lvl = deps.length === 0 ? 0 : 1 + Math.max(...deps.map((d) => compute(byTitle.get(d), seen)));
    levelOf.set(t.title, lvl);
    return lvl;
  };
  tasks.forEach((t) => compute(t));

  const levels = [];
  tasks.forEach((t) => {
    const l = levelOf.get(t.title) || 0;
    (levels[l] = levels[l] || []).push(t);
  });

  const maxRow = Math.max(1, ...levels.map((r) => r.length));
  const canvasW = Math.max(maxRow, 1) * (NODE_W + COL_GAP);
  const pos = {};
  // Planner centered on top.
  pos[ROOT_ID] = { x: canvasW / 2 - NODE_W / 2, y: 20 };
  levels.forEach((row, li) => {
    const rowW = row.length * NODE_W + (row.length - 1) * COL_GAP;
    const startX = canvasW / 2 - rowW / 2;
    row.forEach((t, i) => {
      pos[t.id] = { x: startX + i * (NODE_W + COL_GAP), y: 20 + (li + 1) * (NODE_H + ROW_GAP) };
    });
  });

  const edges = [];
  tasks.forEach((t) => {
    const deps = (t.depends_on || []).filter((d) => byTitle.has(d) && d !== t.title);
    if (deps.length === 0) edges.push({ from: ROOT_ID, to: t.id, type: t.agent_type });
    else deps.forEach((d) => edges.push({ from: byTitle.get(d).id, to: t.id, type: t.agent_type }));
  });

  const height = 40 + (levels.length + 1) * (NODE_H + ROW_GAP);
  return { pos, edges, canvasW: Math.max(canvasW, 320), canvasH: height, byTitle };
}

export function AgentGraphCanvas({ tasks, onClose }) {
  const layout = useMemo(() => buildLayout(tasks || []), [tasks]);
  const [positions, setPositions] = useState(layout.pos);
  const [scale, setScale] = useState(0.9);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [hover, setHover] = useState(null);
  const drag = useRef(null); // { kind: 'node'|'pan', id, startX, startY, origX, origY }

  // Re-seed positions when the task set changes (new nodes added), keeping any
  // the user already moved.
  useEffect(() => {
    setPositions((prev) => {
      const next = { ...layout.pos };
      for (const k of Object.keys(prev)) if (next[k]) next[k] = prev[k];
      return next;
    });
  }, [layout]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [onClose]);

  const onPointerDownNode = (e, id) => {
    e.stopPropagation();
    const p = positions[id] || { x: 0, y: 0 };
    drag.current = { kind: "node", id, startX: e.clientX, startY: e.clientY, origX: p.x, origY: p.y };
  };
  const onPointerDownCanvas = (e) => {
    drag.current = { kind: "pan", startX: e.clientX, startY: e.clientY, origX: pan.x, origY: pan.y };
  };
  const onPointerMove = (e) => {
    const d = drag.current;
    if (!d) return;
    const dx = (e.clientX - d.startX) / (d.kind === "node" ? scale : 1);
    const dy = (e.clientY - d.startY) / (d.kind === "node" ? scale : 1);
    if (d.kind === "node") {
      setPositions((prev) => ({ ...prev, [d.id]: { x: d.origX + dx, y: d.origY + dy } }));
    } else {
      setPan({ x: d.origX + (e.clientX - d.startX), y: d.origY + (e.clientY - d.startY) });
    }
  };
  const onPointerUp = () => { drag.current = null; };

  const onWheel = (e) => {
    if (!e.ctrlKey && !e.metaKey) return; // only zoom with ctrl/cmd+wheel
    e.preventDefault();
    setScale((s) => Math.min(2, Math.max(0.4, s - e.deltaY * 0.001)));
  };

  const zoom = (d) => setScale((s) => Math.min(2, Math.max(0.4, +(s + d).toFixed(2))));
  const reset = () => { setScale(0.9); setPan({ x: 0, y: 0 }); setPositions(layout.pos); };

  const byTitle = layout.byTitle;
  const nodeCenter = (id) => {
    const p = positions[id];
    return p ? { x: p.x + NODE_W / 2, y: p.y + NODE_H / 2 } : null;
  };
  const curve = (a, b) => {
    if (!a || !b) return "";
    const dy = Math.max(20, (b.y - a.y) * 0.5);
    return `M ${a.x} ${a.y + NODE_H / 2} C ${a.x} ${a.y + NODE_H / 2 + dy}, ${b.x} ${b.y - NODE_H / 2 - dy}, ${b.x} ${b.y - NODE_H / 2}`;
  };

  const nodeData = (id) => {
    if (id === ROOT_ID) return { title: "Orion Planner", agent_type: "planner", status: "root", root: true };
    return (tasks || []).find((t) => t.id === id);
  };

  return (
    <div className="fixed inset-0 z-[200] bg-slate-900/60 animate-[toastIn_.15s_ease-out]">
      <div className="absolute inset-3 sm:inset-6 neu-surface rounded-2xl shadow-[0_20px_60px_rgba(15,23,42,0.4)] flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#e2e6ee] shrink-0">
          <div className="flex items-center gap-2">
            <span className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-[#4f46e5]"><Boxes size={17} /></span>
            <div>
              <h3 className="text-[14px] font-bold text-[#334155] leading-tight">Agent Workflow</h3>
              <p className="text-[11px] text-[#9aa6b8] leading-tight">{(tasks || []).length} agents · drag nodes · drag canvas to pan</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => zoom(-0.15)} className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title="Zoom out"><ZoomOut size={16} /></button>
            <span className="text-[12px] font-semibold text-[#64748b] w-10 text-center">{Math.round(scale * 100)}%</span>
            <button onClick={() => zoom(0.15)} className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title="Zoom in"><ZoomIn size={16} /></button>
            <button onClick={reset} className="neu-btn-ghost px-3 h-9 text-[12px] font-semibold">Reset</button>
            <button onClick={onClose} className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-[#8792a6] hover:text-rose-500" title="Close"><X size={17} /></button>
          </div>
        </div>

        {/* Canvas */}
        <div
          className="relative flex-1 overflow-hidden cursor-grab active:cursor-grabbing"
          onMouseDown={onPointerDownCanvas}
          onMouseMove={onPointerMove}
          onMouseUp={onPointerUp}
          onMouseLeave={onPointerUp}
          onWheel={onWheel}
          style={{ backgroundImage: "radial-gradient(#d9deea 1px, transparent 1px)", backgroundSize: "22px 22px" }}
        >
          <div
            className="absolute top-0 left-0 origin-top-left"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`, width: layout.canvasW, height: layout.canvasH }}
          >
            {/* Edges */}
            <svg className="absolute inset-0 pointer-events-none" width={layout.canvasW} height={layout.canvasH} style={{ overflow: "visible" }}>
              {layout.edges.map((e, i) => {
                const a = nodeCenter(e.from);
                const b = nodeCenter(e.to);
                const child = nodeData(e.to);
                const active = child?.status === "running";
                const done = child?.status === "completed";
                const col = colorOf(e.type);
                return (
                  <path key={i} d={curve(a, b)} fill="none" stroke={col}
                    strokeWidth={active || done ? 2.6 : 2}
                    strokeOpacity={done ? 1 : active ? 0.95 : 0.5}
                    strokeLinecap="round"
                    strokeDasharray={active ? "6 5" : undefined}
                    className={active ? "om-flow" : ""} />
                );
              })}
            </svg>

            {/* Planner root */}
            <GraphNode id={ROOT_ID} pos={positions[ROOT_ID]} root onDown={onPointerDownNode} onHover={setHover} />

            {/* Task nodes */}
            {(tasks || []).map((t) => (
              <GraphNode key={t.id} id={t.id} task={t} pos={positions[t.id]} onDown={onPointerDownNode} onHover={setHover} />
            ))}
          </div>

          {/* Hover tooltip — follows the cursor */}
          {hover && (
            <div className="fixed z-[210] pointer-events-none neu-card px-3 py-2.5 max-w-[260px]"
                 style={{ left: Math.min(hover.sx + 16, window.innerWidth - 290), top: Math.min(hover.sy + 16, window.innerHeight - 140) }}>
              <p className="text-[10px] font-bold uppercase tracking-wide mb-0.5" style={{ color: colorOf(hover.data.agent_type) }}>
                {hover.data.root ? "Orchestrator" : (hover.data.agent_type || "general")}
              </p>
              <p className="text-[13px] font-semibold text-[#334155] mb-1">{hover.data.title}</p>
              {!hover.data.root && (
                <>
                  <p className="text-[11.5px] text-[#64748b]">Status: <span className="font-medium capitalize">{hover.data.status || "pending"}</span></p>
                  {hover.data.depends_on?.length > 0 && (
                    <p className="text-[11px] text-[#9aa6b8] mt-0.5">Depends on: {hover.data.depends_on.join(", ")}</p>
                  )}
                  {hover.data.tools_needed?.length > 0 && (
                    <p className="text-[11px] text-[#9aa6b8] mt-0.5">Tools: {hover.data.tools_needed.join(", ")}</p>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GraphNode({ id, task, pos, root, onDown, onHover }) {
  if (!pos) return null;
  const type = root ? "planner" : task.agent_type;
  const col = colorOf(type);
  const status = root ? "root" : task.status;
  const dotColor = status === "completed" ? "#16a34a" : status === "failed" ? "#ef4444" : status === "running" ? col : status === "stopped" ? "#9aa6b8" : "#cbd5e1";
  return (
    <div
      onMouseDown={(e) => onDown(e, id)}
      onMouseEnter={(e) => onHover({ sx: e.clientX, sy: e.clientY, data: root ? { title: "Orion Planner", root: true, agent_type: "planner" } : task })}
      onMouseMove={(e) => onHover({ sx: e.clientX, sy: e.clientY, data: root ? { title: "Orion Planner", root: true, agent_type: "planner" } : task })}
      onMouseLeave={() => onHover(null)}
      className={`absolute cursor-grab active:cursor-grabbing select-none ${root ? "border border-[#c7d2fe]" : "border"} neu-raised rounded-xl px-3 py-2 flex flex-col gap-1`}
      style={{ left: pos.x, top: pos.y, width: NODE_W, minHeight: NODE_H, borderColor: root ? undefined : `${col}44`, animation: "treePop .3s cubic-bezier(.2,.8,.2,1) both" }}
    >
      {root ? (
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-white shrink-0"><Boxes size={15} /></span>
          <div><p className="text-[12.5px] font-bold text-[#334155] leading-tight">Orion Planner</p><p className="text-[10px] text-[#9aa6b8] leading-tight">Orchestrator</p></div>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-full border-2 grid place-items-center shrink-0" style={{ borderColor: dotColor }}>
              {status === "completed" && <Check size={9} strokeWidth={4} className="text-emerald-500" />}
              {status === "running" && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: col }} />}
              {status === "failed" && <AlertCircle size={10} className="text-rose-500" />}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: col }}>{type}</span>
          </div>
          <span className="text-[11.5px] leading-snug text-[#334155] line-clamp-2">{task.title}</span>
        </>
      )}
    </div>
  );
}
