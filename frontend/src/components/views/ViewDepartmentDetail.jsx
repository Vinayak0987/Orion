// Departments · Detail workspace (ViewDepartmentDetail.jsx)
// A rich, multi-tab workspace for a single department. Reads real data from
// departmentApi: get / activity (polled) / missions / schedules, and writes via
// update / archive / createSchedule / deleteSchedule / toggleSchedule.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft, Building2, Users, BarChart3, Database, Boxes, Crown, Sparkles,
  Loader2, RefreshCw, AlertCircle, Wrench, CheckCircle2, XCircle, Clock, Calendar,
  Plus, Trash2, Power, PowerOff, Save, Archive, ListChecks, Activity,
  Megaphone, Landmark, Settings2, FlaskConical,
} from "lucide-react";
import { departmentApi } from "../../departmentApi.js";
import { useToast } from "../ui/Toast.jsx";
import { NeuChip } from "./settings/SettingsShared.jsx";

/* ---------------- helpers ---------------- */
const TYPE_ICON = {
  marketing: { Icon: Megaphone, tint: "text-pink-600" },
  finance: { Icon: Landmark, tint: "text-emerald-600" },
  operations: { Icon: Settings2, tint: "text-orange-500" },
  sales: { Icon: BarChart3, tint: "text-blue-600" },
  hr: { Icon: Users, tint: "text-rose-500" },
  research: { Icon: FlaskConical, tint: "text-[#4f46e5]" },
};
const typeMeta = (t) => TYPE_ICON[t] || { Icon: Building2, tint: "text-[#4f46e5]" };

const STATUS_TONE = {
  active: "text-emerald-600", running: "text-sky-600", pending: "text-amber-600",
  completed: "text-emerald-600", failed: "text-rose-600", partial: "text-amber-600",
  paused: "text-amber-600", archived: "text-slate-500",
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return "—";
  return t.toLocaleString();
};
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

const roleMeta = (role) =>
  role === "head" ? { label: "Head", Icon: Crown, tone: "text-amber-600" }
    : role === "specialist" ? { label: "Specialist", Icon: Sparkles, tone: "text-[#4f46e5]" }
      : { label: "Member", Icon: Users, tone: "text-slate-500" };

