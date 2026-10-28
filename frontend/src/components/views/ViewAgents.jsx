// Agents · Registry (ViewAgents.jsx)
// READ-ONLY directory of every agent in the system. Agents are created
// dynamically by departments/heads during missions — there is no manual
// create/edit/test/delete here. 100% real data from agentApi.list(), with
// department names resolved via departmentApi.list().
import { useEffect, useMemo, useState } from "react";
import {
  Users, Search, Loader2, Bot, Activity, CheckCircle2, Wrench, Clock,
  LayoutGrid, List as ListIcon, RefreshCw, AlertCircle, Crown, Sparkles, Repeat, Shield,
} from "lucide-react";
import { agentApi } from "../../agentApi.js";
import { departmentApi } from "../../departmentApi.js";
import { useToast } from "../ui/Toast.jsx";
import { NeuChip } from "./settings/SettingsShared.jsx";

const TYPE_TINT = {
  research: "text-emerald-600", marketing: "text-pink-600", finance: "text-violet-600",
  operations: "text-orange-600", analysis: "text-violet-600", writing: "text-indigo-600",
  hr: "text-blue-600", general: "text-slate-500",
};

// origin → human role badge. Master = the top-level orchestrator.
const ORIGIN_META = {
  head: { label: "Head", Icon: Crown, tone: "text-amber-600" },
  specialist: { label: "Specialist", Icon: Sparkles, tone: "text-[#4f46e5]" },
  reusable: { label: "Reusable", Icon: Repeat, tone: "text-emerald-600" },
  master: { label: "Master", Icon: Shield, tone: "text-rose-600" },
};
const originMeta = (origin) =>
  ORIGIN_META[origin] || { label: origin ? origin.replace(/\b\w/, (c) => c.toUpperCase()) : "Agent", Icon: Bot, tone: "text-slate-500" };

const relTime = (iso) => {
  if (!iso) return "never";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};
const pct = (v) => (v != null ? `${Math.round(v * 100)}%` : "—");

const StatTile = ({ icon: Icon, label, value, tint = "text-[#4f46e5]" }) => (
  <div className="neu-raised flex items-center gap-3 px-4 py-3.5 rounded-2xl">
    <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center ${tint}`}><Icon size={19} /></span>
    <div><div className="text-[12px] text-[#8792a6] font-medium">{label}</div>
      <div className="text-[20px] font-bold text-[#334155] leading-tight">{value}</div></div>
  </div>
);

const OriginBadge = ({ origin }) => {
  const m = originMeta(origin);
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${m.tone}`}>
      <m.Icon size={12} /> {m.label}
    </span>
  );
};

const ToolChips = ({ tools = [], max = 3 }) => {
  if (!tools.length) return <span className="text-[11.5px] text-[#9aa6b8]">no tools</span>;
  const shown = tools.slice(0, max);
  const rest = tools.length - shown.length;
  return (
    <span className="inline-flex items-center gap-1 flex-wrap">
      {shown.map((t) => <NeuChip key={t}>{t}</NeuChip>)}
      {rest > 0 && <span className="text-[11px] text-[#9aa6b8]">+{rest}</span>}
    </span>
  );
};

