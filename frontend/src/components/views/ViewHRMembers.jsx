import { UserPlus, Plus, Search, ChevronDown, Bot, Users, Pencil, Ban } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = [["All Members","6"],["Human Members","4"],["AI Agents","2"]];
const MEMBERS = [
  { n: "Sarah Johnson", r: "HR Director", t: "Human", m: 2, on: true, act: "30m ago", human: true },
  { n: "David Lee", r: "HR Manager", t: "Human", m: 2, on: true, act: "1h ago", human: true },
  { n: "Emily Chen", r: "Recruiter", t: "Human", m: 1, on: true, act: "2h ago", human: true },
  { n: "Recruitment Agent", r: "Talent Acquisition", t: "AI Agent", m: 2, on: true, act: "15m ago", sel: true },
  { n: "HR Operations Agent", r: "HR Operations", t: "AI Agent", m: 1, idle: true, act: "1h ago" },
];
const RESP = ["Screen candidates","Manage employee records","Handle benefits administration","Conduct performance reviews"];

export const ViewHRMembers = () => (
  <div className="h-full p-6 overflow-y-auto scrollbar-hide bg-white">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "HR" }, { label: "Members" }]} />

    <div className="flex items-start justify-between mb-5">
      <div><h1 className="text-2xl font-extrabold text-[#17143f] tracking-tight">HR Members</h1><p className="text-xs text-slate-500 mt-1">Manage team members and AI agents.</p></div>
      <div className="flex items-center gap-3"><button className="px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-700 flex items-center gap-2"><UserPlus size={15}/>Invite Member</button><button className="px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-semibold flex items-center gap-2 shadow-md shadow-indigo-200"><Plus size={16}/>Add Member</button></div>
    </div>

    <div className="flex items-center gap-3 mb-4">
      <div className="flex items-center gap-2">{TABS.map(([t,c],i)=><button key={t} className={`px-3.5 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 ${i===0?"bg-indigo-50 text-indigo-600":"text-slate-500 hover:bg-slate-50"}`}>{t}<span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">{c}</span></button>)}</div>
      <div className="ml-auto flex items-center gap-2"><div className="relative"><Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"/><input placeholder="Search members..." className="h-9 w-44 rounded-lg border border-slate-200 pl-8 pr-3 text-xs outline-none"/></div><button className="h-9 px-3 rounded-lg border border-slate-200 text-xs text-slate-600 flex items-center gap-1.5">All Types <ChevronDown size={13}/></button></div>
    </div>

    <div className="grid grid-cols-[1.6fr_1fr] gap-5">
      {/* Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead><tr className="text-[11px] font-semibold text-slate-500 border-b border-slate-200"><th className="py-3 px-4">Name</th><th className="py-3 px-2">Role</th><th className="py-3 px-2">Type</th><th className="py-3 px-2">Active Missions</th><th className="py-3 px-2">Status</th><th className="py-3 px-2">Last Activity</th></tr></thead>
          <tbody className="divide-y divide-slate-100">
            {MEMBERS.map(m=>(
              <tr key={m.n} className={`text-xs ${m.sel?"bg-indigo-50/60":"hover:bg-slate-50"} cursor-pointer`}>
                <td className="py-2.5 px-2"><span className="flex items-center gap-2 font-semibold text-slate-800">{m.human?<span className="w-6 h-6 rounded-full bg-gradient-to-br from-rose-200 to-pink-300"/>:<span className="w-6 h-6 rounded-full bg-violet-100 text-violet-600 grid place-items-center"><Bot size={13}/></span>}{m.n}</span></td>
                <td className="py-2.5 px-2 text-slate-500">{m.r}</td>
                <td className="py-2.5 px-2">{m.human?<span className="text-slate-500">Human</span>:<span className="px-2 py-0.5 rounded-full bg-violet-50 text-violet-600 text-[10px] font-semibold">AI Agent</span>}</td>
                <td className="py-2.5 px-2 text-slate-600">{m.m}</td>
                <td className="py-2.5 px-2">{m.idle?<span className="inline-flex items-center gap-1.5 text-slate-400"><span className="w-1.5 h-1.5 rounded-full bg-slate-300"/>Idle</span>:m.sel?<span className="inline-flex items-center gap-1.5 text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Active</span>:<span className="inline-flex items-center gap-1.5 text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Online</span>}</td>
                <td className="py-2.5 px-2 text-slate-400">{m.act}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Member Details */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm h-max">
        <div className="flex items-center justify-between mb-4"><h2 className="text-sm font-bold text-slate-900">Member Details</h2><span className="text-slate-400 text-lg leading-none">&times;</span></div>
        <div className="flex items-center gap-3 mb-4"><span className="w-12 h-12 rounded-xl bg-violet-100 text-violet-600 grid place-items-center"><Bot size={22}/></span><div><div className="flex items-center gap-2"><h3 className="text-base font-bold text-slate-800">Recruitment Agent</h3></div><span className="text-[10px] font-semibold text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded">AI Agent</span><span className="ml-2 inline-flex items-center gap-1.5 text-[11px] text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Active</span></div></div>
        <div className="flex items-center gap-5 border-b border-slate-200 mb-4 text-xs font-semibold">{["Overview","Permissions","Missions"].map((t,i)=><button key={t} className={`pb-2 border-b-2 -mb-px ${i===0?"text-indigo-600 border-indigo-600":"text-slate-500 border-transparent"}`}>{t}</button>)}</div>
        <div className="space-y-4 text-xs">
          <div><p className="font-bold text-slate-800 mb-1">Role</p><p className="text-slate-500">Talent Acquisition Agent</p></div>
          <div><p className="font-bold text-slate-800 mb-1">Description</p><p className="text-slate-500 leading-relaxed">Handles recruitment, candidate screening and hiring processes.</p></div>
          <div><p className="font-bold text-slate-800 mb-1">Model</p><p className="text-slate-500">GPT-4o</p></div>
          <div><p className="font-bold text-slate-800 mb-2">Responsibilities</p><ul className="space-y-1.5 text-slate-500 list-disc pl-4">{RESP.map(r=><li key={r}>{r}</li>)}</ul></div>
          <div><p className="font-bold text-slate-800 mb-2">Active Missions</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"><span className="text-slate-700">Q4 Hiring Campaign</span><span className="text-[10px] text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded">In Progress</span></div>
              <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"><span className="text-slate-700">Employee Onboarding</span><span className="text-[10px] text-indigo-500 bg-indigo-50 px-1.5 py-0.5 rounded">In Progress</span></div>
            </div>
          </div>
        </div>
        <div className="flex gap-2 mt-5"><button className="flex-1 py-2 rounded-lg bg-indigo-600 text-white text-xs font-semibold flex items-center justify-center gap-1.5"><Pencil size={13}/>Edit</button><button className="flex-1 py-2 rounded-lg bg-rose-50 text-rose-600 text-xs font-semibold flex items-center justify-center gap-1.5"><Ban size={13}/>Disable Agent</button></div>
      </div>
    </div>
  </div>
);