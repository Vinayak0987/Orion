// Knowledge · Memory Overview (ViewMemoryOverview.jsx) — redesigned
// A clean, scannable overview of what agents have learned, wired to the backend.
//   entries      = knowledgeApi.listMemory(agentId).entries
//   agent filter = agentApi.list().agents
//   delete       = knowledgeApi.deleteMemory
//   open entry   = onOpenEntry(entry) prop
// Design: 23px semibold title, 15px section headers, 13.5–14px body (DESIGN_SYSTEM.md).
import { useEffect, useMemo, useState } from "react";
import { Layers, Zap, Clock, Users, Trash2, Loader2, Brain, Search } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";
import { knowledgeApi } from "../../knowledgeApi.js";
import { agentApi } from "../../agentApi.js";
import { useToast } from "../ui/Toast.jsx";

const fmtAgo = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso), diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return "yesterday";
  return `${Math.floor(diff / 86400)}d ago`;
};

const PALETTE = ["#4f46e5", "#7c6cf0", "#a5b4fc", "#c7d2fe", "#818cf8"];

export function ViewMemoryOverview({ onOpenEntry }) {
  const toast = useToast();
  const [entries, setEntries] = useState([]);
  const [byAgent, setByAgent] = useState({});
  const [agents, setAgents] = useState([]);
  const [filter, setFilter] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const d = await knowledgeApi.listMemory(filter);
      setEntries(d.entries || []); setByAgent(d.by_agent || {});
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);
  useEffect(() => { agentApi.list().then((d) => setAgents(d.agents || [])).catch(() => {}); }, []);

  const nameOf = (id) => agents.find((a) => a.id === id)?.name || id;
  const del = async (id) => {
    try { await knowledgeApi.deleteMemory(id); setEntries((e) => e.filter((x) => x.id !== id)); toast.success("Memory deleted"); }
    catch (e) { toast.error(e.message); }
  };

  const stats = useMemo(() => {
    const now = Date.now();
    const recent = entries.filter((e) => e.created_at && (now - new Date(e.created_at)) < 7 * 86400e3).length;
    const expiring = entries.filter((e) => e.expires_at).length;
    const agentsWithMem = Object.values(byAgent).filter((n) => n > 0).length;
    return { total: entries.length, recent, expiring, agentsWithMem };
  }, [entries, byAgent]);

  // Distribution by agent (ranked, with share %).
  const dist = useMemo(() => {
    const pairs = Object.entries(byAgent).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
    const total = pairs.reduce((s, [, n]) => s + n, 0) || 1;
    return pairs.slice(0, 6).map(([id, n], i) => ({
      id, label: nameOf(id), count: n, pct: Math.round((n / total) * 100), color: PALETTE[i % PALETTE.length],
    }));
    // eslint-disable-next-line
  }, [byAgent, agents]);

  const STAT_CARDS = [
    { label: "Total Memories", value: stats.total, Icon: Layers, tint: "text-[#4f46e5]" },
    { label: "Added This Week", value: stats.recent, Icon: Zap, tint: "text-violet-500" },
    { label: "With Expiry", value: stats.expiring, Icon: Clock, tint: "text-sky-500" },
    { label: "Agents w/ Memory", value: stats.agentsWithMem, Icon: Users, tint: "text-emerald-500" },
  ];

  const visible = useMemo(() => {
    const sorted = [...entries].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    if (!q.trim()) return sorted;
    const needle = q.toLowerCase();
    return sorted.filter((e) => (e.content || "").toLowerCase().includes(needle) || nameOf(e.agent_id).toLowerCase().includes(needle));
    // eslint-disable-next-line
  }, [entries, q, agents]);

  return (
    <div className="neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-6 sm:px-7 sm:py-7">
      <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Memory Overview" }]} />

      {/* Header */}
      <div className="flex items-start gap-3 mb-6">
        <span className="neu-circle w-10 h-10 rounded-xl text-[#4f46e5] grid place-items-center shrink-0">
          <Brain size={19} />
        </span>
        <div className="flex-1 min-w-0 pt-0.5">
          <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">Memory Overview</h1>
          <p className="text-[13px] text-[#8792a6] mt-1">What your agents have learned from past work</p>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}
          className="neu-input neu-select h-10 px-3.5 rounded-xl text-[13.5px] text-[#5b6678] shrink-0">
          <option value="">All agents</option>
          {agents.map((a) => <option key={a.id} value={a.id}>{a.name} ({byAgent[a.id] || 0})</option>)}
        </select>
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {STAT_CARDS.map((s) => (
          <div key={s.label} className="neu-raised rounded-xl p-4 flex items-center gap-3.5">
            <span className={`neu-circle w-10 h-10 rounded-lg grid place-items-center shrink-0 ${s.tint}`}><s.Icon size={18} /></span>
            <div className="min-w-0">
              <p className="text-[21px] font-semibold text-[#334155] leading-none">{s.value}</p>
              <p className="text-[12px] font-medium text-[#8792a6] mt-1 truncate">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Two-column: distribution (left) + memory stream (right) */}
      <div className="grid grid-cols-[320px_1fr] gap-5 items-start">
        {/* Distribution — horizontal bars, ranked */}
        <div className="neu-card rounded-2xl p-5">
          <h2 className="text-[15px] font-semibold text-[#334155] mb-4">By Agent</h2>
          {loading ? (
            <div className="grid place-items-center py-14 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
          ) : dist.length === 0 ? (
            <p className="text-[13px] text-[#9aa6b8] py-12 text-center">No memories to distribute yet.</p>
          ) : (
            <div className="space-y-3.5">
              {dist.map((d) => (
                <button key={d.id} onClick={() => setFilter(d.id)} className="w-full text-left group">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[13px] font-medium text-[#5b6678] truncate group-hover:text-[#4f46e5]">{d.label}</span>
                    <span className="text-[12px] font-semibold text-[#334155] shrink-0 ml-2">{d.count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-[#e2e6ee] overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${d.pct}%`, background: d.color }} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Memory stream */}
        <div className="neu-card rounded-2xl p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-[15px] font-semibold text-[#334155]">
              {filter ? `${nameOf(filter)}'s Memories` : "All Memories"}
            </h2>
            <div className="relative w-[240px] max-w-[50%]">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9aa6b8]" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search memories…"
                className="neu-input w-full h-9 pl-9 pr-3 rounded-lg text-[13px] text-[#334155] placeholder:text-[#9aa6b8]" />
            </div>
          </div>

          {loading ? (
            <div className="grid place-items-center py-16 text-[#9aa6b8]"><Loader2 className="animate-spin" /></div>
          ) : visible.length === 0 ? (
            <div className="neu-inset rounded-xl py-14 text-center text-[#8792a6] text-[13.5px]">
              {entries.length === 0
                ? "No memories yet. Agents build these automatically as they complete tasks (if memory is enabled)."
                : "No memories match your search."}
            </div>
          ) : (
            <div className="space-y-2 max-h-[calc(100vh-360px)] overflow-y-auto scrollbar-hide pr-0.5">
              {visible.map((e) => (
                <div key={e.id} className="neu-inset rounded-xl px-3.5 py-3 flex items-start gap-3 group">
                  <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-violet-600 shrink-0 mt-0.5"><Brain size={15} /></span>
                  <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onOpenEntry?.(e)}>
                    <p className="text-[13.5px] text-[#334155] line-clamp-2 leading-snug">{e.content}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-[11.5px] font-medium text-[#4f46e5]">{nameOf(e.agent_id)}</span>
                      <span className="w-1 h-1 rounded-full bg-[#c7d2fe]" />
                      <span className="text-[11.5px] text-[#9aa6b8]">{fmtAgo(e.created_at)}</span>
                      {e.expires_at && <><span className="w-1 h-1 rounded-full bg-[#c7d2fe]" /><span className="text-[11.5px] text-[#9aa6b8] flex items-center gap-1"><Clock size={10} /> expires</span></>}
                    </div>
                  </div>
                  <button onClick={() => del(e.id)}
                    className="neu-circle w-7 h-7 rounded-lg grid place-items-center text-rose-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete"><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
