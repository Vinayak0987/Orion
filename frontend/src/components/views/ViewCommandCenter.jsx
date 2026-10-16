import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Plus,
  Square,
  Paperclip,
  ArrowUp,
  Boxes,
  CheckCircle2,
  CircleDot,
  Clock,
  AlertCircle,
  Wrench,
  Microscope,
  ListChecks,
  BarChart3,
  Lightbulb,
  X,
  ShieldQuestion,
  Check,
  FileText,
  Loader2,
  MessageSquarePlus,
  Trash2,
  Pencil,
  Copy,
  CheckCheck,
  FileDown,
  FileCode2,
  Sparkles,
  Globe,
  Search,
  Link2,
  User,
  Timer,
  PenLine,
  Megaphone,
  Briefcase,
  Cpu,
  ChevronDown,
  PanelLeft,
  PanelLeftClose,
  Maximize2,
} from "lucide-react";

import { streamMission, missionApi } from "../../missionApi";
import { chatApi } from "../../chatApi";
import { AgentGraphCanvas } from "./AgentGraphCanvas.jsx";
import { authApi } from "../../auth/authApi.js";
import { useToast } from "../ui/Toast.jsx";
import { Markdown } from "../ui/Markdown.jsx";
import { exportHtml, exportPdf } from "../../utils/exportDoc.js";

const QUICK_TAGS = [
  { label: "Deep Research", Icon: Microscope, fill: "Research [topic] thoroughly and give me a complete report" },
  { label: "Create Plan", Icon: ListChecks, fill: "Create a detailed step-by-step plan for [goal]" },
  { label: "Analyze Data", Icon: BarChart3, fill: "Analyze [subject] and give me key insights and recommendations" },
  { label: "Generate Strategy", Icon: Lightbulb, fill: "Generate a complete strategy for [objective]" },
];

const FOLLOW_UPS = [
  "Turn this into a step-by-step action plan",
  "Summarize the key points in 5 bullets",
  "What are the risks and how do I mitigate them?",
];

const STATUS_ICON = {
  pending: { Icon: Clock, cls: "text-[#94a3b8]" },
  running: { Icon: CircleDot, cls: "text-[#4f46e5] animate-pulse" },
  completed: { Icon: CheckCircle2, cls: "text-emerald-500" },
  failed: { Icon: AlertCircle, cls: "text-rose-500" },
};

