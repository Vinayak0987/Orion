import {
  Bot, Building2, ChevronRight, MessageSquare,
  RefreshCw, Send, ShieldCheck, Sparkles, Users, Workflow,
  Cloud, FileText, FolderOpen, MessagesSquare, LayoutGrid, StickyNote
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const agents = ["Customer Support Agent", "Churn Prediction Agent", "Feedback Analysis Agent", "Retention Campaign Agent"];
const missions = ["Analyze existing customer data", "Identify at-risk customers", "Create retention campaigns", "Build customer feedback insights"];

const MiniResource = ({ icon: Icon, color, label }) => (
  <div className="flex items-center gap-2">
    <span className={`w-7 h-7 rounded-lg grid place-items-center ${color}`}><Icon size={14} /></span>
    <span className="text-[11px] text-slate-600">{label}</span>
  </div>
);

export const ViewCreateDepartment = ({ onCreate }) => (
  <div className="h-full flex flex-col min-h-0 bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "Create Department" }]} />
    <div className="flex items-start justify-between mb-5 shrink-0">
      <div>
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Create Department</h1>
        <p className="text-[15px] text-[#64748b] mt-2">Use natural language or guided setup to create a new department.</p>
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span className="font-semibold text-slate-700">Steps</span>
        {[1,2,3].map((n,i)=><div key={n} className="flex items-center gap-2"><span className={`w-6 h-6 rounded-full grid place-items-center font-bold ${n===1?"bg-[#eef2ff] text-[#4f46e5]":"bg-slate-100 text-slate-500"}`}>{n}</span>{i<2&&<span className="w-8 h-px bg-[#a5b4fc]"/>}</div>)}
      </div>
    </div>

    <div className="grid grid-cols-[0.9fr_1.1fr] gap-5 flex-1 min-h-0">
      <section className="rounded-xl border border-[#e6ebf2] bg-white flex flex-col overflow-hidden">
        <div className="p-5 flex-1 overflow-y-auto scrollbar-hide">
          <div className="flex justify-end mb-5">
            <div className="max-w-[82%] rounded-xl rounded-tr-sm bg-[#eef2ff] px-4 py-3 text-sm text-slate-700">
              I want to create a department to handle customer retention and lifecycle marketing.
            </div>
          </div>
          <div className="flex gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0"><Bot size={16}/></div>
            <div>
              <p className="text-xs font-bold text-slate-800">Orion</p>
              <p className="text-sm text-slate-600 mt-1">I’ll help you create a Customer Success department. Here’s what I propose:</p>
            </div>
          </div>

          <div className="ml-11 rounded-xl border border-[#e6ebf2] overflow-hidden">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-100 text-xs font-bold text-slate-800">Proposed Department</div>
            <div className="p-4 space-y-3 text-xs">
              <div className="grid grid-cols-[120px_1fr]"><span className="font-semibold text-slate-500">Name</span><span className="text-slate-700">Customer Success</span></div>
              <div className="grid grid-cols-[120px_1fr]"><span className="font-semibold text-slate-500">Purpose</span><span className="text-slate-700">Improve customer retention, satisfaction and lifecycle value.</span></div>
              <div className="grid grid-cols-[120px_1fr]"><span className="font-semibold text-slate-500">Key Responsibilities</span><ul className="space-y-1 text-slate-700 list-disc pl-4"><li>Maximize customer health</li><li>Nurture onboarding and support</li><li>Identify churn risks</li><li>Drive expansion opportunities</li></ul></div>
              <div className="grid grid-cols-[120px_1fr]"><span className="font-semibold text-slate-500">Suggested Agents</span><div className="space-y-2">{agents.map(a=><div key={a} className="flex items-center gap-2"><Bot size={13} className="text-[#4f46e5]"/>{a}</div>)}</div></div>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-slate-100">
          <div className="rounded-xl border border-[#e6ebf2] p-2.5">
            <div className="relative"><input placeholder="Refine or ask for changes..." className="w-full h-10 rounded-lg border border-[#e6ebf2] pl-3 pr-11 text-xs outline-none focus:ring-2 focus:ring-[#eef2ff]"/><button className="absolute right-1.5 top-1.5 w-7 h-7 rounded-lg bg-[#4f46e5] text-white grid place-items-center"><Send size={13}/></button></div>
            <div className="flex gap-2 mt-2.5"><button className="px-3 py-2 rounded-lg border border-[#e6ebf2] text-xs text-slate-600 flex items-center gap-1.5"><RefreshCw size={13}/>Regenerate</button><button className="px-3 py-2 rounded-lg border border-[#c7d2fe] text-xs text-[#4f46e5] flex items-center gap-1.5"><Sparkles size={13}/>Use Guided Setup</button></div>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-[#e6ebf2] bg-white p-5 flex flex-col overflow-y-auto scrollbar-hide">
        <h2 className="text-sm font-bold text-slate-900 mb-5">Preview: Department Structure</h2>
        <div className="relative h-[250px] shrink-0">
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 600 250" aria-hidden="true">
            <path d="M300 62 V96 M95 96 H505 M95 96 V138 M230 96 V138 M370 96 V138 M505 96 V138" fill="none" stroke="#6d5dfc" strokeWidth="2" strokeLinecap="round"/>
            {[95,230,370,505].map((x)=><path key={x} d={`M${x-5} 132 L${x} 140 L${x+5} 132 Z`} fill="#6d5dfc"/>)}
          </svg>
          <div className="absolute left-1/2 -translate-x-1/2 top-0 w-56 rounded-2xl border border-[#c7d2fe] bg-[#eef2ff]/50 p-3 flex items-center gap-3"><span className="w-11 h-11 rounded-full bg-[#4f46e5] text-white grid place-items-center shrink-0"><Building2 size={19}/></span><div><p className="text-sm font-bold text-slate-800 leading-tight">Customer Success</p><p className="text-[10px] text-slate-400">Department</p></div></div>
          <div className="absolute left-0 right-0 top-[150px] grid grid-cols-4 gap-3">{[
            [MessageSquare,"Support Agent","bg-emerald-50 text-emerald-600"],
            [Workflow,"Churn Prediction Agent","bg-violet-50 text-violet-600"],
            [ShieldCheck,"Feedback Agent","bg-blue-50 text-blue-600"],
            [Users,"Retention Agent","bg-slate-100 text-slate-600"]
          ].map(([I,n,c])=><div key={n} className="text-center"><span className={`mx-auto w-12 h-12 rounded-full grid place-items-center ${c}`}><I size={19}/></span><p className="text-[10px] font-semibold text-slate-700 mt-2 leading-tight">{n}</p></div>)}</div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-3">
          <div className="rounded-xl border border-[#e6ebf2] p-4"><h3 className="text-xs font-bold text-slate-800 mb-3">Tools</h3><div className="grid grid-cols-3 gap-3"><MiniResource icon={MessagesSquare} color="bg-rose-50 text-rose-500" label="Slack"/><MiniResource icon={LayoutGrid} color="bg-blue-50 text-blue-500" label="CRM"/><MiniResource icon={StickyNote} color="bg-slate-50 text-slate-700" label="Notion"/></div><p className="text-[10px] text-slate-400 mt-2">+6</p></div>
          <div className="rounded-xl border border-[#e6ebf2] p-4"><h3 className="text-xs font-bold text-slate-800 mb-3">Knowledge Sources</h3><div className="grid grid-cols-3 gap-3"><MiniResource icon={Cloud} color="bg-blue-50 text-blue-500" label="Drive"/><MiniResource icon={FileText} color="bg-[#eef2ff] text-[#4f46e5]" label="Docs"/><MiniResource icon={FolderOpen} color="bg-violet-50 text-violet-500" label="Files"/></div><p className="text-[10px] text-slate-400 mt-2">+6</p></div>
        </div>
        <div className="rounded-xl border border-[#e6ebf2] p-4 mt-4 flex-1"><h3 className="text-xs font-bold text-slate-800 mb-3">Initial Missions</h3><ol className="space-y-2 text-xs text-slate-600 list-decimal pl-5">{missions.map(m=><li key={m}>{m}</li>)}</ol></div>
        <button onClick={onCreate} className="ml-auto mt-4 px-6 py-3 rounded-xl bg-[#4f46e5] hover:bg-[#4338ca] text-white text-sm font-semibold flex items-center gap-2 shadow-[0_4px_12px_rgba(79,70,229,0.28)]"><Sparkles size={15}/>Create Department <ChevronRight size={15}/></button>
      </section>
    </div>
  </div>
);
