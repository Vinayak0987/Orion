import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus, Search, RefreshCw, ChevronRight, ChevronLeft, Boxes, Sparkles, BarChart3,
  Rocket, Microscope, ClipboardList, Cog,
} from "lucide-react";

import { missionApi } from "../../missionApi";
import { useToast } from "../ui/Toast.jsx";

const PAGE = 8;

const TYPE_TONE = {
  Research: "text-amber-600",
  Planning: "text-[#4f46e5]",
  Operations: "text-emerald-600",
};
const STATUS_TONE = {
  planning: "text-amber-600",
  running: "text-blue-600",
  completed: "text-emerald-600",
  partial: "text-amber-600",
  failed: "text-rose-600",
  stopped: "text-[#8792a6]",
};
const STATUS_LABEL = {
  planning: "Planning", running: "In Progress", completed: "Completed",
  partial: "Partial", failed: "Failed", stopped: "Stopped",
};
const TYPE_ICON = { Research: Microscope, Planning: ClipboardList, Operations: Cog };

const AVATAR_COLORS = [
  "from-[#6366f1] to-[#4338ca]", "from-[#ec4899] to-[#be185d]",
  "from-[#16a34a] to-[#15803d]", "from-[#f97316] to-[#c2410c]", "from-[#2563eb] to-[#1d4ed8]",
];

