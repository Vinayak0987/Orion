import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft, Rocket, ChevronDown, CheckCircle2, CircleDot, Clock, AlertCircle,
  Square, RotateCw, FileDown, FileCode2, FileJson, Trash2, Wrench, Globe, FileText,
  Users, ListChecks, Boxes, X, ArrowRight,
  Search, Megaphone, Settings2, ChartNoAxesColumn, ChartNoAxesCombined, Workflow, Database,
} from "lucide-react";

import { missionApi } from "../../missionApi";
import { useToast } from "../ui/Toast.jsx";
import { Markdown } from "../ui/Markdown.jsx";
import { ArtifactCard } from "../ui/ArtifactCard.jsx";
import { Modal } from "../ui/Modal.jsx";
import { exportHtml, exportPdf } from "../../utils/exportDoc.js";
import { ExecutionGraph } from "./ExecutionGraph.jsx";

const TABS = ["Overview", "Tasks", "Agents", "Tools", "Evidence", "Results", "Trace"];

const STATUS = {
  pending: { Icon: Clock, tone: "text-amber-600", label: "Pending" },
  running: { Icon: CircleDot, tone: "text-blue-600", label: "Running" },
  completed: { Icon: CheckCircle2, tone: "text-emerald-600", label: "Completed" },
  failed: { Icon: AlertCircle, tone: "text-rose-600", label: "Failed" },
  stopped: { Icon: Square, tone: "text-[#8792a6]", label: "Stopped" },
  planning: { Icon: Clock, tone: "text-amber-600", label: "Planning" },
  partial: { Icon: AlertCircle, tone: "text-amber-600", label: "Partial" },
};
const toolLabel = (t) => (t || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

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
const agentMeta = (t) => AGENT_META[t] || AGENT_META.general;

const TOOL_ICON = { web_search: Globe, web_scraper: Globe, document_rag: Database, document_reader: FileText };
const toolIcon = (id) => TOOL_ICON[id] || Wrench;

function Empty({ icon: Icon, text }) {
  return (
    <div className="neu-inset p-10 text-center">
      <Icon size={24} className="mx-auto text-[#b4bdcc] mb-2" />
      <p className="text-[13px] text-[#8792a6]">{text}</p>
    </div>
  );
}

function StatTile({ label, value, tone }) {
  return (
    <div className="neu-raised px-4 py-2.5 flex-1">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[#b4bdcc]">{label}</p>
      <p className={`text-[18px] font-bold ${tone}`}>{value}</p>
    </div>
  );
}

function ProgressRing({ pct }) {
  const r = 24, c = 2 * Math.PI * r;
  return (
    <div className="relative w-14 h-14 grid place-items-center shrink-0">
      <svg className="w-full h-full -rotate-90">
        <circle cx="28" cy="28" r={r} stroke="#d4d9e4" strokeWidth="5" fill="none" />
        <circle cx="28" cy="28" r={r} stroke="#4f46e5" strokeWidth="5" fill="none" strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)} strokeLinecap="round" />
      </svg>
      <span className="absolute text-[12px] font-bold text-[#334155]">{pct}%</span>
    </div>
  );
}

