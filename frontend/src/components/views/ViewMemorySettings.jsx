import { ChevronRight, ChevronDown } from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = ["General", "Retention", "Privacy", "Access Control", "Advanced"];

const Toggle = ({ on }) => (
  <span className={`w-12 h-7 rounded-full relative transition-colors shrink-0 ${on ? "bg-[#4f46e5]" : "bg-slate-300"}`}>
    <span className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow transition-all ${on ? "right-1" : "left-1"}`} />
  </span>
);

const ToggleRow = ({ title, sub, on, last }) => (
  <div className={`flex items-start justify-between py-4 ${!last ? "border-b border-slate-100" : ""}`}>
    <div>
      <p className="text-[15px] font-bold text-[#0b1220]">{title}</p>
      <p className="text-[13px] text-slate-400 mt-0.5">{sub}</p>
    </div>
    <Toggle on={on} />
  </div>
);

const SelectField = ({ label, value }) => (
  <div>
    <label className="block text-[15px] font-bold text-[#0b1220] mb-2">{label}</label>
    <button className="w-full h-12 rounded-xl border border-[#e6ebf2] px-4 text-[15px] text-slate-700 flex items-center justify-between hover:bg-slate-50">
      {value} <ChevronDown size={17} className="text-slate-400" />
    </button>
  </div>
);

export const ViewMemorySettings = () => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Memory Settings" }]} />

    {/* Header */}
    <div className="flex items-start gap-4 mb-7">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="3" width="16" height="18" rx="2.5"/><path d="M9 3v18" strokeLinecap="round"/><circle cx="14.5" cy="12" r="2.2"/></svg>
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Memory Settings</h1>
        <p className="text-[15px] text-slate-500 mt-2">Retention, privacy, and usage controls</p>
      </div>
      <button className="h-12 px-6 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca]">
        Save Changes
      </button>
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-8 border-b border-[#e6ebf2] mb-7">
      {TABS.map((t, i) => (
        <button key={t} className={`pb-3.5 text-[15px] font-semibold border-b-2 -mb-px ${i === 0 ? "text-[#4f46e5] border-[#4f46e5]" : "text-slate-500 border-transparent hover:text-slate-700"}`}>{t}</button>
      ))}
    </div>

    {/* 2x2 grid */}
    <div className="grid grid-cols-2 gap-6">
      {/* General Settings */}
      <section className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <h2 className="text-[19px] font-bold text-[#0b1220] mb-2">General Settings</h2>
        <ToggleRow title="Enable Memory" sub="Allow Orion to store and use memories" on />
        <ToggleRow title="Auto-categorize" sub="Automatically categorize memories using AI" on />
        <ToggleRow title="Link related memories" sub="Find and connect related information" on last />
        <div className="pt-5">
          <SelectField label="Default memory type" value="Short-term" />
          <p className="text-[13px] text-slate-400 mt-2">Type used when adding memories manually</p>
        </div>
      </section>

      {/* Memory Limits */}
      <section className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <h2 className="text-[19px] font-bold text-[#0b1220] mb-5">Memory Limits</h2>
        <div className="mb-5">
          <div className="flex items-center justify-between gap-4">
            <label className="text-[15px] font-bold text-[#0b1220]">Maximum storage</label>
            <div className="flex items-center gap-2">
              <input defaultValue="10000" className="w-40 h-11 rounded-xl border border-[#e6ebf2] px-4 text-[15px] text-slate-700 outline-none focus:ring-2 focus:ring-[#eef2ff]" />
              <span className="text-[15px] text-slate-500">memories</span>
            </div>
          </div>
          <p className="text-[13px] text-slate-400 mt-2">Set the maximum number of memories to store</p>
        </div>
        <div className="mb-5">
          <div className="flex items-center justify-between gap-4">
            <label className="text-[15px] font-bold text-[#0b1220]">Auto-archive after</label>
            <button className="w-56 h-11 rounded-xl border border-[#e6ebf2] px-4 text-[15px] text-slate-700 flex items-center justify-between hover:bg-slate-50">
              90 days <ChevronDown size={16} className="text-slate-400" />
            </button>
          </div>
          <p className="text-[13px] text-slate-400 mt-2">Move old memories to archive</p>
        </div>
        <div>
          <div className="flex items-center justify-between gap-4">
            <label className="text-[15px] font-bold text-[#0b1220]">Cleanup frequency</label>
            <button className="w-56 h-11 rounded-xl border border-[#e6ebf2] px-4 text-[15px] text-slate-700 flex items-center justify-between hover:bg-slate-50">
              Weekly <ChevronDown size={16} className="text-slate-400" />
            </button>
          </div>
          <p className="text-[13px] text-slate-400 mt-2">Automatically remove expired memories</p>
        </div>
      </section>

      {/* Privacy & Access */}
      <section className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <h2 className="text-[19px] font-bold text-[#0b1220] mb-5">Privacy &amp; Access</h2>
        <div className="mb-5">
          <SelectField label="Data visibility" value="Workspace only" />
          <p className="text-[13px] text-slate-400 mt-2">Control who can access memories</p>
        </div>
        <div className="flex items-start justify-between pt-2">
          <div>
            <p className="text-[15px] font-bold text-[#0b1220]">Allow AI training</p>
            <p className="text-[13px] text-slate-400 mt-0.5">Use anonymised memories to improve AI</p>
          </div>
          <Toggle on={false} />
        </div>
      </section>

      {/* Danger Zone */}
      <section className="rounded-2xl border border-rose-200 bg-rose-50/60 shadow-sm p-6">
        <h2 className="text-[19px] font-bold text-rose-600 mb-5">Danger Zone</h2>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[16px] font-bold text-rose-600">Clear All Memories</p>
            <p className="text-[14px] text-slate-500 mt-1 max-w-[300px]">This will permanently delete all memories. This action cannot be undone.</p>
          </div>
          <button className="h-11 px-6 rounded-xl border-2 border-rose-400 text-rose-600 text-[15px] font-semibold hover:bg-rose-100 shrink-0">
            Clear All
          </button>
        </div>
      </section>
    </div>
  </div>
);
