import { useEffect, useMemo, useRef, useState } from "react";
import {
  ZoomIn, ZoomOut, Maximize2, Crosshair, X, CircleCheck, CircleDot, Clock, CircleX,
  Search, Megaphone, FileText, Workflow, MessageSquare, Send, Plus,
  Bot, ChartNoAxesCombined, Settings2, ChartNoAxesColumn, Sparkles,
  Globe, Database, Wrench, Boxes,
} from "lucide-react";

// Execution graph for Mission Details. Rich rectangular agent cards (icon +
// name + description + tools row + LLM row), curved Bézier connectors with
// arrows. Draggable / selectable. Fully dynamic from the mission's tasks.

// Agent-type → icon + pastel tile + connector color.
const AGENT_META = {
  research: { Icon: Search, tile: "bg-[#e0edff] text-[#2563eb]", edge: "#3b82f6", desc: "Market & information research" },
  analysis: { Icon: ChartNoAxesColumn, tile: "bg-[#efeafd] text-[#7c3aed]", edge: "#8b5cf6", desc: "Data analysis & insights" },
  finance: { Icon: ChartNoAxesCombined, tile: "bg-[#e7f6ef] text-[#16a34a]", edge: "#22c55e", desc: "Budgeting & financial analysis" },
  writing: { Icon: FileText, tile: "bg-[#eef2ff] text-[#4f46e5]", edge: "#6366f1", desc: "Writing & synthesis" },
  marketing: { Icon: Megaphone, tile: "bg-[#fde9f1] text-[#ec4899]", edge: "#ec4899", desc: "Marketing strategy & content" },
  operations: { Icon: Settings2, tile: "bg-[#fff0e0] text-[#f97316]", edge: "#f97316", desc: "Execution plan & operations" },
  hr: { Icon: Workflow, tile: "bg-[#e6efff] text-[#2563eb]", edge: "#2563eb", desc: "People & coordination" },
  general: { Icon: Boxes, tile: "bg-[#eef1f6] text-[#64748b]", edge: "#64748b", desc: "General task handling" },
};
const metaOf = (t) => AGENT_META[t] || AGENT_META.general;

// Tool id → small icon + label.
const TOOL_META = {
  web_search: { Icon: Globe, label: "Web Search" },
  web_scraper: { Icon: Globe, label: "Web Scraper" },
  document_rag: { Icon: Database, label: "Document RAG" },
  document_reader: { Icon: FileText, label: "Document Reader" },
};
const toolMeta = (id) => TOOL_META[id] || { Icon: Wrench, label: (id || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) };

const LEAF_STATUS = {
  completed: { Icon: CircleCheck, color: "text-emerald-500" },
  running: { Icon: CircleDot, color: "text-blue-500" },
  failed: { Icon: CircleX, color: "text-rose-500" },
  stopped: { Icon: CircleX, color: "text-[#9aa6b8]" },
  pending: { Icon: Clock, color: "text-amber-500" },
};

const curve = (x1, y1, x2, y2) => {
  const dx = Math.max(45, (x2 - x1) * 0.55);
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
};

// Geometry — richer cards.
const AGENT_X = 250, AGENT_W = 236, LEAF_X = 560, LEAF_W = 220, LEAF_H = 60, ROW_GAP = 24;
const ORCH_W = 200;


