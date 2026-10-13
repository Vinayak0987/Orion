import { FlaskConical, RotateCcw, Save, ChevronDown, ShieldCheck, Users, Wrench, Check } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = ["General","Autonomy","Agents","Tools","Knowledge","Missions","Notifications"];
const APPROVALS = ["High-budget research", "External data access", "Strategic research", "New methodologies"];
const POLICY = [
  { n: "Research", s: "Department", Icon: FlaskConical, tint: "bg-[#eef2ff] text-[#4f46e5]", card: "border-[#eef2ff] bg-[#eef2ff]/60" },
  { n: "Policies & Permissions", s: "", Icon: ShieldCheck, tint: "bg-blue-100 text-blue-600", card: "border-blue-100 bg-blue-50/60" },
  { n: "Agents", s: "(inherit permissions)", Icon: Users, tint: "bg-emerald-100 text-emerald-600", card: "border-emerald-100 bg-emerald-50/60" },
  { n: "Tools & Knowledge", s: "(controlled access)", Icon: Wrench, tint: "bg-orange-100 text-orange-500", card: "border-orange-100 bg-orange-50/60" },
];
const RULES = ["Respects approval rules","Operates within budget","Follows research ethics","Logs all activities"];

const Field = ({ label, children }) => (
  <div className="mb-4"><label className="block text-xs font-semibold text-slate-600 mb-1.5">{label}</label>{children}</div>
);