const StatTile = ({ icon: Icon, label, value, tint = "text-[#4f46e5]" }) => (
  <div className="neu-raised flex items-center gap-3 px-4 py-3.5 rounded-2xl">
    <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center ${tint}`}><Icon size={19} /></span>
    <div><div className="text-[12px] text-[#8792a6] font-medium">{label}</div>
      <div className="text-[18px] font-bold text-[#334155] leading-tight truncate max-w-[160px]">{value}</div></div>
  </div>
);

const SectionTitle = ({ children }) => (
  <h3 className="text-[14px] font-bold text-[#334155] mb-3">{children}</h3>
);

const StatusBadge = ({ status }) => (
  <span className={`text-[12px] font-semibold capitalize ${STATUS_TONE[status] || "text-slate-500"}`}>● {status || "—"}</span>
);

const TABS = [
  { id: "overview", label: "Overview", Icon: Boxes },
  { id: "team", label: "Team", Icon: Users },
  { id: "activity", label: "Live Activity", Icon: Activity },
  { id: "missions", label: "Missions", Icon: ListChecks },
  { id: "knowledge", label: "Knowledge", Icon: Database },
  { id: "tools", label: "Tools", Icon: Wrench },
  { id: "schedule", label: "Schedule", Icon: Calendar },
  { id: "settings", label: "Settings", Icon: Settings2 },
];

/* =========================================================================
   Main component
   ========================================================================= */
export function ViewDepartmentDetail({ departmentId, onBack }) {
  const toast = useToast();
  const [dept, setDept] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("overview");

  const load = useCallback(() => {
    if (!departmentId) { setError("No department selected."); setLoading(false); return; }
    setLoading(true); setError("");
    departmentApi.get(departmentId)
      .then((d) => setDept(d))
      .catch((e) => { setError(e.message); toast.error(e.message); })
      .finally(() => setLoading(false));
    // eslint-disable-next-line
  }, [departmentId]);
  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="neu-surface h-full grid place-items-center text-[#9aa6b8]">
        <Loader2 className="animate-spin" />
      </div>
    );
  }
  if (error || !dept) {
    return (
      <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-8">
        <button onClick={onBack} className="neu-btn-ghost inline-flex items-center gap-2 h-9 px-3.5 text-[13px] font-semibold text-[#5b6678] mb-5">
          <ArrowLeft size={16} /> Back to Departments
        </button>
        <div className="neu-inset rounded-2xl py-14 text-center">
          <AlertCircle className="mx-auto text-rose-500 mb-2" />
          <p className="text-[13.5px] text-[#5b6678]">{error || "Department not found."}</p>
          <button onClick={load} className="neu-btn-ghost mt-3 h-9 px-4 text-[13px] font-semibold">Retry</button>
        </div>
      </div>
    );
  }

  const { Icon, tint } = typeMeta(dept.dept_type);
  const st = dept.stats || {};
  const members = dept.members || [];
  const head = dept.head || members.find((m) => m.role === "head");
  const headLabel = st.head || head?.agent_name || "—";

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-8">
      <div className="max-w-[1120px] mx-auto">
        {/* Header */}
        <button onClick={onBack} className="neu-btn-ghost inline-flex items-center gap-2 h-9 px-3.5 text-[13px] font-semibold text-[#5b6678] mb-5">
          <ArrowLeft size={16} /> Back to Departments
        </button>
        <div className="flex items-start gap-4 mb-6">
          <span className={`neu-circle w-14 h-14 rounded-2xl grid place-items-center ${tint} shrink-0`}><Icon size={26} /></span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-[23px] font-semibold text-[#334155]">{dept.name}</h1>
              <NeuChip>{dept.dept_type || "general"}</NeuChip>
              <StatusBadge status={dept.status} />
              {dept.is_default && <span className="neu-chip text-[10px] font-bold text-[#4f46e5] px-2 py-0.5">Default</span>}
            </div>
            <p className="text-[14px] text-[#8792a6] mt-1.5 max-w-2xl">{dept.purpose || dept.description || "No purpose set."}</p>
          </div>
          <button onClick={load} title="Refresh" className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#5b6678] shrink-0">
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Stat tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatTile icon={Users} label="Members" value={st.members ?? members.length} />
          <StatTile icon={BarChart3} label="Active Missions" value={st.active_missions ?? 0} tint="text-sky-600" />
          <StatTile icon={Database} label="Knowledge Docs" value={st.knowledge_documents ?? 0} tint="text-violet-600" />
          <StatTile icon={Crown} label="Head" value={headLabel} tint="text-amber-600" />
        </div>

        {/* Tab bar */}
        <div className="neu-inset rounded-2xl p-1.5 mb-6 flex items-center gap-1 overflow-x-auto scrollbar-hide">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 h-9 px-3.5 rounded-xl text-[13px] font-semibold whitespace-nowrap ${
                tab === t.id ? "neu-raised text-[#4f46e5]" : "text-[#8792a6] hover:text-[#5b6678]"}`}>
              <t.Icon size={15} /> {t.label}
            </button>
          ))}
        </div>

        {/* Tab body */}
        {tab === "overview" && <OverviewTab dept={dept} members={members} head={head} />}
        {tab === "team" && <TeamTab members={members} />}
        {tab === "activity" && <ActivityTab departmentId={departmentId} />}
        {tab === "missions" && <MissionsTab departmentId={departmentId} />}
        {tab === "knowledge" && <KnowledgeTab />}
        {tab === "tools" && <ToolsTab members={members} />}
        {tab === "schedule" && <ScheduleTab departmentId={departmentId} />}
        {tab === "settings" && <SettingsTab dept={dept} onSaved={load} onArchived={onBack} />}
      </div>
    </div>
  );
}

