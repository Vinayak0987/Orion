import { ChevronRight, ChevronDown, ArrowUp, ArrowRight, Layers, Zap, Clock, Users, FileText } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const STATS = [
  { label: "Total Memories", value: "1,248", pct: "+12%", Icon: Layers, tint: "bg-[#eef2ff] text-[#4f46e5]" },
  { label: "Short-term Memory", value: "428", pct: "+8%", Icon: Zap, tint: "bg-violet-50 text-violet-500" },
  { label: "Long-term Memory", value: "612", pct: "+15%", Icon: Clock, tint: "bg-blue-50 text-blue-500" },
  { label: "Department Memory", value: "208", pct: "+10%", Icon: Users, tint: "bg-[#eef2ff] text-[#4f46e5]" },
];

const RECENT = [
  { title: "User discussed Q3 marketing plan", time: "2 hours ago", type: "Short-term", tint: "bg-blue-50 text-blue-500" },
  { title: "Product roadmap for 2026", time: "5 hours ago", type: "Long-term", tint: "bg-[#eef2ff] text-[#4f46e5]" },
  { title: "HR policy document uploaded", time: "1 day ago", type: "Department", tint: "bg-emerald-50 text-emerald-600" },
  { title: "Competitor analysis summary", time: "2 days ago", type: "Long-term", tint: "bg-[#eef2ff] text-[#4f46e5]" },
];

/* Donut chart: Short 34, Long 49, Dept 17 */
const Donut = () => {
  const segs = [
    { pct: 34, color: "#818cf8" },
    { pct: 49, color: "#312e81" },
    { pct: 17, color: "#c7d2fe" },
  ];
  const R = 70, C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <svg viewBox="0 0 180 180" className="w-52 h-52 -rotate-90">
      <circle cx="90" cy="90" r={R} fill="none" stroke="#eef2ff" strokeWidth="26" />
      {segs.map((s, i) => {
        const len = (s.pct / 100) * C;
        const el = (
          <circle key={i} cx="90" cy="90" r={R} fill="none" stroke={s.color} strokeWidth="26"
            strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset} />
        );
        offset += len;
        return el;
      })}
    </svg>
  );
};

const LEGEND = [
  { label: "Short-term", pct: "34%", color: "bg-[#818cf8]" },
  { label: "Long-term", pct: "49%", color: "bg-[#312e81]" },
  { label: "Department", pct: "17%", color: "bg-[#c7d2fe]" },
];

/* Bar chart data — stacked (dark on light) */
const BARS = Array.from({ length: 30 }, (_, i) => {
  const seed = (i * 37) % 100;
  const total = 20 + (seed % 90);
  const dark = 10 + (seed % 55);
  return { total, dark };
});