const toolLabel = (t) => (t || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

function fmtTime(iso) {
  const d = iso ? new Date(iso) : new Date();
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
function dayKey(iso) {
  const d = iso ? new Date(iso) : new Date();
  return d.toDateString();
}
function dayLabel(iso) {
  const d = iso ? new Date(iso) : new Date();
  const today = new Date();
  const yest = new Date();
  yest.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yest.toDateString()) return "Yesterday";
  return d.toLocaleDateString([], { weekday: "long", day: "numeric", month: "short", year: "numeric" });
}
function convTime(iso) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

// ---------------- Live Task List (matches reference UI) ----------------
// Per agent-type: a soft tinted icon tile + icon.
const AGENT_STYLE = {
  research: { Icon: Search, tile: "bg-[#e7f6ef] text-[#16a34a]" },
  analysis: { Icon: Link2, tile: "bg-[#e7f6ef] text-[#16a34a]" },
  finance: { Icon: User, tile: "bg-[#eceafd] text-[#6d5ef0]" },
  writing: { Icon: PenLine, tile: "bg-[#eef2ff] text-[#4f46e5]" },
  marketing: { Icon: Megaphone, tile: "bg-[#fde9f1] text-[#ec4899]" },
  operations: { Icon: Cpu, tile: "bg-[#fff0e0] text-[#f97316]" },
  hr: { Icon: User, tile: "bg-[#e6efff] text-[#2563eb]" },
  strategy: { Icon: Timer, tile: "bg-[#fff0e0] text-[#f97316]" },
  general: { Icon: Timer, tile: "bg-[#fff0e0] text-[#f97316]" },
};

function agentStyle(type) {
  return AGENT_STYLE[type] || AGENT_STYLE.general;
}

// A soft indeterminate progress bar for a running task.
function ProgressBar() {
  return (
    <div className="w-24 h-2.5 rounded-full bg-[#e9edf4] overflow-hidden shrink-0">
      <div className="h-full rounded-full bg-gradient-to-r from-[#6366f1] to-[#4f46e5] animate-[progressSlide_1.4s_ease-in-out_infinite]" style={{ width: "60%" }} />
    </div>
  );
}

function TaskCard({ t, index, subtasks = [] }) {
  const { Icon, tile } = agentStyle(t.agent_type);
  const name = t.agent_name || `${(t.agent_type || "general").replace(/\b\w/, (c) => c.toUpperCase())} Agent`;
  const activity =
    t.status === "completed" ? "Done" :
    t.status === "failed" ? "Failed" :
    t.status === "running" ? `${t.title}…` :
    t.title;

  const Status = () =>
    t.status === "running" ? <ProgressBar /> :
    t.status === "completed" ? (
      <span className="w-6 h-6 rounded-full border-2 border-emerald-500/30 grid place-items-center shrink-0"><Check size={13} className="text-emerald-500" strokeWidth={3} /></span>
    ) : t.status === "failed" ? <AlertCircle size={18} className="text-rose-500 shrink-0" /> :
    t.status === "stopped" ? <span className="text-[11px] font-semibold text-[#9aa6b8] shrink-0">Stopped</span> :
    <span className="text-[11px] font-semibold text-[#8b95a7] bg-[#eef1f6] rounded-lg px-3 py-1.5 shrink-0">Queued</span>;

  return (
    <div className="neu-raised p-3 animate-[rowIn_.28s_ease-out]">
      <div className="flex items-center gap-3">
        {/* number badge */}
        <span className="w-6 h-6 rounded-lg bg-[#eef1f6] shadow-[inset_2px_2px_4px_#d4d9e4,inset_-2px_-2px_4px_#ffffff] grid place-items-center text-[11px] font-bold text-[#4f46e5] shrink-0">
          {index}
        </span>
        <span className={`w-9 h-9 rounded-xl grid place-items-center shrink-0 ${tile}`}>
          <Icon size={18} strokeWidth={2} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-bold text-[#334155] truncate">{name}</p>
          <p className="text-[11.5px] text-[#94a3b8] truncate">{activity}</p>
        </div>
        <Status />
      </div>

      {/* nested sub-tasks (tasks that depend on this one) */}
      {subtasks.length > 0 && (
        <div className="mt-2.5 pl-4 ml-3.5 border-l-2 border-[#e2e6ee] flex flex-col gap-2">
          {subtasks.map((st, j) => {
            const style = agentStyle(st.agent_type);
            const sName = st.agent_name || `${(st.agent_type || "general").replace(/\b\w/, (c) => c.toUpperCase())} Agent`;
            const sAct = st.status === "completed" ? "Done" : st.status === "failed" ? "Failed" : st.status === "running" ? `${st.title}…` : st.title;
            return (
              <div key={st.id} className="neu-inset p-2.5 flex items-center gap-2.5 animate-[rowIn_.28s_ease-out]">
                <span className="text-[10px] font-bold text-[#9aa6b8] shrink-0">{index}.{j + 1}</span>
                <span className={`w-7 h-7 rounded-lg grid place-items-center shrink-0 ${style.tile}`}>
                  <style.Icon size={14} strokeWidth={2} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[12px] font-semibold text-[#334155] truncate">{sName}</p>
                  <p className="text-[11px] text-[#94a3b8] truncate">{sAct}</p>
                </div>
                {st.status === "running" ? <ProgressBar /> :
                 st.status === "completed" ? <span className="w-5 h-5 rounded-full border-2 border-emerald-500/30 grid place-items-center shrink-0"><Check size={11} className="text-emerald-500" strokeWidth={3} /></span> :
                 st.status === "failed" ? <AlertCircle size={15} className="text-rose-500 shrink-0" /> :
                 <span className="text-[10px] font-semibold text-[#8b95a7] bg-[#eef1f6] rounded-md px-2 py-1 shrink-0">Queued</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Group tasks into top-level + their direct dependents (shown as sub-tasks).
// Guarantees every task is rendered exactly once (as a parent or a sub-task).
function groupTasks(tasks) {
  const byTitle = new Map(tasks.map((t) => [t.title, t]));

  // A task is a sub-task if it depends on exactly one EXISTING task; that task
  // is its parent. (Tasks with 0 or 2+ real deps are top-level.)
  const parentOf = new Map(); // childTitle -> parentTitle
  for (const t of tasks) {
    const deps = (t.depends_on || []).filter((d) => byTitle.has(d) && d !== t.title);
    if (deps.length === 1) parentOf.set(t.title, deps[0]);
  }

  // Avoid cycles: if A->B and B->A, keep only one as child.
  for (const [child, parent] of [...parentOf.entries()]) {
    if (parentOf.get(parent) === child) parentOf.delete(child);
  }

  const childTitles = new Set(parentOf.keys());
  const groups = [];
  const placed = new Set();

  // Top-level tasks (not a child) in original order, each with its children.
  for (const t of tasks) {
    if (childTitles.has(t.title)) continue;
    const subs = tasks.filter((c) => parentOf.get(c.title) === t.title);
    subs.forEach((s) => placed.add(s.title));
    placed.add(t.title);
    groups.push({ task: t, subs });
  }

  // Safety net: any task not yet placed (e.g. its parent was itself a child)
  // is shown as a standalone top-level card so nothing is ever dropped.
  for (const t of tasks) {
    if (!placed.has(t.title)) {
      placed.add(t.title);
      groups.push({ task: t, subs: [] });
    }
  }

  return groups;
}

function AgentTree({ tasks, running, onStop }) {
  const [open, setOpen] = useState(true);
  const done = (tasks || []).filter((t) => t.status === "completed" || t.status === "failed" || t.status === "stopped").length;
  const allDone = tasks?.length > 0 && done === tasks.length;
  // Auto-collapse once everything is done; auto-open while running.
  useEffect(() => { setOpen(!allDone); }, [allDone]);
  if (!tasks || tasks.length === 0) return null;
  const groups = groupTasks(tasks);

  return (
    <div className="neu-card !rounded-b-none px-4 pt-3.5 pb-3 border-b border-[#e3e7ef]">
      {/* Header — click to collapse/expand */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center gap-3 text-left ${open ? "pb-3 mb-3 border-b border-[#e9edf4]" : ""}`}
      >
        <span className="relative w-7 h-7 shrink-0 grid place-items-center">
          {allDone ? (
            <span className="w-7 h-7 rounded-full border-2 border-emerald-500/30 grid place-items-center">
              <Check size={15} className="text-emerald-500" strokeWidth={3} />
            </span>
          ) : (
            <span className="absolute inset-0 rounded-full border-[3px] border-[#e3e6f0] border-t-[#6366f1] animate-spin" />
          )}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-[14.5px] font-bold text-[#1e293b] leading-tight">
            {allDone ? "Plan complete" : "Creating dynamic plan…"}
          </p>
          <p className="text-[12px] text-[#94a3b8] leading-tight mt-0.5 truncate">
            {allDone ? `${done} agents finished` : `Deploying specialized agents · ${done}/${tasks.length} done`}
          </p>
        </div>
        {running && onStop && (
          <span
            role="button"
            onClick={(e) => { e.stopPropagation(); onStop(); }}
            className="neu-btn-ghost flex items-center gap-1.5 px-3 py-1.5 text-[12.5px] font-semibold shrink-0"
          >
            <Square size={11} className="fill-current" /> Stop
          </span>
        )}
        <ChevronDown size={18} className={`text-[#9aa6b8] shrink-0 transition-transform ${open ? "" : "-rotate-90"}`} />
      </button>

      {/* Task cards — capped height; card never grows past this, scrolls instead */}
      {open && (
        <div className="flex flex-col gap-2.5 max-h-[300px] overflow-y-auto pr-1 om-scroll">
          {groups.map((g, i) => (
            <TaskCard key={g.task.id} t={g.task} index={i + 1} subtasks={g.subs} />
          ))}
        </div>
      )}
    </div>
  );
}

function ToolsRow({ tools }) {
  if (!tools || tools.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {tools.map((t, i) => {
        const tone = t.status === "ok" ? "text-emerald-600" : t.status === "fail" ? "text-rose-600" : "text-[#4f46e5]";
        return (
          <span key={`${t.tool}-${i}`} className={`neu-chip flex items-center gap-1.5 px-2.5 py-1 text-[11.5px] font-medium ${tone}`}>
            <Wrench size={12} className={t.status === "running" ? "animate-pulse" : ""} /> {toolLabel(t.tool)}
          </span>
        );
      })}
    </div>
  );
}

// ============ Live Agent Tree (measured SVG circuit) ============
// Planner (root) → agent-type branch cards → leaf (sub-agent) cards, connected
// by real curved SVG paths measured from the actual DOM node positions, so the
// curves always land exactly on the cards. Nodes appear one-by-one as events
// stream; each connector draws in when its child first mounts.
const BRANCH_COLOR = {
  research: { stroke: "#16a34a", node: "bg-[#e7f6ef] border-[#86e0b0] text-[#15803d]" },
  analysis: { stroke: "#7c3aed", node: "bg-[#efeafd] border-[#c3b5ff] text-[#6d28d9]" },
  finance: { stroke: "#7c3aed", node: "bg-[#efeafd] border-[#c3b5ff] text-[#6d28d9]" },
  writing: { stroke: "#4f46e5", node: "bg-[#eef2ff] border-[#c7d2fe] text-[#4338ca]" },
  marketing: { stroke: "#ec4899", node: "bg-[#fde9f1] border-[#f9b4d0] text-[#be185d]" },
  operations: { stroke: "#f97316", node: "bg-[#fff0e0] border-[#ffc78a] text-[#c2410c]" },
  hr: { stroke: "#2563eb", node: "bg-[#e6efff] border-[#adccf7] text-[#1d4ed8]" },
  general: { stroke: "#64748b", node: "bg-[#eef1f6] border-[#cfd5e2] text-[#475569]" },
};
function branchColor(type) { return BRANCH_COLOR[type] || BRANCH_COLOR.general; }

function LiveAgentTree({ tasks, running }) {
  const wrapRef = useRef(null);
  const rootRef = useRef(null);
  const nodeRefs = useRef(new Map()); // taskId -> element
  const [edges, setEdges] = useState([]);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [expanded, setExpanded] = useState(false);

  const empty = !tasks || tasks.length === 0;

  // ---- Build a layered DAG from the real depends_on graph ----
  // Level = longest path from a root. Same level = parallel (same row);
  // deeper level = runs after its parents (next row). This reflects the actual
  // parallel / sequential / mixed execution structure dynamically.
  const byTitle = new Map((tasks || []).map((t) => [t.title, t]));
  const levelOf = new Map();
  const computeLevel = (t, seen = new Set()) => {
    if (levelOf.has(t.title)) return levelOf.get(t.title);
    if (seen.has(t.title)) return 0; // cycle guard
    seen.add(t.title);
    const deps = (t.depends_on || []).filter((d) => byTitle.has(d) && d !== t.title);
    const lvl = deps.length === 0 ? 0 : 1 + Math.max(...deps.map((d) => computeLevel(byTitle.get(d), seen)));
    levelOf.set(t.title, lvl);
    return lvl;
  };
  (tasks || []).forEach((t) => computeLevel(t));
  const levels = [];
  (tasks || []).forEach((t) => {
    const l = levelOf.get(t.title) || 0;
    (levels[l] = levels[l] || []).push(t);
  });

  const setNodeRef = (id) => (el) => {
    if (el) nodeRefs.current.set(id, el);
    else nodeRefs.current.delete(id);
  };

  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || empty) { setEdges([]); return; }
    const base = wrap.getBoundingClientRect();
    const rectOf = (el) => {
      const r = el.getBoundingClientRect();
      return { top: r.top - base.top, bottom: r.bottom - base.top, cx: (r.left + r.right) / 2 - base.left };
    };
    const vcurve = (x1, y1, x2, y2) => {
      const dy = Math.max(18, (y2 - y1) * 0.5);
      return `M ${x1} ${y1} C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`;
    };
    const next = [];
    const rootEl = rootRef.current;
    if (!rootEl) return;
    const root = rectOf(rootEl);

    (tasks || []).forEach((t) => {
      const el = nodeRefs.current.get(t.id);
      if (!el) return;
      const r = rectOf(el);
      const c = branchColor(t.agent_type);
      const op = t.status === "completed" ? 1 : t.status === "running" ? 0.95 : t.status === "failed" ? 0.9 : 0.5;
      const w = t.status === "running" || t.status === "completed" ? 2.4 : 1.8;
      const deps = (t.depends_on || []).filter((d) => byTitle.has(d) && d !== t.title);
      if (deps.length === 0) {
        // root task → connect from Planner
        next.push({ key: `root-${t.id}`, d: vcurve(root.cx, root.bottom, r.cx, r.top), color: c.stroke, op, w });
      } else {
        // connect from each real parent task
        deps.forEach((d) => {
          const pEl = nodeRefs.current.get(byTitle.get(d).id);
          if (!pEl) return;
          const pr = rectOf(pEl);
          next.push({ key: `${d}-${t.id}`, d: vcurve(pr.cx, pr.bottom, r.cx, r.top), color: c.stroke, op, w });
        });
      }
    });
    setSize({ w: wrap.scrollWidth, h: wrap.scrollHeight });
    setEdges(next);
  }, [tasks, size.w]);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return undefined;
    const ro = new ResizeObserver(() => setSize((s) => ({ ...s, w: wrap.clientWidth })));
    ro.observe(wrap);
    return () => ro.disconnect();
  }, []);

  let appearIndex = 0;

  return (
    <div className="neu-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13.5px] font-bold text-[#334155]">Live Agent Tree</h3>
        <div className="flex items-center gap-2">
          {running && <span className="text-[11px] text-[#9aa6b8] animate-pulse">Generating…</span>}
          {!empty && (
            <button onClick={() => setExpanded(true)} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title="Expand workflow">
              <Maximize2 size={14} />
            </button>
          )}
        </div>
      </div>

      {expanded && <AgentGraphCanvas tasks={tasks} onClose={() => setExpanded(false)} />}

      {empty ? (
        <div className="neu-inset p-5 text-center">
          {running ? (
            <>
              <span className="mx-auto mb-2 block w-6 h-6 rounded-full border-[3px] border-[#e3e6f0] border-t-[#6366f1] animate-spin" />
              <p className="text-[12px] text-[#8792a6]">Planning the mission… agents will appear here as the plan forms.</p>
            </>
          ) : (
            <>
              <Boxes size={22} className="mx-auto text-[#b4bdcc] mb-2" />
              <p className="text-[12px] text-[#8792a6]">The agent tree builds here as Orion plans the mission, forming node by node.</p>
            </>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto om-scroll pb-1">
          <div ref={wrapRef} className="relative min-w-max px-2 pb-2">
            {/* SVG edges */}
            <svg className="absolute inset-0 pointer-events-none" width="100%" height={size.h || "100%"} style={{ overflow: "visible" }}>
              {edges.map((e) => (
                <path key={e.key} d={e.d} fill="none" stroke={e.color} strokeWidth={e.w} strokeOpacity={e.op} strokeLinecap="round" className="om-draw" />
              ))}
            </svg>

            {/* Nodes: Planner on top, then one row per dependency level */}
            <div className="relative flex flex-col items-center gap-7">
              <div ref={rootRef} className="neu-raised px-3 py-2 inline-flex items-center gap-2 border border-[#c7d2fe] animate-[rowIn_.3s_ease-out]">
                <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-white shrink-0"><Boxes size={15} /></span>
                <div>
                  <p className="text-[12.5px] font-bold text-[#334155] leading-tight">Orion Planner</p>
                  <p className="text-[10px] text-[#9aa6b8] leading-tight">{tasks.length} tasks</p>
                </div>
              </div>

              {levels.map((row, li) => (
                <div key={li} className="flex items-start gap-6">
                  {row.map((t) => {
                    const c = branchColor(t.agent_type);
                    const dotColor = t.status === "completed" ? "#16a34a" : t.status === "failed" ? "#ef4444" : t.status === "running" ? c.stroke : t.status === "stopped" ? "#9aa6b8" : "#cbd5e1";
                    const delay = `${appearIndex++ * 80}ms`;
                    const typeLabel = (t.agent_type || "general").replace(/\b\w/, (ch) => ch.toUpperCase());
                    return (
                      <div
                        key={t.id}
                        ref={setNodeRef(t.id)}
                        className={`neu-raised w-[172px] px-3 py-2 flex flex-col gap-1 border ${t.status === "running" ? "ring-1 ring-offset-0" : ""}`}
                        style={{ borderColor: `${c.stroke}44`, animation: "treePop .34s cubic-bezier(.2,.8,.2,1) both", animationDelay: delay }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-3.5 h-3.5 rounded-full border-2 grid place-items-center shrink-0" style={{ borderColor: dotColor }}>
                            {t.status === "completed" && <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#16a34a" }} />}
                            {t.status === "running" && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: c.stroke }} />}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: c.stroke }}>{typeLabel}</span>
                        </div>
                        <span className={`text-[11.5px] leading-snug line-clamp-2 ${t.status === "completed" ? "text-[#334155]" : "text-[#64748b]"}`}>{t.title}</span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============ Tools Being Used ============
const TOOL_META = {
  web_search: { label: "Web Search", Icon: Search },
  document_rag: { label: "Document RAG", Icon: FileText },
};
function ToolsBeingUsed({ tools }) {
  const used = tools || [];
  return (
    <div className="neu-card p-4">
      <h3 className="text-[13.5px] font-bold text-[#334155] mb-3">Tools Being Used</h3>
      {used.length === 0 ? (
        <div className="neu-inset p-5 text-center">
          <Wrench size={20} className="mx-auto text-[#b4bdcc] mb-2" />
          <p className="text-[12px] text-[#8792a6]">No tools used yet. They appear here as agents call them.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {used.map((t, i) => {
            const meta = TOOL_META[t.tool] || { label: toolLabel(t.tool), Icon: Wrench };
            const Icon = meta.Icon;
            const active = t.status === "running";
            const okd = t.status === "ok";
            const failed = t.status === "fail";
            const tone = active ? "text-[#4f46e5]" : okd ? "text-emerald-600" : failed ? "text-rose-600" : "text-[#64748b]";
            return (
              <div key={`${t.tool}-${i}`} className={`neu-inset flex items-center gap-2 px-2.5 py-2 ${active ? "ring-1 ring-[#c7d2fe]" : ""}`}>
                <Icon size={14} className={`${tone} ${active ? "animate-pulse" : ""} shrink-0`} />
                <span className="text-[12px] font-medium truncate text-[#334155]">{meta.label}</span>
                {okd && <Check size={12} className="text-emerald-500 ml-auto shrink-0" strokeWidth={3} />}
                {failed && <X size={12} className="text-rose-500 ml-auto shrink-0" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CopyButton({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard?.writeText(text || "");
        setDone(true);
        setTimeout(() => setDone(false), 1500);
      }}
      className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#8792a6] hover:text-[#4f46e5]"
      title="Copy"
    >
      {done ? <CheckCheck size={13} className="text-emerald-500" /> : <Copy size={13} />}
    </button>
  );
}

function ApprovalCard({ approval, onDecide }) {
  const [busy, setBusy] = useState(false);
  const act = async (d) => { setBusy(true); await onDecide(approval, d); setBusy(false); };
  return (
    <div className="neu-card p-4 border-l-4 border-amber-400 mt-2">
      <div className="flex items-start gap-3">
        <span className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-amber-500 shrink-0"><ShieldQuestion size={18} /></span>
        <div className="flex-1 min-w-0">
          <p className="text-[13.5px] font-semibold text-[#334155]">{approval.title || "Approval required"}</p>
          {approval.description && <p className="text-[12.5px] text-[#64748b] mt-0.5">{approval.description}</p>}
          <div className="flex gap-2 mt-3">
            <button disabled={busy} onClick={() => act("approve")} className="neu-btn-primary px-4 h-9 text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-60"><Check size={14} /> Approve</button>
            <button disabled={busy} onClick={() => act("reject")} className="neu-btn-danger px-4 h-9 text-[13px] font-semibold disabled:opacity-60">Reject</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PlanFileOffer({ message }) {
  const [file, setFile] = useState(null); // {kind, name}
  const title = "Orion Plan";

  function generate(kind) {
    const payload = { title, body: message.text, outputs: message.outputs };
    const base = title.replace(/[^\w- ]+/g, "").trim() || "orion-plan";
    if (kind === "pdf") {
      exportPdf(payload);
      setFile({ kind: "pdf", name: `${base}.pdf` });
    } else {
      exportHtml(payload);
      setFile({ kind: "html", name: `${base}.html` });
    }
  }

  // Generated file card
  if (file) {
    const isPdf = file.kind === "pdf";
    return (
      <div className="neu-card mt-3 flex items-center gap-3 px-3.5 py-3 max-w-sm">
        <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0 ${isPdf ? "text-rose-500" : "text-[#4f46e5]"}`}>
          {isPdf ? <FileDown size={20} /> : <FileCode2 size={20} />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-[#334155] truncate">{file.name}</p>
          <p className="text-[11px] text-[#9aa6b8]">{isPdf ? "PDF document" : "HTML document"} · ready</p>
        </div>
        <button
          onClick={() => generate(file.kind)}
          className="neu-btn-ghost text-[11.5px] font-medium px-2.5 py-1.5"
          title="Generate again"
        >
          {isPdf ? "Open print" : "Download"}
        </button>
      </div>
    );
  }

  // Text offer + action chips
  return (
    <div className="mt-3">
      <p className="text-[12.5px] text-[#64748b] mb-2 flex items-start gap-1.5">
        <Sparkles size={13} className="text-[#4f46e5] mt-0.5 shrink-0" />
        If you want, I can turn this plan into a downloadable file.
      </p>
      <div className="flex gap-2">
        <button onClick={() => generate("pdf")} className="neu-btn-ghost flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium">
          <FileDown size={14} className="text-rose-500" /> Generate PDF
        </button>
        <button onClick={() => generate("html")} className="neu-btn-ghost flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium">
          <FileCode2 size={14} className="text-[#4f46e5]" /> Generate HTML
        </button>
      </div>
    </div>
  );
}

function ClarifyBlock({ question, original, onReply, disabled }) {
  const [answer, setAnswer] = useState("");
  const [sent, setSent] = useState(false);
  const submit = () => {
    const a = answer.trim();
    if (!a) return;
    setSent(true);
    onReply(original, a);
  };
  return (
    <div className="border-l-4 border-[#6366f1] pl-3">
      <div className="flex items-center gap-2 mb-1.5">
        <ShieldQuestion size={15} className="text-[#4f46e5]" />
        <span className="text-[12px] font-semibold text-[#4f46e5]">Orion needs a bit more detail</span>
      </div>
      <p className="text-[13.5px] text-[#334155] mb-3">{question}</p>
      {!sent && (
        <div className="neu-inset flex items-center gap-2 pl-3 pr-1.5 py-1.5">
          <input
            autoFocus
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Type your answer…"
            disabled={disabled}
            className="flex-1 min-w-0 bg-transparent border-0 text-[13px] text-[#334155] placeholder:text-[#9aa6b8] focus:outline-none py-1"
          />
          <button onClick={submit} disabled={disabled} className="neu-btn-primary w-8 h-8 rounded-full grid place-items-center disabled:opacity-60"><ArrowUp size={15} strokeWidth={2.6} /></button>
        </div>
      )}
    </div>
  );
}

// =====================================================================
export const ViewCommandCenter = () => {
  const toast = useToast();
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]); // in-memory render model for the active conversation
  const [prompt, setPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [pendingFile, setPendingFile] = useState(null); // attach-with-message (not sent yet)
  const [user, setUser] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [ctxOpen, setCtxOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [context, setContext] = useState([]);

  const cancelRef = useRef(null);
  const activeMissionRef = useRef(null);
  const fileRef = useRef(null);
  const scrollRef = useRef(null);
  const textareaRef = useRef(null);

  const resetComposerHeight = useCallback(() => {
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, []);

  // --- load conversations + context on mount ---
  const loadConversations = useCallback(async () => {
    try {
      const list = await chatApi.listConversations();
      setConversations(list);
      return list;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    authApi.me().then(setUser).catch(() => {});
    chatApi.listContext().then(setContext).catch(() => {});
    (async () => {
      const list = await loadConversations();
      if (list.length > 0) openConversation(list[0].id);
    })();
    return () => cancelRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // --- conversation ops ---
  async function newConversation() {
    cancelRef.current?.();
    setRunning(false);
    const conv = await chatApi.createConversation("New chat");
    setConversations((c) => [{ ...conv, message_count: 0 }, ...c]);
    setActiveId(conv.id);
    setMessages([]);
    setPendingFile(null);
    setPrompt("");
  }

  async function openConversation(id) {
    if (running) cancelRef.current?.();
    setRunning(false);
    setActiveId(id);
    setPendingFile(null);
    try {
      const conv = await chatApi.getConversation(id);
      // map persisted messages → render model
      setMessages(
        (conv.messages || []).map((m) => ({
          dbId: m.id,
          role: m.role,
          text: m.content,
          createdAt: m.created_at,
          attachments: m.attachments || [],
          outputs: m.outputs || [],
          status: m.status,
          tree: [], // persisted messages don't replay live tree; outputs stand in
          tools: [],
        }))
      );
    } catch {
      setMessages([]);
    }
  }

  async function removeConversation(id, e) {
    e?.stopPropagation();
    try {
      await chatApi.deleteConversation(id);
      setConversations((c) => c.filter((x) => x.id !== id));
      if (activeId === id) {
        const rest = conversations.filter((x) => x.id !== id);
        if (rest[0]) openConversation(rest[0].id);
        else { setActiveId(null); setMessages([]); }
      }
      toast.success("Conversation deleted");
    } catch (err) {
      toast.error(err.message);
    }
  }

  async function commitRename(id, title) {
    setRenaming(null);
    const t = (title || "").trim();
    if (!t) return;
    try {
      await chatApi.renameConversation(id, t);
      setConversations((c) => c.map((x) => (x.id === id ? { ...x, title: t } : x)));
    } catch (err) { toast.error(err.message); }
  }

  // --- messaging ---
  const updateLastAgent = useCallback((patch) => {
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].role === "assistant") {
          next[i] = typeof patch === "function" ? patch(next[i]) : { ...next[i], ...patch };
          break;
        }
      }
      return next;
    });
  }, []);

  async function handleDecision(approval, decision) {
    try {
      await missionApi[decision === "approve" ? "approveDecision" : "rejectDecision"]?.(approval.decision_id);
      toast.success(decision === "approve" ? "Approved" : "Rejected");
    } catch {
      toast.info(`Marked ${decision}d (approvals API wiring pending).`);
    }
    updateLastAgent((m) => ({ ...m, approvals: (m.approvals || []).filter((a) => a.decision_id !== approval.decision_id) }));
  }

  async function send(text) {
    const content = (text ?? prompt).trim();
    if ((!content && !pendingFile) || running) return;

    // ensure a conversation exists
    let convId = activeId;
    if (!convId) {
      const conv = await chatApi.createConversation(content.slice(0, 40) || "New chat");
      convId = conv.id;
      setActiveId(convId);
      setConversations((c) => [{ ...conv, message_count: 0 }, ...c]);
    }

    const now = new Date().toISOString();
    const attachments = pendingFile ? [{ name: pendingFile.name, size: pendingFile.size }] : [];

    // optimistic user message (with attachment riding along)
    setMessages((m) => [...m, { role: "user", text: content, createdAt: now, attachments }]);
    setPrompt("");
    resetComposerHeight();
    const fileToSend = pendingFile?.file || null;
    setPendingFile(null);

    // persist user message
    chatApi.addMessage(convId, { role: "user", content, attachments }).catch(() => {});
    // auto-title if this is the first message
    const conv = conversations.find((c) => c.id === convId);
    if (conv && (conv.title === "New chat" || !conv.message_count)) {
      const title = content.slice(0, 40) || "New chat";
      chatApi.renameConversation(convId, title).catch(() => {});
      setConversations((cs) => cs.map((x) => (x.id === convId ? { ...x, title } : x)));
    }

    // ingest the attached doc (if any) so agents can use it this turn
    if (fileToSend) {
      try {
        const up = missionApi.uploadDocument || authApi.uploadFile;
        await up?.(fileToSend);
      } catch {
        /* degrade silently */
      }
    }

    await runMission(convId, content, false);
  }

  // Runs a mission turn and wires the live event stream into the last assistant
  // message. `clarified` is true when the user is answering a clarifying question.
  async function runMission(convId, promptText, clarified) {
    setRunning(true);

    // assistant placeholder with its own live tree/tools + streamed text buffer
    const agentCreatedAt = new Date().toISOString();
    setMessages((m) => [...m, {
      role: "assistant", text: "", streamed: "", createdAt: agentCreatedAt,
      tree: [], tools: [], outputs: [], approvals: [], status: "running",
    }]);
    const assistantMsg = await chatApi.addMessage(convId, { role: "assistant", content: "", status: "running" }).catch(() => null);

    let missionId;
    try {
      const res = await missionApi.createMission(promptText, { conversationId: convId, clarified });
      missionId = res.mission_id;
      activeMissionRef.current = missionId;
      if (assistantMsg) chatApi.updateMessage(assistantMsg.id, { mission_id: missionId }).catch(() => {});
    } catch (e) {
      toast.error(e.message || "Could not reach the mission backend on :8081.");
      updateLastAgent({ text: e.message || "Could not start the mission.", status: "failed" });
      setRunning(false);
      return;
    }

    const setTree = (fn) => updateLastAgent((m) => ({ ...m, tree: fn(m.tree || []) }));
    const setTools = (fn) => updateLastAgent((m) => ({ ...m, tools: fn(m.tools || []) }));

    cancelRef.current = streamMission(missionId, {
      onEvent: (ev) => {
        switch (ev.event) {
          case "clarification_needed":
            // Pause: show the question inline with a reply box.
            updateLastAgent({ status: "clarify", text: ev.question, clarifyOriginal: ev.original_prompt });
            if (assistantMsg) chatApi.updateMessage(assistantMsg.id, { content: ev.question, status: "done" }).catch(() => {});
            setRunning(false);
            break;
          case "planning_started":
            updateLastAgent((m) => (m.text ? m : { ...m, text: "Planning the mission…" }));
            break;
          case "task_created":
            setTree((prev) => [...prev, { ...ev.task, tools_needed: ev.task.tools_needed || [], status: "pending" }]);
            break;
          case "task_started":
            setTree((prev) => prev.map((t) => (t.id === ev.task_id ? { ...t, status: "running", agent_name: ev.agent_name } : t)));
            break;
          case "tool_call":
            setTools((prev) => (prev.some((t) => t.tool === ev.tool && t.status === "running") ? prev : [...prev, { tool: ev.tool, status: "running" }]));
            break;
          case "tool_result":
            setTools((prev) => prev.map((t) => (t.tool === ev.tool && t.status === "running" ? { ...t, status: ev.success ? "ok" : "fail" } : t)));
            break;
          case "task_completed":
            setTree((prev) => prev.map((t) => (t.id === ev.task_id ? { ...t, status: "completed" } : t)));
            break;
          case "task_failed":
            setTree((prev) => prev.map((t) => (t.id === ev.task_id ? { ...t, status: "failed" } : t)));
            break;
          case "approval_required":
            updateLastAgent((m) => ({ ...m, approvals: [...(m.approvals || []), ev] }));
            break;
          case "answer_chunk":
            // Typewriter: append each streamed chunk to the visible text.
            updateLastAgent((m) => ({ ...m, streamed: (m.streamed || "") + ev.text, text: (m.streamed || "") + ev.text, status: "streaming" }));
            break;
          case "memory_updated":
            chatApi.listContext().then(setContext).catch(() => {});
            if (ev.facts?.length) toast.info(`Learned: ${ev.facts.map((f) => f.key).join(", ")}`);
            break;
          case "mission_completed": {
            const finalText = ev.answer || (ev.status === "partial" ? "Done with some issues." : "Done.");
            updateLastAgent({ text: finalText, outputs: ev.outputs || [], status: "done" });
            if (assistantMsg) chatApi.updateMessage(assistantMsg.id, { content: finalText, outputs: ev.outputs || [], status: "done" }).catch(() => {});
            toast.success("Mission complete.");
            break;
          }
          case "mission_failed":
            updateLastAgent({ text: ev.error || "Mission failed.", status: "failed" });
            if (assistantMsg) chatApi.updateMessage(assistantMsg.id, { content: ev.error || "Mission failed.", status: "failed" }).catch(() => {});
            toast.error(ev.error || "Mission failed.");
            break;
          case "mission_stopped":
            updateLastAgent((m) => ({ ...m, text: m.streamed || m.text || "Stopped.", status: "done" }));
            setRunning(false);
            break;
          default:
            break;
        }
      },
      onDone: () => { setRunning(false); loadConversations(); },
      onError: (msg) => { toast.error(msg); updateLastAgent({ text: msg, status: "failed" }); setRunning(false); },
    });
  }

  // User answers a clarifying question → re-run with the combined prompt, skipping clarify.
  async function replyClarify(original, answer) {
    const a = (answer || "").trim();
    if (!a || !activeId) return;
    const now = new Date().toISOString();
    setMessages((m) => [...m, { role: "user", text: a, createdAt: now, attachments: [] }]);
    chatApi.addMessage(activeId, { role: "user", content: a }).catch(() => {});
    const combined = `${original}\n\nClarification: ${a}`;
    await runMission(activeId, combined, true);
  }

  function stop() {
    // Stop watching the stream.
    cancelRef.current?.();
    cancelRef.current = null;
    // Tell the backend to actually cancel the mission so it stops working.
    const mid = activeMissionRef.current;
    if (mid) missionApi.stopMission(mid).catch(() => {});
    activeMissionRef.current = null;
    // Immediately finalize the current assistant message — keep whatever was
    // generated so far, clear all loading/running state.
    updateLastAgent((m) => {
      const hasContent = (m.streamed || m.text) && m.status !== "running";
      return {
        ...m,
        text: m.streamed || m.text || "Stopped.",
        status: hasContent ? "done" : m.text ? "done" : "done",
        tree: (m.tree || []).map((t) => (t.status === "running" || t.status === "pending" ? { ...t, status: "stopped" } : t)),
        tools: (m.tools || []).map((t) => (t.status === "running" ? { ...t, status: "fail" } : t)),
      };
    });
    setRunning(false);
    toast.info("Stopped.");
  }

  function pickFile(e) {
    const file = e.target.files?.[0];
    if (e.target) e.target.value = "";
    if (!file) return;
    setPendingFile({ name: file.name, size: Math.max(1, Math.round(file.size / 1024)), file });
  }

  async function removeContextFact(key) {
    try { await chatApi.deleteContext(key); setContext(await chatApi.listContext()); } catch (err) { toast.error(err.message); }
  }

  const initials = (() => {
    const n = user?.full_name || "You";
    const p = n.trim().split(/\s+/);
    return ((p[0]?.[0] || "") + (p[1]?.[0] || "")).toUpperCase() || "ME";
  })();

  const lastAgent = [...messages].reverse().find((m) => m.role === "assistant");
  const showFollowUps = !running && lastAgent?.status === "done";
  // The Live Agent Tree persists for the WHOLE conversation: it's the union of
  // every mission turn's tasks. A new prompt adds its tasks (a new Planner-rooted
  // subtree) to the same graph — so the tree keeps growing/continuing until a
  // new conversation starts (which resets `messages`). Each mission's tasks are
  // tagged with a mission index so they render as distinct subtrees.
  const dockTasks = (() => {
    const out = [];
    let m = 0;
    for (const msg of messages) {
      if (msg.role !== "assistant" || !msg.tree?.length) continue;
      m += 1;
      for (const t of msg.tree) out.push({ ...t, _mission: m });
    }
    return out;
  })();
  const dockRunning = running && lastAgent && lastAgent.status !== "done" && lastAgent.status !== "failed";

  return (
    <div className="neu-surface h-full flex">
      {/* ---------------- Conversation sidebar ---------------- */}
      <aside
        className={`shrink-0 flex flex-col border-r border-[#e2e6ee] overflow-hidden transition-all duration-300 ${
          sidebarOpen ? "w-64 p-3" : "w-0 p-0 border-r-0"
        }`}
      >
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setSidebarOpen(false)}
            className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5] shrink-0"
            title="Hide sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
          <button onClick={newConversation} className="neu-btn-primary h-10 flex-1 text-[13.5px] font-semibold flex items-center justify-center gap-2">
            <MessageSquarePlus size={16} /> New chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-hide flex flex-col gap-1.5">
          {conversations.length === 0 && (
            <p className="text-[12px] text-[#9aa6b8] px-2 py-4 text-center">No chats yet. Start one above.</p>
          )}
          {conversations.map((c) => {
            const active = c.id === activeId;
            return (
              <div key={c.id} className={`neu-nav ${active ? "neu-nav-active" : ""} group flex items-center gap-2 px-2.5 py-2`}>
                {renaming === c.id ? (
                  <input
                    autoFocus
                    defaultValue={c.title}
                    onBlur={(e) => commitRename(c.id, e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") commitRename(c.id, e.target.value); if (e.key === "Escape") setRenaming(null); }}
                    className="flex-1 min-w-0 bg-transparent text-[13px] text-[#334155] focus:outline-none"
                  />
                ) : (
                  <button onClick={() => openConversation(c.id)} className="flex-1 min-w-0 text-left">
                    <p className={`text-[13px] truncate ${active ? "text-[#4f46e5] font-semibold" : "text-[#4a5568] font-medium"}`}>{c.title}</p>
                    <p className="text-[10.5px] text-[#9aa6b8]">{convTime(c.updated_at)} · {c.message_count || 0} msgs</p>
                  </button>
                )}
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button onClick={(e) => { e.stopPropagation(); setRenaming(c.id); }} className="w-6 h-6 grid place-items-center rounded text-[#9aa6b8] hover:text-[#4f46e5]" title="Rename"><Pencil size={12} /></button>
                  <button onClick={(e) => removeConversation(c.id, e)} className="w-6 h-6 grid place-items-center rounded text-[#9aa6b8] hover:text-rose-500" title="Delete"><Trash2 size={12} /></button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Memory — automatically learned across chats */}
        <div className="mt-3 pt-3 border-t border-[#e2e6ee]">
          <button onClick={() => setCtxOpen((o) => !o)} className="w-full flex items-center justify-between text-[12px] font-semibold text-[#4a5568] px-1 py-1">
            <span className="flex items-center gap-1.5"><Globe size={13} className="text-[#4f46e5]" /> Memory</span>
            <span className="neu-chip text-[9.5px] font-bold text-[#8792a6] px-1.5 py-0.5">{context.length}</span>
          </button>
          {ctxOpen && (
            <div className="neu-inset p-2 mt-1.5 flex flex-col gap-1">
              <p className="text-[10.5px] text-[#9aa6b8] px-1 mb-0.5 flex items-center gap-1">
                <Sparkles size={10} className="text-[#4f46e5]" /> Learned automatically from your chats · used everywhere
              </p>
              {context.length === 0 && <p className="text-[11px] text-[#9aa6b8] px-1">Nothing learned yet. Keep chatting — Orion remembers durable facts on its own.</p>}
              {context.map((f) => (
                <div key={f.key} className="flex items-center gap-1.5 group">
                  <span className="text-[11px] text-[#4a5568] flex-1 min-w-0 truncate"><b className="text-[#334155]">{f.key}:</b> {f.value}</span>
                  <button onClick={() => removeContextFact(f.key)} className="opacity-0 group-hover:opacity-100 text-[#9aa6b8] hover:text-rose-500" title="Forget this"><X size={11} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* ---------------- Main thread ---------------- */}
      <div className="flex-1 flex flex-col min-h-0 p-6 sm:p-7 relative">
        <div className="shrink-0 mb-5 flex items-start gap-3">
          {!sidebarOpen && (
            <div className="flex items-center gap-2 pt-0.5">
              <button
                onClick={() => setSidebarOpen(true)}
                className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5] shrink-0"
                title="Show sidebar"
              >
                <PanelLeft size={18} />
              </button>
              <button
                onClick={newConversation}
                className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5] shrink-0"
                title="New chat"
              >
                <MessageSquarePlus size={18} />
              </button>
            </div>
          )}
          <div>
            <h1 className="text-[22px] leading-none font-bold tracking-[-0.3px] text-[#334155]">Command Center</h1>
            <p className="text-[13px] text-[#64748b] mt-1">Describe a goal. Orion plans it, assigns agents, and runs it live.</p>
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto pr-1 pb-40 space-y-1 scrollbar-hide">
          <div className="max-w-3xl w-full mx-auto">
          {messages.length === 0 && (
            <div className="neu-card p-8 text-center max-w-lg mx-auto mt-6">
              <span className="neu-circle w-14 h-14 rounded-2xl grid place-items-center text-[#4f46e5] mx-auto mb-4"><Sparkles size={24} /></span>
              <h3 className="text-[16px] font-semibold text-[#334155] mb-1">What should Orion work on?</h3>
              <p className="text-[13px] text-[#8792a6]">Type a goal below, or pick a starter. Attach a document to give agents more to work with.</p>
            </div>
          )}

          {messages.map((m, i) => {
            const prev = messages[i - 1];
            const newDay = i === 0 || dayKey(prev?.createdAt) !== dayKey(m.createdAt);
            return (
              <div key={m.dbId || i}>
                {newDay && (
                  <div className="flex items-center gap-3 my-4">
                    <div className="flex-1 h-px bg-[#dfe4ee]" />
                    <span className="text-[11px] font-semibold text-[#9aa6b8]">{dayLabel(m.createdAt)}</span>
                    <div className="flex-1 h-px bg-[#dfe4ee]" />
                  </div>
                )}

                {m.role === "user" ? (
                  <div className="flex items-start gap-2.5 justify-end mb-4 group">
                    <div className="max-w-xl flex flex-col items-end">
                      <div className="neu-raised rounded-[16px] rounded-tr-md px-4 py-2.5 text-[13.5px] leading-relaxed text-[#334155] whitespace-pre-wrap">
                        {m.text}
                      </div>
                      {m.attachments?.map((a, j) => (
                        <div key={j} className="neu-raised mt-1.5 flex items-center gap-2 px-3 py-2">
                          <FileText size={14} className="text-[#4f46e5]" />
                          <span className="text-[12px] text-[#4a5568] truncate">{a.name}</span>
                          {a.size && <span className="text-[10.5px] text-[#9aa6b8]">{a.size} KB</span>}
                        </div>
                      ))}
                      <div className="flex items-center gap-1.5 justify-end mt-1 pr-1">
                        <span className="text-[10.5px] text-[#9aa6b8]">{fmtTime(m.createdAt)}</span>
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity"><CopyButton text={m.text} /></span>
                      </div>
                    </div>
                    <span className="w-8 h-8 shrink-0 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-[11px] font-semibold text-white">{initials}</span>
                  </div>
                ) : (
                  <div className="flex gap-2.5 items-start mb-5 group">
                    <span className="neu-circle w-8 h-8 shrink-0 rounded-full grid place-items-center text-[#4f46e5]">
                      {m.status === "running" ? <Loader2 size={15} className="animate-spin" /> : m.status === "failed" ? <AlertCircle size={15} className="text-rose-500" /> : <Boxes size={15} />}
                    </span>
                    <div className="flex-1 min-w-0">
                      {m.status === "clarify" ? (
                        <div className="neu-card p-4 rounded-[16px] rounded-tl-md">
                          <ClarifyBlock question={m.text} original={m.clarifyOriginal} onReply={replyClarify} disabled={running} />
                        </div>
                      ) : (
                        <div className="pt-1">
                          {m.text ? (
                            m.status === "streaming" ? (
                              <div className="om-streaming">
                                <Markdown>{m.text}</Markdown>
                              </div>
                            ) : m.status === "failed" ? (
                              <p className="text-[14px] leading-relaxed whitespace-pre-wrap text-rose-600">{m.text}</p>
                            ) : (
                              <Markdown>{m.text}</Markdown>
                            )
                          ) : m.status === "running" ? (
                            <p className="text-[13px] text-[#8792a6] flex items-center gap-2"><Loader2 size={13} className="animate-spin" /> Thinking…</p>
                          ) : null}
                          <ToolsRow tools={m.tools} />
                          {m.outputs?.map((o, j) => {
                            const body = o.result?.data || o.result?.summary || o.result?.error;
                            return (
                              <div key={j} className="neu-inset p-3.5 mt-2.5">
                                <h4 className="text-[12.5px] font-semibold text-[#334155] mb-1">{o.task}</h4>
                                {body ? (
                                  <Markdown compact>{body}</Markdown>
                                ) : (
                                  <p className="text-[12.5px] italic text-[#9aa6b8]">No output was produced for this task.</p>
                                )}
                              </div>
                            );
                          })}
                          {m.approvals?.map((a) => <ApprovalCard key={a.decision_id} approval={a} onDecide={handleDecision} />)}

                          {/* Plan file offer — only when a plan/result was produced */}
                          {m.status === "done" && m.outputs?.length > 0 && (
                            <PlanFileOffer message={m} />
                          )}
                        </div>
                      )}

                      {/* message actions — copy only */}
                      <div className="flex items-center gap-1.5 mt-1.5">
                        <span className="text-[10.5px] text-[#9aa6b8]">{fmtTime(m.createdAt)}</span>
                        {(m.status === "done" || m.status === "failed") && (
                          <span className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <CopyButton text={[m.text, ...(m.outputs || []).map((o) => `${o.task}\n${o.result?.data || o.result?.summary || ""}`)].join("\n\n")} />
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Suggested follow-ups */}
          {showFollowUps && (
            <div className="flex flex-wrap gap-2 pl-11 mb-2">
              {FOLLOW_UPS.map((f) => (
                <button key={f} onClick={() => send(f)} className="neu-btn-ghost text-[12px] font-medium px-3 py-1.5 flex items-center gap-1.5">
                  <Sparkles size={12} className="text-[#4f46e5]" /> {f}
                </button>
              ))}
            </div>
          )}
          </div>
        </div>

        {/* ---------------- Floating composer ---------------- */}
        <div className="absolute bottom-0 left-0 right-0 px-6 sm:px-7 pb-6 pt-10 pointer-events-none bg-gradient-to-t from-[#eef1f6] via-[#eef1f6]/90 to-transparent">
          <div className="max-w-3xl w-full mx-auto pointer-events-auto">
            {pendingFile && (
              <div className="mb-2 flex">
                <span className="neu-chip flex items-center gap-2 px-3 py-1.5 text-[12px] font-medium text-[#4a5568]">
                  <Paperclip size={13} /> {pendingFile.name} <span className="text-[#9aa6b8]">{pendingFile.size} KB</span>
                  <button onClick={() => setPendingFile(null)} className="text-[#9aa6b8] hover:text-rose-500"><X size={13} /></button>
                </span>
              </div>
            )}

            {/* starter chips float just above the bar on an empty chat */}
            {messages.length === 0 && (
              <div className="flex gap-2 mb-3 flex-wrap justify-center">
                {QUICK_TAGS.map(({ label, Icon, fill }) => (
                  <button key={label} onClick={() => setPrompt(fill)} className="neu-btn-ghost flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium"><Icon size={14} /> {label}</button>
                ))}
              </div>
            )}

            {/* Task list docked directly on top of the input — one seamless unit */}
            {dockTasks.length > 0 && (
              <AgentTree tasks={dockTasks} running={dockRunning} onStop={stop} />
            )}

            <div className={`neu-card flex items-end gap-2 pl-4 pr-2.5 py-2.5 ${dockTasks.length > 0 ? "rounded-t-none rounded-b-[20px]" : "rounded-[20px]"}`}>
              <textarea
                ref={textareaRef}
                rows={1}
                value={prompt}
                onChange={(e) => { setPrompt(e.target.value); e.target.style.height = "auto"; if (e.target.value) e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px"; }}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
                placeholder="Message Orion…   (Shift+Enter for a new line)"
                disabled={running}
                className="flex-1 min-w-0 bg-transparent border-0 text-[14px] leading-6 text-[#334155] placeholder:text-[#9aa6b8] focus:outline-none resize-none py-1.5 max-h-40 scrollbar-hide"
              />
              <input ref={fileRef} type="file" className="hidden" onChange={pickFile} accept=".txt,.md,.csv,.pdf,.docx" />
              <button onClick={() => fileRef.current?.click()} className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#64748b] hover:text-[#4f46e5] shrink-0" aria-label="Attach"><Paperclip size={16} /></button>
              {running ? (
                <button onClick={stop} className="neu-btn-danger flex items-center gap-1.5 px-3.5 h-9 text-[12.5px] font-semibold shrink-0"><Square size={11} className="fill-current" /> Stop</button>
              ) : (
                <button onClick={() => send()} className="neu-btn-primary w-9 h-9 rounded-full grid place-items-center shrink-0" aria-label="Send"><ArrowUp size={17} strokeWidth={2.6} /></button>
              )}
            </div>
            <p className="text-center text-[10.5px] text-[#9aa6b8] mt-2">Orion can make mistakes. Review important results.</p>
          </div>
        </div>
      </div>

      {/* ---------------- Right panel: Live Agent Tree + Tools ---------------- */}
      {lastAgent && (
        <div className="w-[400px] shrink-0 border-l border-[#e2e6ee] p-4 flex flex-col gap-4 overflow-y-auto scrollbar-hide">
          <LiveAgentTree tasks={dockTasks} running={dockRunning} />
          <ToolsBeingUsed tools={lastAgent?.tools || []} />
        </div>
      )}
    </div>
  );
};
