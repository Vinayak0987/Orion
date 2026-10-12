import {
  BarChart3, MoreHorizontal, Pencil, Plus, Users, Link2, FileText, Target,
  DollarSign, Search, Share2, TrendingUp, ShoppingCart, CreditCard,
  PieChart, ChevronRight
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const STATS = [
  { Icon: Users, tint: "text-blue-600 bg-blue-50", value: "9", label: "Agents" },
  { Icon: Link2, tint: "text-violet-600 bg-violet-50", value: "4", label: "Active Missions" },
  { Icon: FileText, tint: "text-[#4f46e5] bg-[#eef2ff]", value: "276", label: "Knowledge Items" },
  { Icon: Target, tint: "text-emerald-600 bg-emerald-50", value: "91%", label: "Success Rate" },
];
const TABS = ["Overview","Activity","Members","Settings"];
const AGENTS1 = [
  { n: "Sales Agent", s: "Sales & Revenue", Icon: DollarSign, tint: "text-blue-600 bg-blue-100", card: "border-blue-100 bg-blue-50/50" },
  { n: "Lead Agent", s: "Lead Generation", Icon: TrendingUp, tint: "text-emerald-600 bg-emerald-100", card: "border-emerald-100 bg-emerald-50/50" },
  { n: "Customer Agent", s: "Customer Relations", Icon: ShoppingCart, tint: "text-violet-600 bg-violet-100", card: "border-violet-100 bg-violet-50/50" },
  { n: "Support Agent", s: "Customer Support", Icon: CreditCard, tint: "text-rose-500 bg-rose-100", card: "border-rose-100 bg-rose-50/50" },
];
const AGENTS2 = [
  { n: "Analytics Agent", s: "Sales Analytics", Icon: PieChart, tint: "text-orange-500 bg-orange-100", card: "border-orange-100 bg-orange-50/50" },
  { n: "Forecast Agent", s: "Sales Forecasting", Icon: BarChart3, tint: "text-blue-600 bg-blue-100", card: "border-blue-100 bg-blue-50/50" },
];
const MISSIONS = [
  { n: "Q4 Sales Strategy", st: "In Progress", pct: 65, Icon: DollarSign, tint: "text-blue-600 bg-blue-50" },
  { n: "Lead Generation Campaign", st: "In Progress", pct: 75, Icon: TrendingUp, tint: "text-emerald-600 bg-emerald-50" },
  { n: "Customer Analysis", st: "In Progress", pct: 85, Icon: ShoppingCart, tint: "text-violet-600 bg-violet-50" },
  { n: "Sales Report Generation", st: "Planning", pct: 35, Icon: PieChart, tint: "text-slate-500 bg-slate-100" },
];

const AgentNode = ({ a }) => (
  <div className={`rounded-xl border px-3 py-3 text-center shadow-sm ${a.card || "border-[#e6ebf2] bg-white"}`}>
    <span className={`mx-auto w-9 h-9 rounded-lg grid place-items-center ${a.tint}`}><a.Icon size={16}/></span>
    <p className="text-[12px] font-bold text-slate-800 mt-2 leading-tight">{a.n}</p>
    <p className="text-[10px] text-slate-400">{a.s}</p>
  </div>
);

export const ViewSalesDept = ({ onTabChange }) => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "Sales" }]} />

    {/* Header card */}
    <div className="rounded-2xl border border-[#e6ebf2] bg-white p-4 flex items-center gap-4 mb-4 shadow-sm">
      <span className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 grid place-items-center"><BarChart3 size={22} fill="currentColor"/></span>
      <div className="flex-1">
        <div className="flex items-center gap-2.5"><h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Sales</h1><span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Healthy</span></div>
        <p className="text-[15px] text-[#64748b] mt-2">Drive revenue, customer acquisition and sales performance.</p>
      </div>
      <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] grid place-items-center text-slate-500"><MoreHorizontal size={16}/></button>
      <button className="px-3.5 py-2 rounded-lg border border-[#e6ebf2] text-sm font-medium text-slate-700 flex items-center gap-1.5"><Pencil size={14}/>Edit</button>
      <button className="px-4 py-2 rounded-lg bg-[#4f46e5] text-white text-sm font-semibold flex items-center gap-1.5 shadow-[0_4px_12px_rgba(79,70,229,0.28)]"><Plus size={15}/>New Mission</button>
    </div>

    {/* Stats */}
    <div className="grid grid-cols-4 gap-4 mb-4">
      {STATS.map(s=>(
        <div key={s.label} className="rounded-2xl border border-[#e6ebf2] bg-white p-4 flex items-center gap-3 shadow-sm">
          <span className={`w-11 h-11 rounded-xl grid place-items-center ${s.tint}`}><s.Icon size={20}/></span>
          <div><p className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">{s.value}</p><p className="text-[11px] text-slate-500 mt-1">{s.label}</p></div>
        </div>
      ))}
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-6 border-b border-[#e6ebf2] mb-5">
      {TABS.map((t,i)=><button key={t} onClick={() => {
        if (t === "Activity" && onTabChange) onTabChange("sales-activity");
        else if (t === "Members" && onTabChange) onTabChange("sales-members");
        else if (t === "Settings" && onTabChange) onTabChange("sales-settings");
      }} className={`pb-3 text-sm font-semibold border-b-2 -mb-px ${i===0?"text-[#4f46e5] border-[#4f46e5]":"text-slate-500 border-transparent hover:text-slate-700"}`}>{t}</button>)}
    </div>

    <div className="grid grid-cols-[1.55fr_1fr] gap-5 mb-5">
      {/* Agent structure */}
      <div className="rounded-2xl border border-[#e6ebf2] bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-bold text-slate-900">Department Agent Structure</h2><span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Live</span></div>
        {/* Sales root (centered) */}
        <div className="flex justify-center mb-1">
          <div className="inline-flex rounded-xl border border-blue-100 bg-blue-50/40 px-4 py-3 items-center gap-3">
            <span className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 grid place-items-center"><BarChart3 size={19} fill="currentColor"/></span>
            <div><p className="text-sm font-bold text-slate-800 leading-tight">Sales</p><p className="text-[10px] text-slate-400">Department</p></div>
          </div>
        </div>
        {/* centered bus: drop from center, horizontal bus, dots + arrow drops to 4 agents */}
        <svg className="w-full h-8" viewBox="0 0 640 32" preserveAspectRatio="none" aria-hidden="true">
          <path d="M320 0 V12 M80 12 H560 M80 12 V26 M240 12 V26 M400 12 V26 M560 12 V26" fill="none" stroke="#4f46e5" strokeWidth="1.5"/>
          {[80,240,400,560].map((x)=><circle key={x} cx={x} cy="12" r="3" fill="#4f46e5"/>)}
          {[80,240,400,560].map((x)=><path key={"a"+x} d={`M${x-4} 22 L${x} 27 L${x+4} 22 Z`} fill="#4f46e5"/>)}
        </svg>
        <div className="grid grid-cols-4 gap-3 mb-1">{AGENTS1.map(a=><AgentNode key={a.n} a={a}/>)}</div>
        {/* second centered bus to 2 sub-agents (under middle) */}
        <svg className="w-full h-8" viewBox="0 0 640 32" preserveAspectRatio="none" aria-hidden="true">
          <path d="M320 0 V12 M240 12 H400 M240 12 V26 M400 12 V26" fill="none" stroke="#4f46e5" strokeWidth="1.5"/>
          {[240,400].map((x)=><circle key={x} cx={x} cy="12" r="3" fill="#4f46e5"/>)}
          {[240,400].map((x)=><path key={"a"+x} d={`M${x-4} 22 L${x} 27 L${x+4} 22 Z`} fill="#4f46e5"/>)}
        </svg>
        <div className="grid grid-cols-2 gap-3 px-[25%]">{AGENTS2.map(a=><AgentNode key={a.n} a={a}/>)}</div>
      </div>

      {/* Active missions */}
      <div className="rounded-2xl border border-[#e6ebf2] bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-bold text-slate-900">Active Missions</h2><a className="text-xs font-semibold text-[#4f46e5] flex items-center gap-1">View all <ChevronRight size={12}/></a></div>
        <div className="space-y-3">
          {MISSIONS.map(m=>(
            <div key={m.n} className="rounded-xl border border-[#e6ebf2] p-3">
              <div className="flex items-center gap-2.5 mb-2"><span className={`w-8 h-8 rounded-lg grid place-items-center ${m.tint}`}><m.Icon size={15}/></span><div className="flex-1"><p className="text-xs font-bold text-slate-800">{m.n}</p><span className="text-[10px] font-medium text-[#4f46e5] bg-[#eef2ff] px-1.5 py-0.5 rounded">{m.st}</span></div><span className="text-xs font-bold text-slate-700">{m.pct}%</span></div>
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden"><div className="h-1.5 rounded-full bg-[#4f46e5]" style={{width:`${m.pct}%`}}/></div>
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Bottom row */}
    <div className="grid grid-cols-3 gap-5">
      <div className="rounded-2xl border border-[#e6ebf2] bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 mb-3">Connected Tools</h3>
        <div className="flex items-center gap-2 mb-3">{["S","C","H"].map((l,i)=><span key={i} className="w-9 h-9 rounded-lg border border-[#e6ebf2] grid place-items-center text-xs font-bold text-slate-500">{l}</span>)}<span className="w-9 h-9 rounded-lg bg-slate-100 grid place-items-center text-[11px] font-semibold text-slate-500">+7</span></div>
        <a className="text-xs font-semibold text-[#4f46e5] flex items-center gap-1">Manage tools <ChevronRight size={12}/></a>
      </div>
      <div className="rounded-2xl border border-[#e6ebf2] bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 mb-3">Knowledge Sources</h3>
        <div className="flex items-center gap-2 mb-3">{[FileText,FileText,FileText].map((I,i)=><span key={i} className="w-9 h-9 rounded-lg border border-[#e6ebf2] grid place-items-center text-[#4f46e5]"><I size={16}/></span>)}<span className="w-9 h-9 rounded-lg bg-slate-100 grid place-items-center text-[11px] font-semibold text-slate-500">+4</span></div>
        <a className="text-xs font-semibold text-[#4f46e5] flex items-center gap-1">Manage knowledge <ChevronRight size={12}/></a>
      </div>
      <div className="rounded-2xl border border-[#e6ebf2] bg-white p-5 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 mb-2">Department Performance</h3>
        <div className="flex items-end justify-between">
          <svg viewBox="0 0 120 50" className="w-28 h-12"><polyline points="0,45 20,38 40,40 60,28 80,30 100,16 120,8" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          <div className="text-right"><p className="text-lg font-extrabold text-emerald-600">+18%</p><p className="text-[10px] text-slate-400">vs last month</p></div>
        </div>
      </div>
    </div>
  </div>
);