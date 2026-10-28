// Departments · Overview (ViewDepartments.jsx)
// Live departments overview wired to departmentApi.list(). Org-tree panel with
// an "Orion" root above real department cards, plus a detail table. Clicking a
// department calls onDepartmentClick(dept) with the full dept object.
import { useEffect, useMemo, useState } from "react";
import {
  Building2, Plus, Search, Loader2, RefreshCw, AlertCircle, Network,
  Megaphone, Landmark, Settings2, BarChart3, Users, FlaskConical, Boxes,
} from "lucide-react";
import { departmentApi } from "../../departmentApi.js";
import { useToast } from "../ui/Toast.jsx";

// Icon + tint chosen from dept_type (falls back to a generic box).
const TYPE_ICON = {
  marketing: { Icon: Megaphone, tint: "text-pink-600" },
  finance: { Icon: Landmark, tint: "text-emerald-600" },
  operations: { Icon: Settings2, tint: "text-orange-500" },
  sales: { Icon: BarChart3, tint: "text-blue-600" },
  hr: { Icon: Users, tint: "text-rose-500" },
  research: { Icon: FlaskConical, tint: "text-[#4f46e5]" },
  general: { Icon: Boxes, tint: "text-slate-500" },
};
const typeMeta = (t) => TYPE_ICON[t] || { Icon: Building2, tint: "text-[#4f46e5]" };

const STATUS_DOT = {
  active: "bg-emerald-500", healthy: "bg-emerald-500", idle: "bg-amber-500",
  paused: "bg-amber-500", archived: "bg-slate-400",
};