export const ViewMemoryOverview = () => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Memory Overview" }]} />

    {/* Header */}
    <div className="flex items-start gap-4 mb-7">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="3" width="16" height="18" rx="2.5"/><path d="M9 3v18" strokeLinecap="round"/><circle cx="14.5" cy="12" r="2.2"/></svg>
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Memory Overview</h1>
        <p className="text-[15px] text-slate-500 mt-2">Short-term, long-term, department memory</p>
      </div>
      <button className="h-11 px-4 rounded-xl border border-[#e6ebf2] text-[14px] font-medium text-slate-600 flex items-center gap-3 hover:bg-slate-50">
        Last 30 days <ChevronDown size={16} className="text-slate-400" />
      </button>
    </div>

    {/* Stat cards */}
    <div className="grid grid-cols-4 gap-5 mb-6">
      {STATS.map((s) => (
        <div key={s.label} className="rounded-2xl border border-[#e6ebf2] shadow-sm p-5">
          <p className="text-[14px] font-medium text-slate-500">{s.label}</p>
          <p className="text-[32px] font-extrabold text-[#0b1220] leading-none mt-2">{s.value}</p>
          <div className="flex items-center justify-between mt-3">
            <span className="inline-flex items-center gap-1 text-[13px] font-bold text-emerald-600">
              <ArrowUp size={14} strokeWidth={2.6} /> {s.pct}
            </span>
            <span className={`w-11 h-11 rounded-xl grid place-items-center ${s.tint}`}><s.Icon size={20} /></span>
          </div>
        </div>
      ))}
    </div>

    {/* Distribution + Recent */}
    <div className="grid grid-cols-[1.15fr_1fr] gap-6 mb-6">
      {/* Distribution */}
      <div className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <h2 className="text-[18px] font-bold text-[#0b1220] mb-3">Memory Distribution</h2>
        <div className="flex items-center gap-8">
          <div className="relative shrink-0">
            <Donut />
            <div className="absolute inset-0 grid place-items-center">
              <div className="text-center">
                <p className="text-[26px] font-extrabold text-[#0b1220] leading-none">1,248</p>
                <p className="text-[12px] text-slate-400 mt-1">Total Memories</p>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-4">
            {LEGEND.map((l) => (
              <div key={l.label} className="flex items-center justify-between">
                <span className="flex items-center gap-2.5 text-[15px] font-medium text-slate-600">
                  <span className={`w-3 h-3 rounded-full ${l.color}`} /> {l.label}
                </span>
                <span className="text-[15px] font-bold text-slate-700">{l.pct}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent */}
      <div className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[18px] font-bold text-[#0b1220]">Recent Memories</h2>
          <button className="text-[14px] font-semibold text-[#4f46e5] flex items-center gap-1">View all <ArrowRight size={15} /></button>
        </div>
        <div className="space-y-1">
          {RECENT.map((r, i) => (
            <div key={r.title} className={`flex items-center gap-3.5 py-3 ${i !== RECENT.length - 1 ? "border-b border-slate-100" : ""}`}>
              <span className="w-10 h-10 rounded-xl bg-slate-100 grid place-items-center text-slate-500 shrink-0"><FileText size={18} /></span>
              <div className="flex-1 min-w-0">
                <p className="text-[15px] font-semibold text-slate-800 truncate">{r.title}</p>
                <p className="text-[13px] text-slate-400">{r.time}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-[12px] font-semibold ${r.tint}`}>{r.type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Activity chart */}
    <div className="rounded-2xl border border-[#e6ebf2] bg-white shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-[18px] font-bold text-[#0b1220]">Memory Activity</h2>
        <button className="h-10 px-4 rounded-xl border border-[#e6ebf2] text-[14px] font-medium text-slate-600 flex items-center gap-3 hover:bg-slate-50">
          Daily <ChevronDown size={16} className="text-slate-400" />
        </button>
      </div>
      <div className="flex gap-3">
        {/* Y axis */}
        <div className="flex flex-col justify-between text-[12px] text-slate-400 h-56 pb-6 text-right w-8">
          <span>150</span><span>100</span><span>50</span><span>0</span>
        </div>
        {/* Chart */}
        <div className="flex-1">
          <div className="relative h-56 border-b border-[#e6ebf2]">
            {/* gridlines */}
            {[0, 1, 2].map((g) => (
              <div key={g} className="absolute left-0 right-0 border-t border-dashed border-slate-100" style={{ top: `${(g / 3) * 100}%` }} />
            ))}
            <div className="absolute inset-0 flex items-end gap-[5px] px-1">
              {BARS.map((b, i) => (
                <div key={i} className="flex-1 flex flex-col justify-end items-center h-full">
                  <div className="w-full rounded-t-sm bg-[#c7d2fe]" style={{ height: `${(b.total / 150) * 100}%` }}>
                    <div className="w-full rounded-t-sm bg-[#4f46e5]" style={{ height: `${(b.dark / b.total) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          {/* X axis labels */}
          <div className="flex justify-between text-[12px] text-slate-400 mt-2 px-1">
            {["Sep 1", "Sep 5", "Sep 10", "Sep 15", "Sep 20", "Sep 25", "Sep 30"].map((l) => <span key={l}>{l}</span>)}
          </div>
        </div>
      </div>
    </div>
  </div>
);
