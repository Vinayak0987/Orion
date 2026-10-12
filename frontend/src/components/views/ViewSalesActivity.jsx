import { ChevronDown, DollarSign, TrendingUp, ShoppingCart, FileText, ShieldCheck, BarChart3, CircleCheck } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const STATS = [
  { value: "15", label: "Total Sales", sub: "+25%", subColor: "text-emerald-500" },
  { value: "12", label: "Completed", sub: "+18%", subColor: "text-emerald-500" },
  { value: "94%", label: "Success Rate", sub: "+6%", subColor: "text-emerald-500" },
  { value: "3.5h", label: "Avg. Execution Time", sub: "-22%", subColor: "text-emerald-500" },
  { value: "$2.4K", label: "Total Revenue", sub: "+18%", subColor: "text-rose-500" },
];
const TABS = ["Activity Feed","Performance","Missions","Agent Activity","Tool Usage"];

const TODAY = [
  { Icon: DollarSign, tint: "text-blue-600 bg-blue-50", t: "Sales Agent completed task", d: "Closed deal with new client", time: "11:15 AM", done: true },
  { Icon: TrendingUp, tint: "text-emerald-600 bg-emerald-50", t: "Lead Agent updated pipeline", d: "Added 8 new qualified leads", time: "10:30 AM", done: true },
  { Icon: ShoppingCart, tint: "text-violet-600 bg-violet-50", t: "New mission started", d: "Customer follow-up campaign", time: "09:45 AM", done: false },
  { Icon: FileText, tint: "text-blue-600 bg-blue-50", t: "Sales Agent completed task", d: "Generated sales report", time: "09:00 AM", done: true },
  { Icon: ShieldCheck, tint: "text-emerald-600 bg-emerald-50", t: "Human approval received", d: "Discount approved for VIP client", time: "08:15 AM", done: true },
];
const YEST = [
  { Icon: BarChart3, tint: "text-orange-500 bg-orange-50", t: "Analytics Agent generated report", d: "Weekly sales performance analysis", time: "5:45 PM", done: true },
  { Icon: DollarSign, tint: "text-blue-600 bg-blue-50", t: "Sales Agent completed task", d: "Followed up with 12 prospects", time: "3:30 PM", done: true },
];

const WORKLOAD = [
  { n: "Sales Agent", pct: 82 }, { n: "Lead Agent", pct: 75 }, { n: "Customer Agent", pct: 70 },
  { n: "Support Agent", pct: 65 }, { n: "Analytics Agent", pct: 60 }, { n: "Forecast Agent", pct: 55 },
];
const OUTCOMES = [
  { t: "New client acquisition: $15K deal", time: "1h ago" },
  { t: "Pipeline increased by 35%", time: "4h ago" },
  { t: "Customer satisfaction up 12%", time: "1d ago" },
];

const FeedRow = ({ e, last }) => (
  <div className="flex gap-3 relative">
    {!last && <span className="absolute left-[15px] top-9 bottom-0 w-px bg-slate-100" />}
    <span className={`w-8 h-8 rounded-full grid place-items-center shrink-0 z-10 ${e.tint}`}><e.Icon size={15} /></span>
    <div className="flex-1 pb-5">
      <div className="flex items-center justify-between"><p className="text-sm font-semibold text-slate-800">{e.t}</p><span className="text-[11px] text-slate-400">{e.time}</span></div>
      <p className="text-xs text-slate-400 mt-0.5">{e.d}</p>
    </div>
  </div>
);

export const ViewSalesActivity = () => (
  <div className="h-full p-6 overflow-y-auto scrollbar-hide bg-white">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "Sales" }, { label: "Activity" }]} />

    <div className="flex items-start justify-between mb-5">
      <div><h1 className="text-2xl font-extrabold text-[#17143f] tracking-tight">Sales Activity</h1><p className="text-xs text-slate-500 mt-1">Track sales performance, missions and recent work.</p></div>
      <button className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 flex items-center gap-2">Last 30 days <ChevronDown size={15}/></button>
    </div>

    {/* Stats */}
    <div className="grid grid-cols-5 gap-4 mb-6">
      {STATS.map(s=>(
        <div key={s.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-3xl font-extrabold text-slate-800 leading-none">{s.value}</p><p className="text-xs text-slate-500 mt-1.5">{s.label}</p><p className={`text-[11px] font-semibold mt-0.5 ${s.subColor}`}>{s.sub}</p></div>
      ))}
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-6 border-b border-slate-200 mb-5">
      {TABS.map((t,i)=><button key={t} className={`pb-3 text-sm font-semibold border-b-2 -mb-px ${i===0?"text-indigo-600 border-indigo-600":"text-slate-500 border-transparent hover:text-slate-700"}`}>{t}</button>)}
    </div>

    <div className="grid grid-cols-[1.5fr_1fr] gap-6">
      {/* Feed */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold text-slate-700 mb-3">Today</p>
        <div>{TODAY.map((e,i)=><FeedRow key={i} e={e} last={i===TODAY.length-1}/>)}</div>
        <p className="text-xs font-bold text-slate-700 mb-3 mt-2">Yesterday</p>
        <div>{YEST.map((e,i)=><FeedRow key={i} e={e} last={i===YEST.length-1}/>)}</div>
      </div>

      {/* Right column */}
      <div className="space-y-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-3">Agent Workload</h3>
          <div className="space-y-2.5">
            {WORKLOAD.map(w=>(
              <div key={w.n} className="flex items-center gap-3"><span className="text-xs text-slate-600 w-28 shrink-0">{w.n}</span><div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden"><div className="h-2 rounded-full bg-indigo-500" style={{width:`${w.pct}%`}}/></div><span className="text-[11px] font-semibold text-slate-500 w-8 text-right">{w.pct}%</span></div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3"><h3 className="text-sm font-bold text-slate-900">Mission Execution</h3><span className="text-[10px] text-slate-400 flex items-center gap-2"><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-500"/>Completed</span><span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-200"/>In Progress</span></span></div>
          <div className="flex items-end justify-between gap-1.5 h-28">
            {[[65,25],[75,30],[55,45],[70,20],[60,25],[85,35],[50,30],[80,20],[45,50],[90,25],[70,35],[75,20]].map(([a,b],i)=>(
              <div key={i} className="flex-1 flex flex-col items-center justify-end gap-0.5 h-full">
                <div className="w-full rounded-t bg-indigo-500" style={{height:`${a}%`}}/>
                <div className="w-full rounded-t bg-indigo-200" style={{height:`${b/3}%`}}/>
              </div>
            ))}
          </div>
          <div className="flex justify-between text-[9px] text-slate-400 px-1 mt-1.5"><span>Sep 1</span><span>Sep 7</span><span>Sep 14</span><span>Sep 21</span><span>Sep 30</span></div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-3">Recent Outcomes</h3>
          <div className="space-y-3">
            {OUTCOMES.map(o=>(
              <div key={o.t} className="flex items-center gap-2.5"><CircleCheck size={16} className="text-emerald-500 shrink-0"/><p className="text-xs text-slate-600 flex-1">{o.t}</p><span className="text-[10px] text-slate-400">{o.time}</span></div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);