export function ExecutionGraph({ tasks = [], running, onSelect, selectedId, toolsUsed = [], model }) {
  const [scale, setScale] = useState(1);
  const [expanded, setExpanded] = useState(false);
  const [positions, setPositions] = useState({});
  const [hover, setHover] = useState(null);
  const drag = useRef(null);

  const groups = useMemo(() => {
    const by = new Map();
    for (const t of tasks) {
      const key = t.agent_id || t.agent_type || "general";
      if (!by.has(key)) by.set(key, { key, type: t.agent_type || "general", name: t.agent_name || `${t.agent_type || "general"} agent`, leaves: [] });
      by.get(key).leaves.push(t);
    }
    return [...by.values()];
  }, [tasks]);

  // Per-agent card height: header + tools row (if any) + LLM row.
  const agentH = (g) => {
    const tools = [...new Set(g.leaves.flatMap((l) => l.tools_needed || []))];
    const toolRows = tools.length > 3 ? 2 : 1; // label + at least one chip/empty row
    return 60 + 16 + toolRows * 30 + 44; // header + tools label + tool rows + llm+padding
  };
  const ORCH_H = 110;

  // Default layout (node id -> {x,y} top-left).
  const { base, W, H } = useMemo(() => {
    let y = 24;
    const b = {};
    groups.forEach((g, gi) => {
      const top = y;
      const ah = agentH(g);
      // leaves need room for 2-line titles → use a taller row.
      const leafRow = LEAF_H + ROW_GAP;
      const blockH = Math.max(g.leaves.length * leafRow, ah);
      g.leaves.forEach((lf, li) => { b[`leaf:${lf.id}`] = { x: LEAF_X, y: top + li * leafRow }; });
      b[`agent:${gi}`] = { x: AGENT_X, y: top + blockH / 2 - ah / 2 };
      y += blockH + 40; // generous gap between agent blocks → no overlap
    });
    const height = Math.max(y + 20, 280); // trailing bottom padding
    const width = LEAF_X + LEAF_W + 40;
    b.orch = { x: 24, y: height / 2 - ORCH_H / 2 };
    return { base: b, W: width, H: height };
  }, [groups]);

  // Reset custom positions when the task set changes.
  useEffect(() => { setPositions({}); }, [base]);

  const posOf = (id) => positions[id] || base[id];

  function onDown(e, id) {
    e.stopPropagation();
    const p = posOf(id);
    drag.current = { id, sx: e.clientX, sy: e.clientY, ox: p.x, oy: p.y, moved: false };
  }
  function onMove(e) {
    const d = drag.current;
    if (!d) return;
    const dx = (e.clientX - d.sx) / scale;
    const dy = (e.clientY - d.sy) / scale;
    if (Math.abs(e.clientX - d.sx) > 3 || Math.abs(e.clientY - d.sy) > 3) d.moved = true;
    // Free drag — no clamping. Node may move past the original bounds; the
    // canvas grows and scrolls to keep it inside the container's content area.
    const nx = Math.max(0, d.ox + dx);
    const ny = Math.max(0, d.oy + dy);
    setPositions((prev) => ({ ...prev, [d.id]: { x: nx, y: ny } }));
  }
  function onUp() {
    const d = drag.current;
    if (d && !d.moved && d.id.startsWith("leaf:")) {
      const id = d.id.slice(5);
      onSelect?.(tasks.find((t) => t.id === id) || null);
    }
    drag.current = null;
  }

  if (tasks.length === 0) {
    return (
      <div className="neu-inset min-h-[220px] grid place-items-center p-8 text-center">
        <div>
          <Boxes size={26} className="mx-auto text-[#b4bdcc] mb-2" />
          <p className="text-[13px] text-[#8792a6]">The execution graph appears here once the mission has tasks.</p>
        </div>
      </div>
    );
  }

  const orch = posOf("orch");
  const orchCenter = () => { const p = posOf("orch"); return { x: p.x + ORCH_W / 2 + 42, y: p.y + 42 }; };
  const agentCenter = (gi) => { const p = posOf(`agent:${gi}`); return { x: p.x, y: p.y + agentH(groups[gi]) / 2, right: p.x + AGENT_W }; };
  const leafCenter = (id) => { const p = posOf(`leaf:${id}`); return { x: p.x, y: p.y + LEAF_H / 2 }; };

  // Grow the canvas content to fit any node dragged beyond the base bounds so
  // the container gets a scrollbar instead of losing the node. A generous
  // bottom margin keeps the lowest node off the container's bottom edge.
  const PAD = 40;
  const BOTTOM = 70; // breathing room below the lowest node
  let cw = W, ch = H;
  groups.forEach((g, gi) => {
    const a = posOf(`agent:${gi}`);
    cw = Math.max(cw, a.x + AGENT_W + PAD); ch = Math.max(ch, a.y + agentH(g) + BOTTOM);
    g.leaves.forEach((lf) => {
      const l = posOf(`leaf:${lf.id}`);
      cw = Math.max(cw, l.x + LEAF_W + PAD); ch = Math.max(ch, l.y + LEAF_H + BOTTOM);
    });
  });
  cw = Math.max(cw, orch.x + ORCH_W + PAD); ch = Math.max(ch, orch.y + ORCH_H + BOTTOM);

  const VIEW_H = Math.min(Math.max(ch * scale, 300), 560); // viewport height of the canvas
  const canvas = (
    <div
      className="neu-inset relative overflow-auto om-scroll"
      style={{ backgroundImage: "radial-gradient(#d9deea 1px, transparent 1px)", backgroundSize: "18px 18px", width: "100%", height: VIEW_H }}
      onMouseMove={onMove}
      onMouseUp={onUp}
      onMouseLeave={onUp}
    >
      {/* scaled graph — grows with dragged nodes so the canvas scrolls */}
      <div className="origin-top-left" style={{ transform: `scale(${scale})`, width: cw, height: ch }}>
        <div className="relative" style={{ width: cw, height: ch }}>
            {/* connectors */}
            <svg className="absolute inset-0 pointer-events-none" width={cw} height={ch} style={{ overflow: "visible" }}>
              <defs>
                {groups.map((g, gi) => (
                  <marker key={gi} id={`mk-${gi}`} viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                    <circle cx="5" cy="5" r="3" fill={metaOf(g.type).edge} />
                  </marker>
                ))}
              </defs>
              {groups.map((g, gi) => {
                const col = metaOf(g.type).edge;
                const oc = orchCenter();
                const ac = agentCenter(gi);
                const run = g.leaves.some((l) => l.status === "running");
                return (
                  <g key={gi}>
                    <path d={curve(oc.x + 2, oc.y, ac.x - 6, ac.y)} stroke={col} strokeWidth="2.4" fill="none" markerEnd={`url(#mk-${gi})`} className={run ? "om-flow" : ""} strokeDasharray={run ? "6 5" : undefined} opacity="0.85" />
                    {g.leaves.map((lf) => {
                      const lc = leafCenter(lf.id);
                      const lrun = lf.status === "running";
                      return <path key={lf.id} d={curve(ac.right, ac.y, lc.x - 6, lc.y)} stroke={col} strokeWidth="2" fill="none" markerEnd={`url(#mk-${gi})`} className={lrun ? "om-flow" : ""} strokeDasharray={lrun ? "6 5" : undefined} opacity={lf.status === "completed" ? 0.85 : 0.6} />;
                    })}
                  </g>
                );
              })}
            </svg>

            {/* Orchestrator — Orion sphere with agent-robot icon */}
            <div
              className="absolute flex flex-col items-center cursor-grab active:cursor-grabbing select-none"
              style={{ left: orch.x, top: orch.y, width: ORCH_W }}
              onMouseDown={(e) => onDown(e, "orch")}
              onMouseEnter={(e) => setHover({ sx: e.clientX, sy: e.clientY, title: "Orion Planner", sub: "Orchestrator", body: `Coordinates ${tasks.length} tasks across ${groups.length} agents.` })}
              onMouseMove={(e) => hover && setHover((h) => ({ ...h, sx: e.clientX, sy: e.clientY }))}
              onMouseLeave={() => setHover(null)}
            >
              <div className="relative grid place-items-center" style={{ width: 84, height: 84 }}>
                <span className="absolute inset-[-4px] rounded-[26px]" style={{ background: "radial-gradient(circle, rgba(99,102,241,.18), transparent 70%)" }} />
                <span
                  className="relative grid place-items-center text-white rounded-[22px]"
                  style={{ width: 64, height: 64, background: "linear-gradient(145deg, #6366f1, #4338ca)", boxShadow: "0 8px 20px rgba(67,56,202,.35), inset 0 1px 2px rgba(255,255,255,.35)" }}
                >
                  <Bot size={30} strokeWidth={2} className="relative" />
                </span>
              </div>
              <div className="neu-raised rounded-xl px-3 py-1.5 mt-2 text-center">
                <p className="text-[12px] font-bold text-[#334155] leading-tight">Orion Planner</p>
                <p className="text-[9.5px] text-[#94a3b8] leading-tight">Orchestrator</p>
              </div>
            </div>

            {/* Agent cards */}
            {groups.map((g, gi) => {
              const m = metaOf(g.type);
              const p = posOf(`agent:${gi}`);
              const anyRun = g.leaves.some((l) => l.status === "running");
              const allDone = g.leaves.every((l) => ["completed", "failed", "stopped"].includes(l.status));
              const tools = [...new Set(g.leaves.flatMap((l) => l.tools_needed || []))]
                .filter((t) => toolsUsed.length === 0 || toolsUsed.includes(t));
              return (
                <div
                  key={gi}
                  className="absolute neu-card cursor-grab active:cursor-grabbing select-none"
                  style={{ left: p.x, top: p.y, width: AGENT_W }}
                  onMouseDown={(e) => onDown(e, `agent:${gi}`)}
                  onMouseEnter={(e) => setHover({ sx: e.clientX, sy: e.clientY, title: g.name, sub: `${g.type} agent`, body: `${g.leaves.length} task(s) · ${allDone ? "finished" : anyRun ? "running" : "queued"}` })}
                  onMouseMove={(e) => hover && setHover((h) => ({ ...h, sx: e.clientX, sy: e.clientY }))}
                  onMouseLeave={() => setHover(null)}
                >
                  {/* header */}
                  <div className="flex items-start gap-2.5 p-3 pb-2">
                    <span className={`neu-circle relative w-9 h-9 rounded-xl grid place-items-center shrink-0 ${m.tile}`}>
                      {anyRun && <span className="absolute inset-[-2px] rounded-xl animate-ping" style={{ background: `radial-gradient(circle, ${m.edge}33, transparent 70%)`, animationDuration: "1.8s" }} />}
                      <m.Icon size={18} strokeWidth={2} className="relative" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <h5 className="text-[13px] font-bold text-[#334155] leading-tight truncate capitalize">{g.name}</h5>
                      <p className="text-[10.5px] text-[#94a3b8] leading-snug truncate">{m.desc}</p>
                    </div>
                    {allDone && <CircleCheck size={14} className="text-emerald-500 shrink-0 mt-0.5" />}
                  </div>
                  {/* tools row — real tools actually used */}
                  <div className="px-3 pb-2">
                    <p className="text-[9px] font-bold uppercase tracking-wide text-[#b4bdcc] mb-1">Tools used</p>
                    {tools.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {tools.map((t) => {
                          const tm = toolMeta(t);
                          return (
                            <span key={t} className="neu-chip inline-flex items-center gap-1 px-1.5 py-1 text-[9.5px] font-medium text-[#475569]">
                              <tm.Icon size={10} className="text-[#64748b]" /> {tm.label}
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      <span className="text-[9.5px] text-[#9aa6b8] italic">No tools used</span>
                    )}
                  </div>
                  {/* llm row — real model */}
                  <div className="px-3 pb-3">
                    <div className="neu-inset px-2.5 py-1.5 flex items-center gap-1.5">
                      <span className="text-[9px] font-bold uppercase tracking-wide text-[#b4bdcc]">LLM</span>
                      <Sparkles size={11} className="text-[#6366f1]" />
                      <span className="text-[10.5px] font-semibold text-[#475569] truncate">{model || "—"}</span>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Leaf task cards */}
            {groups.flatMap((g) => g.leaves.map((lf) => ({ lf, edge: metaOf(g.type).edge }))).map(({ lf, edge }) => {
              const s = LEAF_STATUS[lf.status] || LEAF_STATUS.pending;
              const p = posOf(`leaf:${lf.id}`);
              const sel = selectedId === lf.id;
              return (
                <div
                  key={lf.id}
                  className="absolute neu-raised flex items-center gap-2.5 px-3 py-2.5 cursor-grab active:cursor-grabbing select-none"
                  style={{ left: p.x, top: p.y, width: LEAF_W, minHeight: LEAF_H, boxShadow: sel ? `0 0 0 2px #8b5cf6, 6px 6px 14px #d4d9e4, -6px -6px 14px #ffffff` : undefined }}
                  onMouseDown={(e) => onDown(e, `leaf:${lf.id}`)}
                  onMouseEnter={(e) => setHover({ sx: e.clientX, sy: e.clientY, title: lf.title, sub: `${lf.agent_type || "general"} · ${lf.status || "pending"}`, body: lf.result?.summary || (lf.tools_needed?.length ? `Tools: ${lf.tools_needed.join(", ")}` : "No output yet.") })}
                  onMouseMove={(e) => hover && setHover((h) => ({ ...h, sx: e.clientX, sy: e.clientY }))}
                  onMouseLeave={() => setHover(null)}
                >
                  <span className="neu-circle w-7 h-7 rounded-lg grid place-items-center shrink-0">
                    <s.Icon size={14} className={s.color} strokeWidth={2.4} />
                  </span>
                  <span className="text-[11.5px] font-medium text-[#334155] leading-snug line-clamp-2 flex-1">{lf.title}</span>
                </div>
              );
            })}
          </div>
        </div>
    </div>
  );

  const toolbar = (inFull) => (
    <div className="flex items-center justify-between px-1 pb-2 shrink-0">
      <span className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600">
        <span className={`w-1.5 h-1.5 rounded-full bg-emerald-500 ${running ? "animate-pulse" : ""}`} /> {running ? "Live" : "Complete"}
      </span>
      <div className="flex items-center gap-1.5">
        <button onClick={() => setScale((s) => Math.max(0.5, +(s - 0.1).toFixed(2)))} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#64748b]" title="Zoom out"><ZoomOut size={14} /></button>
        <span className="text-[11px] font-semibold text-[#64748b] w-9 text-center">{Math.round(scale * 100)}%</span>
        <button onClick={() => setScale((s) => Math.min(1.6, +(s + 0.1).toFixed(2)))} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#64748b]" title="Zoom in"><ZoomIn size={14} /></button>
        <button onClick={() => { setScale(1); setPositions({}); }} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#64748b]" title="Reset layout & zoom"><Crosshair size={13} /></button>
        <button onClick={() => setExpanded(!inFull)} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title={inFull ? "Close" : "Expand"}>
          {inFull ? <X size={14} /> : <Maximize2 size={13} />}
        </button>
      </div>
    </div>
  );

  const legend = (
    <div className="flex items-center gap-4 pt-2 shrink-0 text-[11px] font-medium text-[#64748b]">
      <span className="flex items-center gap-1.5"><CircleCheck size={13} className="text-emerald-500" /> Completed</span>
      <span className="flex items-center gap-1.5"><CircleDot size={13} className="text-blue-500" /> Running</span>
      <span className="flex items-center gap-1.5"><Clock size={13} className="text-amber-500" /> Pending</span>
      <span className="flex items-center gap-1.5"><CircleX size={13} className="text-rose-500" /> Failed</span>
      <span className="ml-auto text-[10.5px] text-[#9aa6b8]">Drag nodes · hover for details</span>
    </div>
  );

  const tooltip = hover && (
    <div className="fixed z-[210] pointer-events-none neu-card px-3 py-2.5 max-w-[260px]"
         style={{ left: Math.min(hover.sx + 16, window.innerWidth - 290), top: Math.min(hover.sy + 16, window.innerHeight - 130) }}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#4f46e5] mb-0.5">{hover.sub}</p>
      <p className="text-[13px] font-semibold text-[#334155] mb-1">{hover.title}</p>
      <p className="text-[11.5px] text-[#64748b] line-clamp-3">{hover.body}</p>
    </div>
  );

  return (
    <>
      <div className="flex flex-col">
        {toolbar(false)}
        {canvas}
        {legend}
      </div>
      {!expanded && tooltip}

      {expanded && (
        <div className="fixed inset-0 z-[200] bg-slate-900/60 animate-[toastIn_.15s_ease-out]" onMouseDown={(e) => e.target === e.currentTarget && setExpanded(false)}>
          <div className="absolute inset-3 sm:inset-6 neu-surface rounded-2xl shadow-[0_20px_60px_rgba(15,23,42,0.4)] flex flex-col overflow-hidden">
            <div className="px-5 py-3 border-b border-[#e2e6ee] shrink-0 flex items-center justify-between">
              <h3 className="text-[14px] font-bold text-[#334155]">Execution Graph</h3>
            </div>
            <div className="flex-1 min-h-0 overflow-auto om-scroll p-5">
              {toolbar(true)}
              {canvas}
              {legend}
            </div>
          </div>
          {tooltip}
        </div>
      )}
    </>
  );
}