function timeAgo(iso) {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function AgentAvatars({ ids = [] }) {
  const shown = ids.slice(0, 3);
  const extra = ids.length - shown.length;
  if (ids.length === 0) return <span className="text-[12px] text-[#9aa6b8]">—</span>;
  return (
    <div className="flex items-center -space-x-2">
      {shown.map((id, i) => (
        <span key={id} className={`w-7 h-7 rounded-full bg-gradient-to-br ${AVATAR_COLORS[i % AVATAR_COLORS.length]} grid place-items-center text-[10px] font-bold text-white ring-2 ring-[#eef1f6]`}>
          {id.slice(0, 2).toUpperCase()}
        </span>
      ))}
      {extra > 0 && (
        <span className="w-7 h-7 rounded-full neu-circle grid place-items-center text-[10px] font-bold text-[#64748b] ring-2 ring-[#eef1f6]">+{extra}</span>
      )}
    </div>
  );
}

export const ViewMissions = ({ onViewDetails, onNavigate }) => {
  const toast = useToast();
  const [missions, setMissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState("All");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    missionApi
      .missionsQuery({ limit: 200 })
      .then((d) => { setMissions(d.missions || []); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  // Derive counts for the filter tabs.
  const counts = useMemo(() => {
    const c = { All: missions.length, Research: 0, Planning: 0, Operations: 0, Completed: 0 };
    for (const m of missions) {
      if (m.type && c[m.type] !== undefined) c[m.type] += 1;
      if (m.status === "completed") c.Completed += 1;
    }
    return c;
  }, [missions]);

  const filtered = useMemo(() => {
    let list = missions;
    if (tab === "Completed") list = list.filter((m) => m.status === "completed");
    else if (tab !== "All") list = list.filter((m) => m.type === tab);
    if (query) {
      const q = query.toLowerCase();
      list = list.filter((m) => (m.title || m.prompt || "").toLowerCase().includes(q) || (m.prompt || "").toLowerCase().includes(q));
    }
    return list;
  }, [missions, tab, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE));
  const pageRows = filtered.slice(page * PAGE, page * PAGE + PAGE);
  useEffect(() => { setPage(0); }, [tab, query]);

  const TABS = [
    ["All", counts.All], ["Research", counts.Research], ["Planning", counts.Planning],
    ["Operations", counts.Operations], ["Completed", counts.Completed],
  ];

  return (
    <div className="neu-surface h-full flex flex-col p-6 sm:p-7">
      <div className="max-w-[1400px] mx-auto w-full flex flex-col min-h-0 flex-1">
        {/* Header */}
        <div className="flex justify-between items-start mb-6 shrink-0">
          <div>
            <h1 className="text-[24px] leading-none font-bold tracking-[-0.4px] text-[#334155] mb-1.5">Missions</h1>
            <p className="text-[13.5px] text-[#64748b]">Plan, track, and review every goal Orion has worked on.</p>
          </div>
          <div className="flex items-center gap-2.5">
            <button onClick={load} className="neu-circle w-11 h-11 rounded-xl grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title="Refresh"><RefreshCw size={17} /></button>
            <button onClick={() => onNavigate?.("command-center")} className="neu-btn-primary h-11 px-5 text-[14px] font-semibold flex items-center gap-2">
              <Plus size={17} strokeWidth={2.6} /> New Mission
            </button>
          </div>
        </div>

        {/* Tabs + search */}
        <div className="flex items-center gap-3 mb-4 shrink-0 flex-wrap">
          <div className="neu-seg flex p-1 gap-1">
            {TABS.map(([name, n]) => (
              <button key={name} onClick={() => setTab(name)} className={`neu-seg-item px-3.5 py-2 text-[12.5px] font-semibold ${tab === name ? "neu-seg-item-active" : ""}`}>
                {name} <span className="opacity-60">({n})</span>
              </button>
            ))}
          </div>
          <div className="ml-auto relative w-64">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9aa6b8]" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search missions…" className="neu-input w-full h-10 pl-10 pr-3 text-[13.5px] text-[#334155]" />
          </div>
        </div>

        {error && (
          <div className="neu-card p-4 mb-4 border-l-4 border-rose-400">
            <p className="text-[13px] text-rose-600 font-medium">{error}</p>
            <p className="text-[11.5px] text-[#9aa6b8] mt-1">Start the mission backend on port 8081.</p>
          </div>
        )}

        {/* Table */}
        <div className="neu-card flex-1 min-h-0 overflow-auto scrollbar-hide p-2">
          {loading ? (
            <div className="p-10 text-center text-[#8792a6] text-[13px]">Loading…</div>
          ) : pageRows.length === 0 ? (
            <div className="p-12 text-center">
              <Boxes size={28} className="mx-auto text-[#b4bdcc] mb-3" />
              <p className="text-[14px] font-semibold text-[#334155] mb-1">No missions {tab !== "All" ? `in ${tab}` : "yet"}</p>
              <p className="text-[12.5px] text-[#8792a6]">Start one from the Command Center.</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[11.5px] font-semibold text-[#8792a6] uppercase tracking-wide">
                  <th className="py-3 px-3 w-10">#</th>
                  <th className="py-3 px-3">Mission / Objective</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Agents</th>
                  <th className="py-3 px-3 w-44">Progress</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3 text-right">Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((m, i) => {
                  const TypeIcon = TYPE_ICON[m.type] || ClipboardList;
                  const active = selected === m.id;
                  return (
                    <tr key={m.id} onClick={() => onViewDetails?.(m.id)}
                        className="cursor-pointer transition-colors hover:bg-[#e9edf4] rounded-xl">
                      <td className="py-3.5 px-3 text-[12.5px] text-[#9aa6b8] font-medium rounded-l-xl">{page * PAGE + i + 1}</td>
                      <td className="py-3.5 px-3">
                        <h4 className="text-[13px] font-semibold text-[#334155] truncate max-w-xs">{m.title || m.prompt}</h4>
                        <p className="text-[11.5px] text-[#9aa6b8] truncate max-w-md">{m.prompt}</p>
                      </td>
                      <td className="py-3.5 px-3">
                        <span className={`neu-chip inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold ${TYPE_TONE[m.type] || "text-[#64748b]"}`}>
                          <TypeIcon size={12} /> {m.type}
                        </span>
                      </td>
                      <td className="py-3.5 px-3"><AgentAvatars ids={m.agent_ids} /></td>
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2.5">
                          <div className="flex-1 neu-inset h-2 rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-gradient-to-r from-[#6366f1] to-[#4338ca]" style={{ width: `${m.progress || 0}%` }} />
                          </div>
                          <span className="text-[11.5px] font-bold text-[#64748b] w-9 text-right">{m.progress || 0}%</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-3">
                        <span className={`neu-chip inline-block px-2.5 py-1 text-[11px] font-bold ${STATUS_TONE[m.status] || "text-[#64748b]"}`}>
                          {STATUS_LABEL[m.status] || m.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-right text-[12px] text-[#9aa6b8] whitespace-nowrap rounded-r-xl">{timeAgo(m.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {filtered.length > PAGE && (
          <div className="flex justify-between items-center py-3 shrink-0 text-[12.5px] text-[#64748b] font-medium">
            <span>Showing {page * PAGE + 1}-{Math.min((page + 1) * PAGE, filtered.length)} of {filtered.length}</span>
            <div className="flex items-center gap-2">
              <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#64748b] disabled:opacity-40"><ChevronLeft size={16} /></button>
              {Array.from({ length: pageCount }).map((_, i) => (
                <button key={i} onClick={() => setPage(i)} className={`w-9 h-9 rounded-lg grid place-items-center text-[12.5px] font-bold ${i === page ? "neu-nav-active text-[#4f46e5]" : "neu-circle text-[#64748b]"}`}>{i + 1}</button>
              ))}
              <button disabled={page >= pageCount - 1} onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))} className="neu-circle w-9 h-9 rounded-lg grid place-items-center text-[#64748b] disabled:opacity-40"><ChevronRight size={16} /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
