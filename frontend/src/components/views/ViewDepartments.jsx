import { Network, Plus, ChevronDown, Building2, Megaphone, Landmark, Settings2, BarChart3, Users, FlaskConical } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = [["All Departments","6"],["Pre-built",null],["Custom","2"]];

const DEPTS = [
  { name: "Marketing", agents: 12, Icon: Megaphone, tint: "text-violet-600 bg-violet-50" },
  { name: "Finance", agents: 8, Icon: Landmark, tint: "text-emerald-600 bg-emerald-50" },
  { name: "Operations", agents: 10, Icon: Settings2, tint: "text-orange-500 bg-orange-50" },
  { name: "Sales", agents: 9, Icon: BarChart3, tint: "text-blue-600 bg-blue-50" },
  { name: "HR", agents: 6, Icon: Users, tint: "text-rose-500 bg-rose-50" },
  { name: "Research", agents: 7, Icon: FlaskConical, tint: "text-[#4f46e5] bg-[#eef2ff]" },
];

const ROWS = [
  { name: "Marketing", Icon: Megaphone, tint: "text-violet-600", type: "Pre-built", custom: false, lead: 12, active: 12, know: 324, act: "2h ago" },
  { name: "Finance", Icon: Landmark, tint: "text-emerald-600", type: "Pre-built", custom: false, lead: 8, active: 3, know: 198, act: "5h ago" },
  { name: "Operations", Icon: Settings2, tint: "text-orange-500", type: "Pre-built", custom: false, lead: 10, active: 6, know: 412, act: "1h ago" },
  { name: "Sales", Icon: BarChart3, tint: "text-blue-600", type: "Pre-built", custom: false, lead: 9, active: 4, know: 276, act: "3h ago" },
  { name: "HR", Icon: Users, tint: "text-rose-500", type: "Custom", custom: true, lead: 2, active: 2, know: 134, act: "6h ago" },
  { name: "Research", Icon: FlaskConical, tint: "text-[#4f46e5]", type: "Custom", custom: true, lead: 7, active: 3, know: 298, act: "4h ago" },
];

const DeptCard = ({ d, onClick }) => (
  <div onClick={onClick} className="rounded-2xl border border-[#e6ebf2] bg-white p-4 shadow-[0_8px_26px_rgba(36,45,64,0.045)] cursor-pointer hover:bg-slate-50 transition-colors">
    <div className="flex items-center gap-3 mb-2.5">
      <span className={`w-11 h-11 rounded-xl grid place-items-center ${d.tint}`}><d.Icon size={20} strokeWidth={2}/></span>
      <div><h3 className="text-[15px] font-bold text-slate-800 leading-tight">{d.name}</h3><p className="text-xs text-slate-400">{d.agents} agents</p></div>
    </div>
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Healthy</span>
  </div>
);