/* ---------------- Org tree (shared) ---------------- */
const OrgTree = ({ members, head }) => {
  const specialists = members.filter((m) => m.role !== "head");
  const headMember = head || members.find((m) => m.role === "head");
  return (
    <div className="neu-inset rounded-2xl p-5">
      <div className="flex justify-center mb-4">
        <div className="neu-raised rounded-xl px-4 py-2.5 inline-flex items-center gap-2.5 border border-[#c7d2fe]">
          <span className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-white"><Crown size={16} /></span>
          <div>
            <p className="text-[13px] font-bold text-[#334155] leading-tight">{headMember?.agent_name || "No head assigned"}</p>
            <p className="text-[10.5px] text-[#9aa6b8]">{headMember?.agent_role_title || "Department Head"}</p>
          </div>
        </div>
      </div>
      {specialists.length === 0 ? (
        <p className="text-center text-[12.5px] text-[#8792a6]">No specialists yet — they are created dynamically as missions run.</p>
      ) : (
        <div className="flex flex-wrap justify-center gap-2.5">
          {specialists.map((m) => {
            const rm = roleMeta(m.role);
            return (
              <div key={m.agent_id} className="neu-raised rounded-xl px-3 py-2 inline-flex items-center gap-2 border border-[#e2e6ee]">
                <rm.Icon size={13} className={rm.tone} />
                <div>
                  <p className="text-[12px] font-semibold text-[#334155] leading-tight">{m.agent_name}</p>
                  <p className="text-[10px] text-[#9aa6b8]">{m.agent_type}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/* ---------------- Overview ---------------- */
const OverviewTab = ({ dept, members, head }) => {
  const responsibilities = dept.responsibilities || dept.config?.responsibilities || [];
  const instructions = dept.instructions || dept.config?.instructions || "";
  return (
    <div className="space-y-6">
      <div className="neu-card rounded-2xl p-5">
        <SectionTitle>Responsibilities</SectionTitle>
        {Array.isArray(responsibilities) && responsibilities.length > 0 ? (
          <ul className="space-y-2">
            {responsibilities.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-[13.5px] text-[#5b6678]">
                <CheckCircle2 size={15} className="text-[#4f46e5] mt-0.5 shrink-0" /> {typeof r === "string" ? r : r.title || JSON.stringify(r)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[13px] text-[#8792a6]">No responsibilities defined for this department yet.</p>
        )}
      </div>

      <div className="neu-card rounded-2xl p-5">
        <SectionTitle>Instructions</SectionTitle>
        {instructions ? (
          <p className="text-[13.5px] text-[#5b6678] whitespace-pre-wrap leading-relaxed">{instructions}</p>
        ) : (
          <p className="text-[13px] text-[#8792a6]">No standing instructions set.</p>
        )}
      </div>

      <div className="neu-card rounded-2xl p-5">
        <SectionTitle>Org Tree</SectionTitle>
        <OrgTree members={members} head={head} />
      </div>
    </div>
  );
};

/* ---------------- Team ---------------- */
const TeamTab = ({ members }) => {
  if (!members.length) {
    return (
      <div className="neu-inset rounded-2xl py-14 text-center text-[#8792a6]">
        No members yet. Agents join this department as missions create heads and specialists.
      </div>
    );
  }
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {members.map((m) => {
        const rm = roleMeta(m.role);
        const tools = m.agent_tools || [];
        return (
          <div key={m.agent_id} className="neu-card rounded-2xl p-4">
            <div className="flex items-center gap-3 mb-2.5">
              <span className="neu-circle w-11 h-11 rounded-xl grid place-items-center text-[#4f46e5]"><Boxes size={19} /></span>
              <div className="min-w-0 flex-1">
                <h3 className="text-[14.5px] font-semibold text-[#334155] truncate">{m.agent_name}</h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`inline-flex items-center gap-1 text-[11px] font-semibold ${rm.tone}`}><rm.Icon size={12} /> {rm.label}</span>
                  <NeuChip>{m.agent_type}</NeuChip>
                </div>
              </div>
            </div>
            {m.agent_role_title && <p className="text-[12px] text-[#5b6678] mb-2">{m.agent_role_title}</p>}
            {tools.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {tools.map((t) => <NeuChip key={t}>{t}</NeuChip>)}
              </div>
            ) : (
              <p className="text-[11.5px] text-[#9aa6b8]">No tools assigned.</p>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ---------------- Live Activity (polled) ---------------- */
const ActivityTab = ({ departmentId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const timer = useRef(null);

  const poll = useCallback(() => {
    departmentApi.activity(departmentId)
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [departmentId]);

  useEffect(() => {
    poll();
    timer.current = setInterval(poll, 5000);
    return () => clearInterval(timer.current);
  }, [poll]);

  const running = data?.running || [];

  if (loading) return <div className="grid place-items-center py-16 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>;

  if (!running.length) {
    return (
      <div className="neu-inset rounded-2xl py-14 text-center text-[#8792a6]">
        <Activity size={26} className="mx-auto text-[#b4bdcc] mb-2" />
        No active work right now. Running missions and their tool calls appear here live.
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-[12px] text-[#8792a6]">
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Live · refreshes every 5s
      </div>
      {running.map((r) => (
        <div key={r.mission_id} className="neu-card rounded-2xl p-5">
          <div className="flex items-center justify-between gap-3 mb-3">
            <h3 className="text-[14px] font-semibold text-[#334155] truncate">{r.title || "Untitled mission"}</h3>
            <StatusBadge status={r.status} />
          </div>
          <p className="text-[11.5px] text-[#9aa6b8] mb-3">Started {relTime(r.created_at)}</p>

          {(r.tasks || []).length > 0 && (
            <div className="mb-3">
              <p className="text-[11.5px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-2">Tasks</p>
              <div className="space-y-1.5">
                {r.tasks.map((t, i) => (
                  <div key={i} className="neu-inset rounded-xl px-3 py-2 flex items-center gap-2">
                    <StatusBadge status={t.status} />
                    <span className="text-[12.5px] text-[#5b6678] truncate">{t.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(r.recent_tools || []).length > 0 && (
            <div>
              <p className="text-[11.5px] font-semibold uppercase tracking-wide text-[#9aa6b8] mb-2">Recent tool calls</p>
              <div className="flex flex-wrap gap-2">
                {r.recent_tools.map((tool, i) => (
                  <span key={i} className="neu-inset inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[12px] text-[#5b6678]">
                    {tool.success ? <CheckCircle2 size={13} className="text-emerald-600" /> : <XCircle size={13} className="text-rose-600" />}
                    {tool.tool_name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

/* ---------------- Missions ---------------- */
const MissionsTab = ({ departmentId }) => {
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true); setError("");
    departmentApi.missions(departmentId)
      .then((d) => setMissions(d.missions || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [departmentId]);

  if (loading) return <div className="grid place-items-center py-16 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>;
  if (error) return <div className="neu-inset rounded-2xl py-14 text-center text-[#5b6678]">{error}</div>;
  if (!missions.length) {
    return <div className="neu-inset rounded-2xl py-14 text-center text-[#8792a6]">No missions have been run for this department yet.</div>;
  }
  return (
    <div className="neu-card rounded-2xl p-2 overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-[11.5px] uppercase tracking-wide text-[#9aa6b8]">
            <th className="py-3 px-3">Mission</th><th className="py-3 px-3">Mode</th>
            <th className="py-3 px-3">Status</th><th className="py-3 px-3">Created</th>
          </tr>
        </thead>
        <tbody>
          {missions.map((m) => (
            <tr key={m.id} className="hover:bg-[#e9edf4] transition-colors rounded-xl">
              <td className="py-3 px-3 text-[13.5px] font-medium text-[#334155] max-w-[420px]">
                <span className="block truncate">{m.title || m.prompt || "Untitled"}</span>
              </td>
              <td className="py-3 px-3"><NeuChip>{m.mode || "—"}</NeuChip></td>
              <td className="py-3 px-3"><StatusBadge status={m.status} /></td>
              <td className="py-3 px-3 text-[12.5px] text-[#8792a6]">{relTime(m.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/* ---------------- Knowledge (honest placeholder) ---------------- */
const KnowledgeTab = () => (
  <div className="neu-inset rounded-2xl py-14 px-6 text-center text-[#8792a6]">
    <Database size={28} className="mx-auto text-[#b4bdcc] mb-3" />
    <p className="text-[14px] text-[#5b6678] font-medium mb-1">Department knowledge</p>
    <p className="text-[13px] max-w-md mx-auto">
      Documents scoped to this department will appear here. For now, upload and manage sources from the
      <span className="font-semibold text-[#4f46e5]"> Knowledge</span> section in the sidebar.
    </p>
  </div>
);

/* ---------------- Tools (aggregated from members) ---------------- */
const ToolsTab = ({ members }) => {
  const tools = useMemo(() => {
    const set = new Set();
    members.forEach((m) => (m.agent_tools || []).forEach((t) => set.add(t)));
    return [...set].sort();
  }, [members]);

  if (!tools.length) {
    return <div className="neu-inset rounded-2xl py-14 text-center text-[#8792a6]">No tools in use across this department's members yet.</div>;
  }
  return (
    <div className="neu-card rounded-2xl p-5">
      <SectionTitle>Tools used across the department ({tools.length})</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {tools.map((t) => (
          <span key={t} className="neu-inset inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12.5px] text-[#5b6678]">
            <Wrench size={13} className="text-[#4f46e5]" /> {t}
          </span>
        ))}
      </div>
    </div>
  );
};

/* ---------------- Schedule (CRON) ---------------- */
const ScheduleTab = ({ departmentId }) => {
  const toast = useToast();
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // form
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("planning");
  const [cadence, setCadence] = useState("daily");
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [firstRunIn, setFirstRunIn] = useState(0);

  const load = useCallback(() => {
    setLoading(true);
    departmentApi.schedules(departmentId)
      .then((d) => setSchedules(d.schedules || []))
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line
  }, [departmentId]);
  useEffect(() => { load(); }, [load]);

  const create = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) { toast.error("Enter a prompt for the schedule."); return; }
    setSaving(true);
    try {
      await departmentApi.createSchedule(departmentId, {
        prompt: prompt.trim(),
        mode,
        cadence,
        interval_minutes: cadence === "interval" ? Number(intervalMinutes) : undefined,
        first_run_in_minutes: Number(firstRunIn) || 0,
      });
      toast.success("Schedule created.");
      setPrompt("");
      load();
    } catch (err) {
      toast.error(err.message || "Could not create schedule.");
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (s) => {
    try {
      await departmentApi.toggleSchedule(s.id, !s.enabled);
      toast.success(s.enabled ? "Schedule paused." : "Schedule enabled.");
      load();
    } catch (err) { toast.error(err.message); }
  };
  const remove = async (s) => {
    if (!window.confirm("Delete this schedule? This cannot be undone.")) return;
    try {
      await departmentApi.deleteSchedule(s.id);
      toast.success("Schedule deleted.");
      load();
    } catch (err) { toast.error(err.message); }
  };

  const cadenceLabel = (s) =>
    s.cadence === "interval" ? `Every ${s.interval_minutes || "?"} min` : (s.cadence || "—");

  return (
    <div className="space-y-6">
      {/* New schedule form */}
      <div className="neu-card rounded-2xl p-5">
        <SectionTitle>New Schedule</SectionTitle>
        <p className="text-[12.5px] text-[#8792a6] mb-4 flex items-center gap-1.5">
          <Clock size={13} className="text-[#4f46e5]" /> Automatically run a recurring mission for this department (cron).
        </p>
        <form onSubmit={create} className="space-y-3">
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3}
            placeholder="What should this department do on schedule? e.g. 'Summarize new competitor activity and post to the brief.'"
            className="neu-inset w-full rounded-xl px-3.5 py-2.5 text-[13.5px] text-[#334155] placeholder:text-[#9aa6b8] outline-none resize-none" />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="text-[11.5px] font-semibold text-[#8792a6] block mb-1">Mode</label>
              <select value={mode} onChange={(e) => setMode(e.target.value)}
                className="neu-input neu-select w-full h-10 px-3 text-[13px] text-[#334155] rounded-xl">
                <option value="planning">Planning</option>
                <option value="action">Action</option>
              </select>
            </div>
            <div>
              <label className="text-[11.5px] font-semibold text-[#8792a6] block mb-1">Cadence</label>
              <select value={cadence} onChange={(e) => setCadence(e.target.value)}
                className="neu-input neu-select w-full h-10 px-3 text-[13px] text-[#334155] rounded-xl">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="interval">Interval</option>
              </select>
            </div>
            {cadence === "interval" && (
              <div>
                <label className="text-[11.5px] font-semibold text-[#8792a6] block mb-1">Every (min)</label>
                <input type="number" min={1} value={intervalMinutes} onChange={(e) => setIntervalMinutes(e.target.value)}
                  className="neu-inset w-full h-10 px-3 text-[13px] text-[#334155] rounded-xl outline-none" />
              </div>
            )}
            <div>
              <label className="text-[11.5px] font-semibold text-[#8792a6] block mb-1">First run in (min)</label>
              <input type="number" min={0} value={firstRunIn} onChange={(e) => setFirstRunIn(e.target.value)}
                className="neu-inset w-full h-10 px-3 text-[13px] text-[#334155] rounded-xl outline-none" />
            </div>
          </div>
          <button type="submit" disabled={saving}
            className="neu-btn-primary inline-flex items-center gap-2 h-10 px-4 text-[13.5px] font-semibold disabled:opacity-60">
            {saving ? <Loader2 size={15} className="animate-spin" /> : <Plus size={16} />} Create Schedule
          </button>
        </form>
      </div>

      {/* Existing schedules */}
      <div>
        <SectionTitle>Active Schedules</SectionTitle>
        {loading ? (
          <div className="grid place-items-center py-10 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : !schedules.length ? (
          <div className="neu-inset rounded-2xl py-12 text-center text-[#8792a6]">No schedules yet. Create one above to automate this department.</div>
        ) : (
          <div className="space-y-3">
            {schedules.map((s) => (
              <div key={s.id} className="neu-card rounded-2xl p-4">
                <div className="flex items-start gap-3">
                  <span className={`neu-circle w-10 h-10 rounded-xl grid place-items-center shrink-0 ${s.enabled ? "text-emerald-600" : "text-[#9aa6b8]"}`}>
                    <Calendar size={18} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] text-[#334155] leading-snug">{s.prompt}</p>
                    <div className="flex items-center gap-3 flex-wrap mt-2 text-[11.5px] text-[#8792a6]">
                      <span className="inline-flex items-center gap-1"><Clock size={12} /> {cadenceLabel(s)}</span>
                      <span>Next: {fmtTime(s.next_run)}</span>
                      {s.last_run && <span>Last: {relTime(s.last_run)}</span>}
                      <span className={`font-semibold ${s.enabled ? "text-emerald-600" : "text-[#9aa6b8]"}`}>
                        {s.enabled ? "Enabled" : "Paused"}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button onClick={() => toggle(s)} title={s.enabled ? "Pause" : "Enable"}
                      className={`neu-circle w-9 h-9 rounded-lg grid place-items-center ${s.enabled ? "text-amber-600" : "text-emerald-600"}`}>
                      {s.enabled ? <PowerOff size={15} /> : <Power size={15} />}
                    </button>
                    <button onClick={() => remove(s)} title="Delete"
                      className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-rose-500">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/* ---------------- Settings ---------------- */
const SettingsTab = ({ dept, onSaved, onArchived }) => {
  const toast = useToast();
  const [name, setName] = useState(dept.name || "");
  const [purpose, setPurpose] = useState(dept.purpose || "");
  const [description, setDescription] = useState(dept.description || "");
  const [instructions, setInstructions] = useState(dept.instructions || dept.config?.instructions || "");
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const save = async () => {
    if (!name.trim()) { toast.error("Name cannot be empty."); return; }
    setSaving(true);
    try {
      await departmentApi.update(dept.id, {
        name: name.trim(),
        purpose,
        description,
        instructions,
      });
      toast.success("Department updated.");
      onSaved?.();
    } catch (err) {
      toast.error(err.message || "Could not update department.");
    } finally {
      setSaving(false);
    }
  };

  const archive = async () => {
    if (dept.is_default) return;
    if (!window.confirm(`Archive "${dept.name}"? Its agents and history are preserved but it will no longer be active.`)) return;
    setArchiving(true);
    try {
      await departmentApi.archive(dept.id);
      toast.success("Department archived.");
      onArchived?.();
    } catch (err) {
      toast.error(err.message || "Could not archive department.");
    } finally {
      setArchiving(false);
    }
  };

  const Field = ({ label, children }) => (
    <div>
      <label className="text-[12px] font-semibold text-[#8792a6] block mb-1.5">{label}</label>
      {children}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="neu-card rounded-2xl p-5 space-y-4">
        <SectionTitle>Edit Department</SectionTitle>
        <Field label="Name">
          <input value={name} onChange={(e) => setName(e.target.value)}
            className="neu-inset w-full h-10 px-3.5 text-[13.5px] text-[#334155] rounded-xl outline-none" />
        </Field>
        <Field label="Purpose">
          <input value={purpose} onChange={(e) => setPurpose(e.target.value)}
            className="neu-inset w-full h-10 px-3.5 text-[13.5px] text-[#334155] rounded-xl outline-none" />
        </Field>
        <Field label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3}
            className="neu-inset w-full rounded-xl px-3.5 py-2.5 text-[13.5px] text-[#334155] outline-none resize-none" />
        </Field>
        <Field label="Instructions">
          <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={4}
            placeholder="Standing instructions for how this department should operate."
            className="neu-inset w-full rounded-xl px-3.5 py-2.5 text-[13.5px] text-[#334155] placeholder:text-[#9aa6b8] outline-none resize-none" />
        </Field>
        <button onClick={save} disabled={saving}
          className="neu-btn-primary inline-flex items-center gap-2 h-10 px-4 text-[13.5px] font-semibold disabled:opacity-60">
          {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={16} />} Save Changes
        </button>
      </div>

      <div className="neu-card rounded-2xl p-5">
        <SectionTitle>Danger Zone</SectionTitle>
        <p className="text-[13px] text-[#8792a6] mb-3">
          {dept.is_default
            ? "This is a default department and cannot be archived."
            : "Archiving removes this department from active use. Agents and history are preserved."}
        </p>
        <button onClick={archive} disabled={dept.is_default || archiving}
          className="neu-btn-ghost inline-flex items-center gap-2 h-10 px-4 text-[13.5px] font-semibold text-rose-600 disabled:opacity-50 disabled:cursor-not-allowed">
          {archiving ? <Loader2 size={15} className="animate-spin" /> : <Archive size={16} />} Archive Department
        </button>
      </div>
    </div>
  );
};

export default ViewDepartmentDetail;