const relTime = (iso) => {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const headName = (d) => d.stats?.head || d.head?.agent_name || d.head?.name || "—";

const DeptCard = ({ d, onClick }) => {
  const { Icon, tint } = typeMeta(d.dept_type);
  const st = d.stats || {};
  return (
    <div onClick={onClick}
      className="neu-card rounded-2xl p-4 cursor-pointer hover:-translate-y-0.5 transition-transform">
      <div className="flex items-center gap-3 mb-2.5">
        <span className={`neu-circle w-11 h-11 rounded-xl grid place-items-center ${tint}`}><Icon size={20} strokeWidth={2} /></span>
        <div className="min-w-0 flex-1">
          <h3 className="text-[15px] font-bold text-[#334155] leading-tight truncate">{d.name}</h3>
          <p className="text-[11.5px] text-[#9aa6b8] capitalize">{d.dept_type || "general"}</p>
        </div>
        {d.is_default && <span className="neu-chip text-[9.5px] font-bold text-[#4f46e5] px-1.5 py-0.5">Default</span>}
      </div>
      <div className="flex items-center gap-3 text-[11.5px] text-[#8792a6] mb-2">
        <span className="flex items-center gap-1"><Users size={12} /> {st.members ?? 0}</span>
        <span className="flex items-center gap-1" title="Head"><Boxes size={12} /> {headName(d)}</span>
        <span className="ml-auto flex items-center gap-1" title="Active missions"><BarChart3 size={12} /> {st.active_missions ?? 0}</span>
      </div>
      <span className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[#5b6678] capitalize">
        <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[d.status] || "bg-slate-400"}`} />{d.status || "active"}
      </span>
    </div>
  );
};

export function ViewDepartments({ onCreate, onDepartmentClick }) {
  const toast = useToast();
  const [depts, setDepts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");

  const load = () => {
    setLoading(true); setError("");
    departmentApi.list()
      .then((d) => setDepts(d.departments || []))
      .catch((e) => { setError(e.message); toast.error(e.message); })
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const filtered = useMemo(() => depts.filter((d) =>
    !q || `${d.name} ${d.dept_type || ""} ${d.purpose || ""}`.toLowerCase().includes(q.toLowerCase())
  ), [depts, q]);

  const click = (d) => onDepartmentClick && onDepartmentClick(d);

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-8">
      <div className="max-w-[1120px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h1 className="text-[23px] font-semibold text-[#334155]">Departments</h1>
            <p className="text-[14px] text-[#8792a6] mt-1">Organize your business around autonomous teams, each led by a head agent.</p>
          </div>
          <div className="flex items-center gap-2.5 shrink-0">
            <button onClick={load} title="Refresh" className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#5b6678]">
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
            <button onClick={onCreate} className="neu-btn-primary inline-flex items-center gap-2 h-10 px-4 text-[14px] font-semibold">
              <Plus size={17} /> New Department
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="flex flex-wrap items-center gap-2.5 mb-6">
          <div className="neu-inset flex items-center gap-2 px-3.5 h-11 rounded-xl flex-1 min-w-[220px]">
            <Search size={17} className="text-[#9aa6b8]" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search departments…"
              className="bg-transparent outline-none text-[14px] text-[#334155] w-full placeholder:text-[#9aa6b8]" />
          </div>
        </div>

        {loading ? (
          <div className="grid place-items-center py-20 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
        ) : error ? (
          <div className="neu-inset rounded-2xl py-14 text-center">
            <AlertCircle className="mx-auto text-rose-500 mb-2" />
            <p className="text-[13.5px] text-[#5b6678]">{error}</p>
            <button onClick={load} className="neu-btn-ghost mt-3 h-9 px-4 text-[13px] font-semibold">Retry</button>
          </div>
        ) : depts.length === 0 ? (
          <div className="neu-inset rounded-2xl py-16 text-center text-[#8792a6]">
            No departments yet. Create your first department to start organizing autonomous teams.
          </div>
        ) : (
          <>
            {/* Org tree panel */}
            <div className="neu-card rounded-2xl p-6 mb-5">
              <div className="flex justify-center">
                <div className="neu-raised rounded-2xl px-5 py-3 flex items-center gap-3 border border-[#c7d2fe]">
                  <span className="w-11 h-11 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] text-white grid place-items-center shrink-0"><Building2 size={20} /></span>
                  <div>
                    <p className="text-[15px] font-bold text-[#334155] leading-tight">Orion</p>
                    <p className="text-[11px] text-[#9aa6b8]">Business Operating System · {depts.length} department{depts.length === 1 ? "" : "s"}</p>
                  </div>
                </div>
              </div>
              <div className="flex justify-center my-2">
                <Network size={18} className="text-[#c7d2fe]" />
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map((d) => <DeptCard key={d.id} d={d} onClick={() => click(d)} />)}
              </div>
              {filtered.length === 0 && (
                <p className="text-center text-[13px] text-[#8792a6] py-6">No departments match your search.</p>
              )}
            </div>

            {/* Detail table */}
            <div className="neu-card rounded-2xl p-2 overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[11.5px] uppercase tracking-wide text-[#9aa6b8]">
                    <th className="py-3 px-3">Department</th><th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Head</th><th className="py-3 px-3">Members</th>
                    <th className="py-3 px-3">Active Missions</th><th className="py-3 px-3">Knowledge</th>
                    <th className="py-3 px-3">Status</th><th className="py-3 px-3">Last Activity</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((d) => {
                    const { Icon, tint } = typeMeta(d.dept_type);
                    const st = d.stats || {};
                    return (
                      <tr key={d.id} onClick={() => click(d)}
                        className="hover:bg-[#e9edf4] transition-colors rounded-xl cursor-pointer">
                        <td className="py-3 px-3">
                          <span className="flex items-center gap-2 font-semibold text-[#334155] text-[13.5px]">
                            <Icon size={16} className={tint} />{d.name}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[13px] text-[#5b6678] capitalize">{d.dept_type || "general"}</td>
                        <td className="py-3 px-3 text-[13px] text-[#5b6678]">{headName(d)}</td>
                        <td className="py-3 px-3 text-[13px] text-[#5b6678]">{st.members ?? 0}</td>
                        <td className="py-3 px-3 text-[13px] text-[#5b6678]">{st.active_missions ?? 0}</td>
                        <td className="py-3 px-3 text-[13px] text-[#5b6678]">{st.knowledge_documents ?? 0}</td>
                        <td className="py-3 px-3">
                          <span className="inline-flex items-center gap-1.5 text-[12.5px] font-medium text-[#5b6678] capitalize">
                            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[d.status] || "bg-slate-400"}`} />{d.status || "active"}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[12.5px] text-[#8792a6]">{relTime(st.last_activity)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-[12px] text-[#9aa6b8] mt-4 text-center">
              {depts.length} department{depts.length === 1 ? "" : "s"} · click any row or card to open its workspace
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default ViewDepartments;