export function ViewAgents() {
  const toast = useToast();
  const [agents, setAgents] = useState([]);
  const [deptMap, setDeptMap] = useState({}); // id -> name
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [originFilter, setOriginFilter] = useState("");
  const [view, setView] = useState("grid");

  const load = () => {
    setLoading(true); setError("");
    Promise.all([
      agentApi.list(),
      departmentApi.list().catch(() => ({ departments: [] })),
    ])
      .then(([a, d]) => {
        setAgents(a.agents || []);
        const map = {};
        (d.departments || []).forEach((dep) => { map[dep.id] = dep.name; });
        setDeptMap(map);
      })
      .catch((e) => { setError(e.message); toast.error(e.message); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const origins = useMemo(() => [...new Set(agents.map((a) => a.origin).filter(Boolean))].sort(), [agents]);

  const filtered = useMemo(() => agents.filter((a) => {
    if (q && !(`${a.name} ${a.agent_type} ${a.role_title || ""} ${a.purpose || ""}`.toLowerCase().includes(q.toLowerCase()))) return false;
    if (originFilter && (a.origin || "") !== originFilter) return false;
    return true;
  }), [agents, q, originFilter]);

  const total = agents.length;
  const heads = agents.filter((a) => a.origin === "head").length;
  const specialists = agents.filter((a) => a.origin === "specialist").length;
  const reusable = agents.filter((a) => a.origin === "reusable").length;

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-8">
      <div className="max-w-[1120px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h1 className="text-[23px] font-semibold text-[#334155]">Agents</h1>
            <p className="text-[14px] text-[#8792a6] mt-1">
              A live registry of every agent. Agents are created dynamically by departments and heads during missions — this is a read-only directory.
            </p>
          </div>
          <button onClick={load} title="Refresh" className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#5b6678] shrink-0">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatTile icon={Users} label="Total Agents" value={total} />
          <StatTile icon={Crown} label="Heads" value={heads} tint="text-amber-600" />
          <StatTile icon={Sparkles} label="Specialists" value={specialists} tint="text-[#4f46e5]" />
          <StatTile icon={Repeat} label="Reusable" value={reusable} tint="text-emerald-600" />
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5 mb-5">
          <div className="neu-inset flex items-center gap-2 px-3.5 h-11 rounded-xl flex-1 min-w-[220px]">
            <Search size={17} className="text-[#9aa6b8]" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search agents by name…"
              className="bg-transparent outline-none text-[14px] text-[#334155] w-full placeholder:text-[#9aa6b8]" />
          </div>
          <select value={originFilter} onChange={(e) => setOriginFilter(e.target.value)}
            className="neu-input neu-select h-11 px-3.5 text-[13.5px] text-[#334155] rounded-xl">
            <option value="">All Origins</option>
            {origins.map((o) => <option key={o} value={o}>{originMeta(o).label}</option>)}
          </select>
          <div className="neu-inset flex items-center p-1 rounded-xl">
            <button onClick={() => setView("grid")} title="Grid"
              className={`w-9 h-9 rounded-lg grid place-items-center ${view === "grid" ? "neu-raised text-[#4f46e5]" : "text-[#8792a6]"}`}><LayoutGrid size={16} /></button>
            <button onClick={() => setView("table")} title="Table"
              className={`w-9 h-9 rounded-lg grid place-items-center ${view === "table" ? "neu-raised text-[#4f46e5]" : "text-[#8792a6]"}`}><ListIcon size={16} /></button>
          </div>
        </div>

        {/* Body */}
        {loading ? (
          <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : error ? (
          <div className="neu-inset rounded-2xl py-14 text-center">
            <AlertCircle className="mx-auto text-rose-500 mb-2" />
            <p className="text-[13.5px] text-[#5b6678]">{error}</p>
            <button onClick={load} className="neu-btn-ghost mt-3 h-9 px-4 text-[13px] font-semibold">Retry</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">
            {agents.length === 0
              ? "No agents yet. Agents appear here once a mission spins up department heads and specialists."
              : "No agents match your filters."}
          </div>
        ) : view === "grid" ? (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((a) => {
              const s = a.stats || {};
              const deptName = a.department_id ? (deptMap[a.department_id] || "—") : "—";
              return (
                <div key={a.id} className="neu-card rounded-2xl p-4 flex flex-col">
                  <div className="flex items-center gap-3 mb-3">
                    <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center ${TYPE_TINT[a.agent_type] || "text-slate-500"}`}><Bot size={20} /></span>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-[14.5px] font-semibold text-[#334155] truncate">{a.name}</h3>
                      <div className="flex items-center gap-2 mt-0.5">
                        <OriginBadge origin={a.origin} />
                        <NeuChip>{a.agent_type}</NeuChip>
                      </div>
                    </div>
                  </div>
                  {a.role_title && <p className="text-[12px] text-[#5b6678] font-medium mb-1.5 truncate">{a.role_title}</p>}
                  <p className="text-[12.5px] text-[#8792a6] line-clamp-2 mb-3 min-h-[34px]">{a.purpose || "No description."}</p>
                  <div className="mb-3">
                    <ToolChips tools={a.tools} />
                  </div>
                  <div className="flex items-center gap-3 text-[11.5px] text-[#8792a6] mt-auto">
                    <span className="flex items-center gap-1" title="Department"><Users size={12} /> {deptName}</span>
                    <span className="flex items-center gap-1 ml-auto" title="Runs"><Activity size={12} /> {s.runs || 0}</span>
                    <span className="flex items-center gap-1" title="Success rate"><CheckCircle2 size={12} /> {pct(s.success_rate)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="neu-card rounded-2xl p-2 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[11.5px] uppercase tracking-wide text-[#9aa6b8]">
                  <th className="py-3 px-3">Agent</th><th className="py-3 px-3">Role</th>
                  <th className="py-3 px-3">Type</th><th className="py-3 px-3">Department</th>
                  <th className="py-3 px-3">Tools</th><th className="py-3 px-3">Runs</th>
                  <th className="py-3 px-3">Success</th><th className="py-3 px-3">Last Active</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => {
                  const s = a.stats || {};
                  const deptName = a.department_id ? (deptMap[a.department_id] || "—") : "—";
                  return (
                    <tr key={a.id} className="hover:bg-[#e9edf4] transition-colors rounded-xl">
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2.5">
                          <span className={`neu-circle w-9 h-9 rounded-lg grid place-items-center ${TYPE_TINT[a.agent_type] || "text-slate-500"}`}><Bot size={16} /></span>
                          <div className="min-w-0">
                            <span className="text-[13.5px] font-semibold text-[#334155] block truncate">{a.name}</span>
                            {a.role_title && <span className="text-[11px] text-[#9aa6b8] block truncate">{a.role_title}</span>}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3"><OriginBadge origin={a.origin} /></td>
                      <td className="py-3 px-3"><NeuChip>{a.agent_type}</NeuChip></td>
                      <td className="py-3 px-3 text-[13px] text-[#5b6678]">{deptName}</td>
                      <td className="py-3 px-3"><ToolChips tools={a.tools} max={2} /></td>
                      <td className="py-3 px-3 text-[13px] text-[#5b6678]">{s.runs || 0}</td>
                      <td className="py-3 px-3 text-[13px] text-[#5b6678]">{pct(s.success_rate)}</td>
                      <td className="py-3 px-3 text-[12.5px] text-[#8792a6]">{relTime(s.last_active)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {!loading && !error && (
          <p className="text-[12px] text-[#9aa6b8] mt-4 text-center">
            Showing {filtered.length} of {agents.length} agent{agents.length === 1 ? "" : "s"}
          </p>
        )}
      </div>
    </div>
  );
}

export default ViewAgents;