export const ViewResearchSettings = () => (
  <div className="h-full p-6 overflow-y-auto scrollbar-hide bg-white">
    <DirectoryLocation items={[{ label: "Departments" }, { label: "Research" }, { label: "Settings" }]} />

    <div className="flex items-center gap-3 mb-5">
      <span className="w-11 h-11 rounded-xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center"><FlaskConical size={20} fill="currentColor"/></span>
      <div className="flex-1">
        <div className="flex items-center gap-2.5"><h1 className="text-xl font-extrabold text-[#17143f]">Research Settings</h1><span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-600"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"/>Healthy</span></div>
        <p className="text-xs text-slate-500 mt-0.5">Manage department configuration and behavior.</p>
      </div>
      <button className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 flex items-center gap-1.5"><RotateCcw size={14}/>Reset</button>
      <button className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-200"><Save size={14}/>Save Changes</button>
    </div>

    <div className="flex items-center gap-6 border-b border-slate-200 mb-6">
      {TABS.map((t,i)=><button key={t} className={`pb-3 text-sm font-semibold border-b-2 -mb-px ${i===0?"text-indigo-600 border-indigo-600":"text-slate-500 border-transparent hover:text-slate-700"}`}>{t}</button>)}
    </div>

    <div className="grid grid-cols-3 gap-6">
      {/* Basic Information */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900 mb-4">Basic Information</h2>
        <Field label="Department Name"><input defaultValue="Research" className="w-full h-9 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:ring-2 focus:ring-indigo-100"/></Field>
        <Field label="Description"><textarea rows={3} defaultValue="Drive innovation through data-driven insights, market research and strategic analysis." className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-indigo-100 resize-none"/></Field>
        <Field label="Department Type"><div className="flex items-center gap-5 text-xs text-slate-600"><label className="flex items-center gap-2"><span className="w-4 h-4 rounded-full border-[5px] border-indigo-500"/>Pre-built</label><label className="flex items-center gap-2"><span className="w-4 h-4 rounded-full border border-slate-300"/>Custom</label></div></Field>
        <Field label="Icon & Color"><div className="flex items-center gap-3"><span className="px-3 h-9 rounded-lg bg-[#eef2ff] text-[#4f46e5] text-xs font-semibold inline-flex items-center gap-1.5"><FlaskConical size={13}/>Research</span><div className="flex gap-1.5">{["bg-[#4f46e5]","bg-indigo-400","bg-violet-400","bg-blue-400","bg-cyan-500"].map(c=><span key={c} className={`w-4 h-4 rounded-full ${c}`}/>)}</div></div></Field>
        <Field label="Operating Instructions"><textarea rows={3} placeholder="You are the research department responsible for..." className="w-full rounded-lg border border-slate-200 px-3 py-2 text-xs outline-none focus:ring-2 focus:ring-indigo-100 resize-none"/></Field>
      </section>

      {/* Autonomy & Governance */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900 mb-4">Autonomy &amp; Governance</h2>
        <Field label="Autonomy Level">
          <button className="w-full h-9 rounded-lg border border-slate-200 px-3 text-sm text-slate-700 flex items-center justify-between">Semi-Autonomous <ChevronDown size={15} className="text-slate-400"/></button>
          <p className="text-[10px] text-slate-400 mt-1">Can execute tasks within defined limits</p>
        </Field>
        <Field label="Require Approval For"><div className="space-y-2.5">{APPROVALS.map((a,i)=><label key={a} className="flex items-center gap-2.5 text-xs text-slate-600"><span className={`w-4 h-4 rounded grid place-items-center ${i<2?"bg-indigo-600 text-white":"border border-slate-300"}`}>{i<2&&<Check size={11} strokeWidth={3}/>}</span>{a}</label>)}</div></Field>
        <Field label="Budget & Cost Limits"><p className="text-[10px] text-slate-500 mb-1">Monthly Budget (USD)</p><div className="flex items-center h-9 rounded-lg border border-slate-200 px-3"><span className="text-slate-400 text-sm mr-1">$</span><input defaultValue="6,000" className="flex-1 text-sm outline-none"/></div></Field>
        <Field label="Model Preferences"><p className="text-[10px] text-slate-500 mb-1">Preferred LLM</p><button className="w-full h-9 rounded-lg border border-slate-200 px-3 text-sm text-slate-700 flex items-center justify-between">GPT-4o <ChevronDown size={15} className="text-slate-400"/></button><p className="text-[10px] text-slate-400 mt-1">Used for planning and complex reasoning</p></Field>
        <div><p className="text-xs font-semibold text-slate-600 mb-2">Mission Behavior</p>
          <label className="flex items-center justify-between text-xs text-slate-600 mb-2">Allow self-initiated missions <span className="w-9 h-5 rounded-full bg-slate-200 relative"><span className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white"/></span></label>
          <label className="flex items-center justify-between text-xs text-slate-600">Enable cross-department collaboration <span className="w-9 h-5 rounded-full bg-indigo-600 relative"><span className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-white"/></span></label>
        </div>
      </section>

      {/* Runtime Policy */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900 mb-1">Runtime Policy</h2>
        <p className="text-[11px] text-slate-400 mb-4">How permissions flow in this department</p>
        <div className="rounded-xl bg-slate-50/40 p-3">
          <div className="flex flex-col items-stretch">
            {POLICY.map((p,i)=>(
              <div key={p.n} className="flex flex-col items-stretch">
                <div className={`rounded-xl border p-3.5 flex items-center gap-3 shadow-sm ${p.card}`}>
                  <span className={`w-9 h-9 rounded-xl grid place-items-center shrink-0 ${p.tint}`}><p.Icon size={17}/></span>
                  <div><p className="text-[13px] font-bold text-slate-800 leading-tight">{p.n}</p>{p.s&&<p className="text-[10px] text-slate-400 mt-0.5">{p.s}</p>}</div>
                </div>
                {i<POLICY.length-1&&(
                  <div className="flex flex-col items-center h-6 justify-center">
                    <span className="w-px h-3 bg-slate-300"/>
                    <ChevronDown size={16} className="text-slate-400 -mt-1"/>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="mt-5 space-y-2.5">
          {RULES.map(r=>(
            <div key={r} className="flex items-center gap-2.5 text-[13px] text-slate-600">
              <span className="w-5 h-5 rounded-full bg-emerald-500 grid place-items-center shrink-0"><Check size={12} className="text-white" strokeWidth={3}/></span>
              {r}
            </div>
          ))}
        </div>
      </section>
    </div>
  </div>
);