export const ViewDepartments = ({ onOpen, onCreate, onDepartmentClick }) => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "All Departments" }]} />

    <div className="flex items-start justify-between mb-5">
      <div>
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Departments</h1>
        <p className="text-[15px] text-[#64748b] mt-2">Organize your business around autonomous teams.</p>
      </div>
      <div className="flex items-center gap-3">
        <button className="h-12 px-5 rounded-xl border border-[#e6ebf2] text-[15px] font-semibold text-[#334155] flex items-center gap-2 hover:bg-[#f5f8fc]"><Network size={16}/>View Organization</button>
        <button onClick={onCreate} className="h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-bold flex items-center gap-2 shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca]"><Plus size={16}/>New Department</button>
      </div>
    </div>

    <div className="flex items-center gap-3 mb-6">
      <div className="flex items-center gap-2">
        {TABS.map(([t,c],i)=><button key={t} className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 ${i===0?"bg-[#eef2ff] text-[#4f46e5]":"text-slate-500 hover:bg-slate-50"}`}>{t}{c&&<span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">{c}</span>}</button>)}
      </div>
      <div className="ml-auto flex items-center gap-2">
        <input placeholder="Search departments..." className="h-9 w-44 rounded-lg border border-[#e6ebf2] px-3 text-xs outline-none"/>
        <button className="h-9 px-3 rounded-lg border border-[#e6ebf2] text-xs text-slate-600 flex items-center gap-1.5">All Status <ChevronDown size={13}/></button>
        <button className="h-9 px-3 rounded-lg border border-[#e6ebf2] text-xs text-slate-600 flex items-center gap-1.5">Sort by <ChevronDown size={13}/></button>
      </div>
    </div>

    {/* Org tree — enclosed panel */}
    <div className="relative rounded-2xl border border-[#e6ebf2] bg-white shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-6 mb-5">
      <div className="flex justify-center">
        <div className="rounded-2xl border border-[#c7d2fe] bg-[#eef2ff]/40 px-5 py-3 flex items-center gap-3 shadow-sm">
          <span className="w-11 h-11 rounded-full bg-[#4f46e5] text-white grid place-items-center shadow-sm"><Building2 size={20}/></span>
          <div><p className="text-base font-bold text-slate-800 leading-tight">Orion</p><p className="text-[11px] text-slate-400">Business Operating System</p></div>
        </div>
      </div>
      <svg className="w-full h-9" viewBox="0 0 1000 36" preserveAspectRatio="none" aria-hidden="true">
        <path d="M500 0 V12 M167 24 V12 H833 V24 M500 12 V24" fill="none" stroke="#4f46e5" strokeWidth="1.6"/>
        {[167,500,833].map((x)=>(<g key={x}><path d={`M${x-4} 22 L${x} 28 L${x+4} 22 Z`} fill="#4f46e5"/></g>))}
      </svg>
      <div className="grid grid-cols-3 gap-4 mb-4">{DEPTS.slice(0,3).map(d=><DeptCard key={d.name} d={d} onClick={()=>onDepartmentClick && onDepartmentClick(d.name)}/>)}</div>
      <svg className="w-full h-9 -mt-2" viewBox="0 0 1000 36" preserveAspectRatio="none" aria-hidden="true">
        <path d="M167 0 V12 H833 V0 M167 12 V24 M500 12 V24 M833 12 V24" fill="none" stroke="#4f46e5" strokeWidth="1.6"/>
        {[167,500,833].map((x)=>(<path key={x} d={`M${x-4} 22 L${x} 28 L${x+4} 22 Z`} fill="#4f46e5"/>))}
      </svg>
      <div className="grid grid-cols-3 gap-4">{DEPTS.slice(3).map(d=><DeptCard key={d.name} d={d} onClick={()=>onDepartmentClick && onDepartmentClick(d.name)}/>)}</div>
    </div>

    {/* Table — enclosed panel */}
    <div className="rounded-2xl border border-[#e6ebf2] bg-white shadow-[0_8px_26px_rgba(36,45,64,0.045)] overflow-hidden">
    <table className="w-full text-left">
      <thead><tr className="border-b border-[#e6ebf2] text-[11px] font-semibold text-slate-500">
        <th className="py-3 px-5">Department</th><th className="py-3 px-3">Type</th><th className="py-3 px-3">Lead / Agents</th><th className="py-3 px-3">Active Missions</th><th className="py-3 px-3">Knowledge</th><th className="py-3 px-3">Status</th><th className="py-3 px-3">Last Activity</th>
      </tr></thead>
      <tbody className="divide-y divide-[#eef2f8]">
        {ROWS.map(r=>(
          <tr key={r.name} onClick={()=>onDepartmentClick && onDepartmentClick(r.name)} className="text-xs text-slate-600 hover:bg-slate-50 cursor-pointer">
            <td className="py-3 px-5"><span className="flex items-center gap-2 font-semibold text-slate-800"><r.Icon size={15} className={r.tint}/>{r.name}</span></td>
            <td className="py-3 px-3">{r.custom?<span className="px-2 py-0.5 rounded-full bg-violet-50 text-violet-600 text-[10px] font-semibold">Custom</span>:<span className="text-slate-400">Pre-built</span>}</td>
            <td className="py-3 px-3"><span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded-full bg-slate-200"/> {r.lead}</span></td>
            <td className="py-3 px-3">{r.active}</td>
            <td className="py-3 px-3">{r.know}</td>
            <td className="py-3 px-3"><span className="inline-flex items-center gap-1.5 text-emerald-600 font-medium"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Healthy</span></td>
            <td className="py-3 px-3 text-slate-400">{r.act}</td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  </div>
);