export const ViewMissionDetails = ({ missionId, onBack, onNavigate, onViewDetails }) => {
  const toast = useToast();
  const [mission, setMission] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("Overview");
  const [selectedTask, setSelectedTask] = useState(null);
  const [actionsOpen, setActionsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [tools, setTools] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [trace, setTrace] = useState(null);
  const actionsRef = useRef(null);

  const load = useCallback(() => {
    if (!missionId) return;
    missionApi.mission(missionId).then(setMission).catch((e) => setError(e.message));
  }, [missionId]);

  useEffect(() => { load(); }, [load]);

  // Reset per-mission view state when switching to a different mission (e.g. Re-run).
  useEffect(() => {
    setTab("Overview"); setSelectedTask(null); setTools(null); setEvidence(null); setTrace(null); setMission(null); setError("");
  }, [missionId]);

  // Poll while running.
  const liveStatus = mission?.status;
  useEffect(() => {
    if (!mission || ["completed", "failed", "partial", "stopped"].includes(mission.status)) return undefined;
    const id = setInterval(() => {
      load();
      missionApi.missionTools(missionId).then((d) => setTools(d.tools || [])).catch(() => {});
      missionApi.missionTrace(missionId).then(setTrace).catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [liveStatus, load, missionId]);

  // Close actions menu on outside click.
  useEffect(() => {
    if (!actionsOpen) return undefined;
    const onDoc = (e) => actionsRef.current && !actionsRef.current.contains(e.target) && setActionsOpen(false);
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [actionsOpen]);

  // Lazy-load tab data.
  useEffect(() => {
    if (!missionId) return;
    // Load tools + trace eagerly (Overview graph shows real tools used + model).
    if (tools === null) missionApi.missionTools(missionId).then((d) => setTools(d.tools || [])).catch(() => setTools([]));
    if (trace === null) missionApi.missionTrace(missionId).then(setTrace).catch(() => setTrace({ steps: [], total_cost_usd: 0, total_tokens: 0 }));
    if ((tab === "Evidence" || tab === "Results" || tab === "Trace") && evidence === null)
      missionApi.missionEvidence(missionId).then((d) => setEvidence(d.evidence || [])).catch(() => setEvidence([]));
  }, [tab, missionId, tools, evidence, trace]);

  // Real tools actually used + real model (from execution traces).
  const toolsUsed = (tools || []).map((t) => t.tool);
  const usedModel = (trace?.steps || []).find((s) => s.type === "llm" && s.model)?.model
    || (trace?.steps || []).find((s) => s.type === "llm" && s.provider)?.provider || null;

  const tasks = mission?.tasks || [];
  const done = tasks.filter((t) => ["completed", "failed", "stopped"].includes(t.status)).length;
  const pct = tasks.length ? Math.round((100 * done) / tasks.length) : 0;
  const isRunning = mission && ["planning", "running"].includes(mission.status);

  function buildExportPayload() {
    return {
      title: mission.title || "Orion Mission",
      body: `${mission.prompt}`,
      outputs: tasks.filter((t) => t.result).map((t) => ({ task: t.title, result: t.result })),
      charts: [
        ...(evidence || []).flatMap((e) => (Array.isArray(e.output?.images) ? e.output.images : [])),
        ...tasks.flatMap((t) => (Array.isArray(t.result?.images) ? t.result.images : [])),
      ],
    };
  }

  async function reRun() {
    setActionsOpen(false);
    try {
      const res = await missionApi.createMission(mission.prompt, { clarified: true });
      toast.success("Re-running mission…");
      if (res?.mission_id && onViewDetails) {
        // Open the new mission's detail view — its live polling shows it running.
        onViewDetails(res.mission_id);
      } else {
        onNavigate?.("missions");
      }
    } catch (e) { toast.error(e.message); }
  }
  async function doStop() {
    try { await missionApi.stopMission(missionId); toast.info("Mission stopped."); load(); } catch (e) { toast.error(e.message); }
  }
  async function doDelete() {
    try { await missionApi.deleteMission(missionId); toast.success("Mission deleted."); onBack?.(); } catch (e) { toast.error(e.message); }
  }
  function downloadJson() {
    setActionsOpen(false);
    missionApi.exportMissionJson(missionId).then((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
      a.download = `${(mission.title || "mission").replace(/[^\w- ]+/g, "")}.json`; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }).catch((e) => toast.error(e.message));
  }

  if (error) {
    return (
      <div className="neu-surface h-full p-7">
        <button onClick={onBack} className="neu-btn-ghost flex items-center gap-2 px-3 h-9 text-[13px] font-semibold mb-4"><ArrowLeft size={15} /> Back</button>
        <div className="neu-card p-4 border-l-4 border-rose-400 max-w-lg"><p className="text-[13px] text-rose-600">{error}</p></div>
      </div>
    );
  }
  if (!mission) return <div className="neu-surface h-full grid place-items-center text-[#8792a6] text-[13px]">Loading…</div>;

  const st = STATUS[mission.status] || STATUS.pending;

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide p-6 sm:p-7">
      <div className="max-w-[1400px] mx-auto w-full flex flex-col">
        <button onClick={onBack} className="neu-btn-ghost flex items-center gap-2 px-3 h-9 text-[13px] font-semibold mb-4 self-start"><ArrowLeft size={15} /> Back to Missions</button>

        {/* Header */}
        <div className="flex justify-between items-start mb-5 gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            <span className="neu-circle w-12 h-12 rounded-2xl grid place-items-center text-[#4f46e5] shrink-0"><Rocket size={22} /></span>
            <div className="min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-[22px] leading-tight font-bold tracking-[-0.3px] text-[#334155]">{mission.title || mission.prompt}</h1>
                <span className={`neu-chip px-2.5 py-1 text-[11px] font-bold ${st.tone}`}>{st.label}</span>
              </div>
              <p className="text-[13px] text-[#64748b] mt-1 line-clamp-2 max-w-2xl">{mission.prompt}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <ProgressRing pct={pct} />
            {isRunning && (
              <button onClick={doStop} className="neu-btn-danger flex items-center gap-1.5 px-3.5 h-10 text-[13px] font-semibold"><Square size={12} className="fill-current" /> Stop</button>
            )}
            <div className="relative" ref={actionsRef}>
              <button onClick={() => setActionsOpen((o) => !o)} className="neu-btn-ghost flex items-center gap-2 px-4 h-10 text-[13px] font-semibold">Actions <ChevronDown size={15} /></button>
              {actionsOpen && (
                <div className="absolute right-0 top-[calc(100%+6px)] w-52 neu-card py-1.5 z-30 animate-[toastIn_.15s_ease-out]">
                  <MenuItem icon={RotateCw} label="Re-run mission" onClick={reRun} />
                  <MenuItem icon={FileDown} label="Download PDF" onClick={() => { setActionsOpen(false); exportPdf(buildExportPayload()); }} />
                  <MenuItem icon={FileCode2} label="Download HTML" onClick={() => { setActionsOpen(false); exportHtml(buildExportPayload()); }} />
                  <MenuItem icon={FileJson} label="Download JSON" onClick={downloadJson} />
                  <div className="my-1 border-t border-[#e2e6ee]" />
                  <MenuItem icon={Trash2} label="Delete mission" danger onClick={() => { setActionsOpen(false); setConfirmDelete(true); }} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="neu-seg flex p-1 gap-1 mb-5 overflow-x-auto scrollbar-hide w-full">
          {TABS.map((t) => (
            <button key={t} onClick={() => setTab(t)} className={`neu-seg-item px-4 py-2 text-[12.5px] font-semibold whitespace-nowrap ${tab === t ? "neu-seg-item-active" : ""}`}>{t}</button>
          ))}
        </div>

        {/* Content */}
        <div className="pb-6">
          {tab === "Overview" && (
            <div className="flex gap-4 items-start">
              <div className="neu-card p-4 flex-1 min-w-0">
                <h3 className="text-[14px] font-bold text-[#334155] mb-3">Execution Graph</h3>
                <ExecutionGraph tasks={tasks} running={isRunning} onSelect={setSelectedTask} selectedId={selectedTask?.id} toolsUsed={toolsUsed} model={usedModel} />
              </div>
              <TaskPanel task={selectedTask} onClose={() => setSelectedTask(null)} />
            </div>
          )}

          {tab === "Tasks" && (
            <div className="space-y-2.5">
              {tasks.length === 0 ? <Empty icon={ListChecks} text="No tasks yet." /> : tasks.map((t) => {
                const s = STATUS[t.status] || STATUS.pending;
                return (
                  <div key={t.id} className="neu-card p-4">
                    <div className="flex items-center gap-3">
                      <span className={`neu-circle w-9 h-9 rounded-xl grid place-items-center ${s.tone}`}><s.Icon size={17} strokeWidth={2.2} /></span>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-[13.5px] font-semibold text-[#334155]">{t.title}</h4>
                        <p className="text-[11.5px] text-[#9aa6b8]">{t.agent_type}{t.depends_on?.length ? ` · depends on: ${t.depends_on.join(", ")}` : ""}{t.tools_needed?.length ? ` · tools: ${t.tools_needed.join(", ")}` : ""}</p>
                      </div>
                      <span className={`neu-chip px-2.5 py-1 text-[11px] font-bold ${s.tone}`}>{s.label}</span>
                    </div>
                    {t.result?.summary && <div className="mt-3 pl-12 text-[13px] text-[#64748b]"><Markdown compact>{t.result.summary}</Markdown></div>}
                    {Array.isArray(t.result?.images) && t.result.images.length > 0 && (
                      <div className="mt-3 pl-12 grid gap-2">
                        {t.result.images.map((img, k) => (
                          <a key={k} href={`${missionApi.base}${img.url}`} target="_blank" rel="noreferrer" className="block neu-inset rounded-xl p-2 w-fit">
                            <img src={`${missionApi.base}${img.url}`} alt="Chart" className="max-w-[480px] w-full rounded-lg bg-white" loading="lazy" />
                          </a>
                        ))}
                      </div>
                    )}
                    {Array.isArray(t.result?.artifacts) && t.result.artifacts.length > 0 && (
                      <div className="mt-3 pl-12 grid gap-3">
                        {t.result.artifacts.map((a, k) => (
                          <ArtifactCard key={(a.url || a.filename || a.type) + k} artifact={a} />
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {tab === "Agents" && (() => {
            const by = new Map();
            for (const t of tasks) { const k = t.agent_id || t.agent_type || "general"; if (!by.has(k)) by.set(k, { name: t.agent_name || t.agent_type, type: t.agent_type || "general", tasks: [] }); by.get(k).tasks.push(t); }
            const arr = [...by.values()];
            const totalDone = tasks.filter((t) => t.status === "completed").length;
            return arr.length === 0 ? <Empty icon={Users} text="No agents ran yet." /> : (
              <div>
                {/* summary strip */}
                <div className="flex gap-3 mb-4">
                  <StatTile label="Agents" value={arr.length} tone="text-[#4f46e5]" />
                  <StatTile label="Tasks" value={tasks.length} tone="text-[#2563eb]" />
                  <StatTile label="Completed" value={`${totalDone}/${tasks.length}`} tone="text-emerald-600" />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                  {arr.map((a, i) => {
                    const m = agentMeta(a.type);
                    const ok = a.tasks.filter((t) => t.status === "completed").length;
                    const prog = a.tasks.length ? Math.round((100 * a.tasks.filter((t) => ["completed", "failed", "stopped"].includes(t.status)).length) / a.tasks.length) : 0;
                    const usedTools = [...new Set(a.tasks.flatMap((t) => t.tools_needed || []))].filter((t) => toolsUsed.length === 0 || toolsUsed.includes(t));
                    const allDone = a.tasks.every((t) => ["completed", "failed", "stopped"].includes(t.status));
                    const running = a.tasks.some((t) => t.status === "running");
                    return (
                      <div key={i} className="neu-card overflow-hidden transition-all hover:-translate-y-0.5">
                        {/* tinted header band */}
                        <div className="flex items-center gap-3 px-4 py-3.5" style={{ background: `linear-gradient(90deg, ${m.edge}14, transparent)` }}>
                          <span className={`neu-circle w-11 h-11 rounded-2xl grid place-items-center shrink-0 ${m.tile}`}><m.Icon size={20} strokeWidth={2} /></span>
                          <div className="min-w-0 flex-1">
                            <h4 className="text-[14px] font-bold text-[#334155] truncate capitalize">{a.name}</h4>
                            <p className="text-[11px] text-[#94a3b8] truncate">{m.desc}</p>
                          </div>
                          {/* progress ring */}
                          <div className="relative w-12 h-12 shrink-0 grid place-items-center">
                            <svg className="w-full h-full -rotate-90">
                              <circle cx="24" cy="24" r="19" stroke="#d9deea" strokeWidth="4" fill="none" />
                              <circle cx="24" cy="24" r="19" stroke={m.edge} strokeWidth="4" fill="none" strokeDasharray={2 * Math.PI * 19} strokeDashoffset={2 * Math.PI * 19 * (1 - prog / 100)} strokeLinecap="round" />
                            </svg>
                            <span className="absolute text-[10px] font-bold text-[#334155]">{prog}%</span>
                          </div>
                        </div>
                        {/* body */}
                        <div className="px-4 pb-4 pt-3">
                          <div className="flex items-center justify-between mb-3">
                            <span className={`neu-chip inline-flex items-center gap-1.5 px-2.5 py-1 text-[10.5px] font-bold ${allDone ? "text-emerald-600" : running ? "text-blue-600" : "text-[#8792a6]"}`}>
                              <span className="w-1.5 h-1.5 rounded-full" style={{ background: allDone ? "#16a34a" : running ? "#2563eb" : "#94a3b8" }} />
                              {allDone ? "Completed" : running ? "Running" : "Queued"}
                            </span>
                            <span className="text-[11px] font-semibold text-[#64748b]">{ok}/{a.tasks.length} tasks</span>
                          </div>
                          <p className="text-[9px] font-bold uppercase tracking-wide text-[#b4bdcc] mb-1.5">Tools used</p>
                          <div className="flex flex-wrap gap-1.5">
                            {usedTools.length > 0 ? usedTools.map((t) => {
                              const TI = toolIcon(t);
                              return <span key={t} className="neu-chip inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[10.5px] font-medium text-[#475569]"><TI size={12} className="text-[#64748b]" /> {toolLabel(t)}</span>;
                            }) : <span className="neu-chip inline-flex items-center gap-1.5 px-2.5 py-1.5 text-[10.5px] text-[#9aa6b8] italic"><Wrench size={11} /> No tools used</span>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {tab === "Tools" && (
            tools === null ? <Empty icon={Wrench} text="Loading…" /> :
            tools.length === 0 ? <Empty icon={Wrench} text="No tools were called in this mission." /> : (
              <div>
                <div className="flex gap-3 mb-4">
                  <StatTile label="Tools used" value={tools.length} tone="text-[#2563eb]" />
                  <StatTile label="Total calls" value={tools.reduce((s, t) => s + t.calls, 0)} tone="text-[#4f46e5]" />
                  <StatTile label="Avg success" value={`${Math.round(tools.reduce((s, t) => s + t.success_rate, 0) / tools.length)}%`} tone="text-emerald-600" />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
                  {tools.map((t) => {
                    const TI = toolIcon(t.tool);
                    return (
                      <div key={t.tool} className="neu-card overflow-hidden transition-all hover:-translate-y-0.5">
                        <div className="h-1" style={{ background: t.success_rate === 100 ? "#22c55e" : "#f59e0b" }} />
                        <div className="p-4">
                          <div className="flex items-center gap-3 mb-3">
                            <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center shrink-0 text-[#2563eb]"><TI size={20} strokeWidth={2} /></span>
                            <div className="flex-1 min-w-0">
                              <h4 className="text-[14px] font-bold text-[#334155]">{toolLabel(t.tool)}</h4>
                              <p className="text-[11px] text-[#94a3b8]">{t.calls} call{t.calls !== 1 ? "s" : ""} this mission</p>
                            </div>
                            <span className={`neu-chip px-2.5 py-1 text-[11px] font-bold ${t.success_rate === 100 ? "text-emerald-600" : "text-amber-600"}`}>{t.success_rate}%</span>
                          </div>
                          <div className="grid grid-cols-2 gap-2.5">
                            <div className="neu-inset px-3 py-2.5">
                              <p className="text-[9.5px] font-bold uppercase tracking-wide text-[#b4bdcc]">Avg latency</p>
                              <p className="text-[15px] font-bold text-[#334155]">{t.avg_latency_ms}<span className="text-[10px] font-semibold text-[#9aa6b8] ml-0.5">ms</span></p>
                            </div>
                            <div className="neu-inset px-3 py-2.5">
                              <p className="text-[9.5px] font-bold uppercase tracking-wide text-[#b4bdcc]">Successes</p>
                              <p className="text-[15px] font-bold text-[#334155]">{t.successes}<span className="text-[10px] font-semibold text-[#9aa6b8] ml-0.5">/{t.calls}</span></p>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )
          )}

          {tab === "Evidence" && (
            evidence === null ? <Empty icon={Globe} text="Loading…" /> :
            evidence.length === 0 ? <Empty icon={Globe} text="No evidence gathered — agents didn't call external tools." /> : (
              <div className="space-y-2.5">
                {evidence.map((e, i) => (
                  <div key={i} className="neu-card p-4">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#4f46e5]"><Globe size={13} /></span>
                      <span className="text-[12.5px] font-semibold text-[#334155]">{toolLabel(e.tool)}</span>
                      <span className={`neu-chip px-2 py-0.5 text-[10px] font-bold ${e.success ? "text-emerald-600" : "text-rose-600"}`}>{e.success ? "ok" : "failed"}</span>
                    </div>
                    {e.input?.query && <p className="text-[12px] text-[#64748b] mb-1">Query: <span className="font-medium">{e.input.query}</span></p>}
                    {/* Chart images produced by code_interpreter */}
                    {Array.isArray(e.output?.images) && e.output.images.length > 0 && (
                      <div className="grid gap-2 mb-2">
                        {e.output.images.map((img, k) => (
                          <a key={k} href={`${missionApi.base}${img.url}`} target="_blank" rel="noreferrer"
                            className="block neu-inset rounded-xl p-2">
                            <img src={`${missionApi.base}${img.url}`} alt="Chart"
                              className="w-full max-w-[520px] rounded-lg bg-white" loading="lazy" />
                          </a>
                        ))}
                      </div>
                    )}
                    <pre className="neu-inset p-2.5 text-[11.5px] text-[#64748b] whitespace-pre-wrap max-h-40 overflow-auto om-scroll">{JSON.stringify(e.output, null, 2).slice(0, 1200)}</pre>
                  </div>
                ))}
              </div>
            )
          )}

          {tab === "Results" && (() => {
            const withResults = tasks.filter((t) => t.result?.data || t.result?.summary || t.result?.error);
            const charts = (evidence || []).flatMap((e) => (Array.isArray(e.output?.images) ? e.output.images : []));
            const artifacts = tasks.flatMap((t) => (Array.isArray(t.result?.artifacts) ? t.result.artifacts : []));
            return withResults.length === 0 && charts.length === 0 && artifacts.length === 0 ? <Empty icon={FileText} text="No results yet." /> : (
              <div className="space-y-3">
                <div className="flex justify-end gap-2">
                  <button onClick={() => exportPdf(buildExportPayload())} className="neu-btn-ghost flex items-center gap-1.5 px-3 h-9 text-[12px] font-semibold"><FileDown size={14} /> PDF</button>
                  <button onClick={() => exportHtml(buildExportPayload())} className="neu-btn-ghost flex items-center gap-1.5 px-3 h-9 text-[12px] font-semibold"><FileCode2 size={14} /> HTML</button>
                  <button onClick={downloadJson} className="neu-btn-ghost flex items-center gap-1.5 px-3 h-9 text-[12px] font-semibold"><FileJson size={14} /> JSON</button>
                </div>
                {/* Generated charts */}
                {charts.length > 0 && (
                  <div className="neu-card p-5">
                    <h4 className="text-[14px] font-semibold text-[#334155] mb-3">Charts</h4>
                    <div className="grid gap-3">
                      {charts.map((img, k) => (
                        <a key={k} href={`${missionApi.base}${img.url}`} target="_blank" rel="noreferrer" className="block neu-inset rounded-xl p-2">
                          <img src={`${missionApi.base}${img.url}`} alt="Chart" className="w-full max-w-[560px] rounded-lg bg-white" loading="lazy" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
                {/* Typed multi-type artifacts */}
                {artifacts.length > 0 && (
                  <div className="neu-card p-5">
                    <h4 className="text-[14px] font-semibold text-[#334155] mb-3">Artifacts</h4>
                    <div className="grid gap-3">
                      {artifacts.map((a, k) => (
                        <ArtifactCard key={(a.url || a.filename || a.type) + k} artifact={a} />
                      ))}
                    </div>
                  </div>
                )}
                {withResults.map((t) => (
                  <div key={t.id} className="neu-card p-5">
                    <h4 className="text-[14px] font-semibold text-[#334155] mb-2">{t.title}</h4>
                    <Markdown>{t.result?.data || t.result?.summary || t.result?.error}</Markdown>
                  </div>
                ))}
              </div>
            );
          })()}

          {tab === "Trace" && (
            trace === null ? <Empty icon={Boxes} text="Loading…" /> :
            trace.steps.length === 0 ? <Empty icon={Boxes} text="No trace steps recorded." /> : (
              <div className="space-y-2.5">
                <div className="flex gap-3">
                  <div className="neu-raised px-4 py-2.5 flex-1"><p className="text-[11px] text-[#9aa6b8]">Total tokens</p><p className="text-[16px] font-bold text-[#334155]">{trace.total_tokens.toLocaleString()}</p></div>
                  <div className="neu-raised px-4 py-2.5 flex-1"><p className="text-[11px] text-[#9aa6b8]">Total cost</p><p className="text-[16px] font-bold text-[#334155]">${trace.total_cost_usd.toFixed(4)}</p></div>
                  <div className="neu-raised px-4 py-2.5 flex-1"><p className="text-[11px] text-[#9aa6b8]">Steps</p><p className="text-[16px] font-bold text-[#334155]">{trace.steps.length}</p></div>
                </div>
                {trace.steps.map((s, i) => (
                  <div key={i} className="neu-card p-3.5 flex items-center gap-3">
                    <span className={`neu-circle w-8 h-8 rounded-lg grid place-items-center ${s.success ? "text-[#4f46e5]" : "text-rose-500"}`}>
                      {s.type === "tool" ? <Wrench size={14} /> : <Boxes size={14} />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12.5px] font-semibold text-[#334155]">{s.type === "tool" ? toolLabel(s.tool_name) : `LLM · ${s.model || s.provider || "call"}`}</p>
                      <p className="text-[11px] text-[#9aa6b8]">{s.type === "llm" ? `${(s.input_tokens || 0) + (s.output_tokens || 0)} tokens · ` : ""}{s.latency_ms ?? 0}ms{s.cost_usd ? ` · $${s.cost_usd.toFixed(5)}` : ""}</p>
                    </div>
                    {!s.success && <span className="neu-chip px-2 py-0.5 text-[10px] font-bold text-rose-600">error</span>}
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>

      <Modal open={confirmDelete} onClose={() => setConfirmDelete(false)} title="Delete mission?" subtitle="This permanently removes the mission and its tasks." icon={Trash2}
             footer={<>
               <button onClick={() => setConfirmDelete(false)} className="neu-btn-ghost px-4 h-10 text-[13px] font-semibold">Cancel</button>
               <button onClick={() => { setConfirmDelete(false); doDelete(); }} className="neu-btn-danger-solid px-4 h-10 text-[13px] font-semibold">Delete</button>
             </>}>
        <p className="text-[13.5px]">"{mission.title || mission.prompt}" will be deleted. This cannot be undone.</p>
      </Modal>
    </div>
  );
};

function TaskPanel({ task, onClose }) {
  if (!task) {
    return (
      <div className="neu-card w-[320px] shrink-0 p-6 hidden lg:flex flex-col items-center justify-center text-center min-h-[300px]">
        <span className="neu-circle w-12 h-12 rounded-2xl grid place-items-center text-[#b4bdcc] mb-3"><ListChecks size={22} /></span>
        <p className="text-[13px] font-semibold text-[#334155] mb-1">Task Details</p>
        <p className="text-[12px] text-[#8792a6]">Click a task node in the graph to see its details.</p>
      </div>
    );
  }
  const s = STATUS[task.status] || STATUS.pending;
  const output = task.result?.data || task.result?.summary || task.result?.error;
  return (
    <div className="neu-card w-[320px] shrink-0 p-5 flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <h2 className="text-[15px] font-bold text-[#334155]">Task Details</h2>
        <button onClick={onClose} className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-[#8792a6] hover:text-[#334155]"><X size={14} /></button>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center ${s.tone}`}><s.Icon size={19} strokeWidth={2.2} /></span>
        <div className="min-w-0">
          <h4 className="text-[13.5px] font-bold text-[#334155] leading-tight">{task.title}</h4>
          <p className="text-[11.5px] text-[#9aa6b8] capitalize">{task.agent_name || task.agent_type} · {s.label}</p>
        </div>
      </div>

      <Section title="Type">
        <span className="neu-chip inline-block px-2.5 py-1 text-[11px] font-bold text-[#4f46e5] capitalize">{task.agent_type}</span>
      </Section>

      {task.depends_on?.length > 0 && (
        <Section title="Depends on">
          <div className="flex flex-wrap gap-1.5">{task.depends_on.map((d) => <span key={d} className="neu-chip px-2 py-0.5 text-[10.5px] font-medium text-[#64748b]">{d}</span>)}</div>
        </Section>
      )}

      <Section title="Tools">
        {task.tools_needed?.length ? (
          <div className="flex flex-wrap gap-1.5">{task.tools_needed.map((t) => <span key={t} className="neu-chip flex items-center gap-1 px-2 py-0.5 text-[10.5px] font-medium text-[#64748b]"><Wrench size={10} /> {t.replace(/_/g, " ")}</span>)}</div>
        ) : <p className="text-[12px] text-[#9aa6b8]">No tools required.</p>}
      </Section>

      <Section title="Output">
        {output ? <div className="neu-inset p-3 max-h-56 overflow-auto om-scroll"><Markdown compact>{output}</Markdown></div>
          : <p className="text-[12px] text-[#9aa6b8] italic">No output produced yet.</p>}
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-4">
      <h5 className="text-[11px] font-bold uppercase tracking-wide text-[#8792a6] mb-1.5">{title}</h5>
      {children}
    </div>
  );
}

function MenuItem({ icon: Icon, label, onClick, danger }) {
  return (
    <button onClick={onClick} className={`neu-nav w-full flex items-center gap-2.5 px-3 py-2 text-left text-[13px] font-medium ${danger ? "text-[#e11d48]" : "text-[#4a5568]"}`}>
      <Icon size={15} className={danger ? "text-[#e11d48]" : "text-[#8792a6]"} /> {label}
    </button>
  );
}
