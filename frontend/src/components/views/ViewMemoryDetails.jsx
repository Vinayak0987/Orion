import {
  ChevronRight, ChevronDown, Plus, Search, List, LayoutGrid, MoreHorizontal,
  ArrowRight, FileText,
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const MEMORIES = [
  { title: "Q3 marketing discussion", type: "Short-term", dept: "Marketing", created: "Sep 15, 2026", used: "Sep 15, 2026" },
  { title: "Product feature ideas", type: "Long-term", dept: "Product", created: "Sep 14, 2026", used: "Sep 15, 2026" },
  { title: "Customer feedback summary", type: "Short-term", dept: "Sales", created: "Sep 13, 2026", used: "Sep 14, 2026", selected: true },
  { title: "HR onboarding process", type: "Department", dept: "HR", created: "Sep 12, 2026", used: "Sep 13, 2026" },
  { title: "Competitor analysis", type: "Long-term", dept: "Research", created: "Sep 10, 2026", used: "Sep 12, 2026" },
  { title: "Financial planning notes", type: "Short-term", dept: "Finance", created: "Sep 08, 2026", used: "Sep 11, 2026" },
];

const Dropdown = ({ label }) => (
  <button className="h-11 px-4 rounded-xl border border-[#e6ebf2] bg-white text-[14px] font-medium text-slate-600 flex items-center gap-6 hover:bg-slate-50">
    {label}
    <ChevronDown size={16} className="text-slate-400" />
  </button>
);

const Check = ({ checked }) => (
  <span className={`w-[18px] h-[18px] rounded-[5px] inline-grid place-items-center ${checked ? "bg-[#4f46e5]" : "border-2 border-slate-300"}`}>
    {checked && (
      <svg viewBox="0 0 24 24" className="w-3 h-3 text-white" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5L20 7" /></svg>
    )}
  </span>
);

export const ViewMemoryDetails = () => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Memory Details" }]} />

    {/* Header */}
    <div className="flex items-start gap-4 mb-7">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="1.7"><rect x="4" y="3" width="16" height="18" rx="2.5"/><path d="M9 3v18" strokeLinecap="round"/><circle cx="14.5" cy="12" r="2.2"/></svg>
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Memory Details</h1>
        <p className="text-[15px] text-slate-500 mt-2">View, edit, delete specific memories</p>
      </div>
      <button className="h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold flex items-center gap-2 shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca]">
        <Plus size={18} strokeWidth={2.5} /> Add Memory
      </button>
    </div>

    {/* Filter bar */}
    <div className="flex items-center gap-3 mb-5">
      <div className="relative flex-1 max-w-[340px]">
        <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          placeholder="Search memories..."
          className="w-full h-11 rounded-xl border border-[#e6ebf2] bg-white pl-10 pr-3 text-[14px] text-slate-700 placeholder:text-slate-400 outline-none focus:border-[#a5b4fc] focus:ring-2 focus:ring-[#eef2ff]"
        />
      </div>
      <Dropdown label="All Types" />
      <Dropdown label="All Departments" />
      <Dropdown label="Latest" />
      <div className="ml-auto flex items-center rounded-xl border border-[#e6ebf2] overflow-hidden">
        <button className="w-11 h-11 grid place-items-center text-slate-500 hover:bg-slate-50"><List size={18} /></button>
        <button className="w-11 h-11 grid place-items-center bg-[#eef2ff] text-[#4f46e5] border-l border-[#e6ebf2]"><LayoutGrid size={18} /></button>
      </div>
    </div>

    {/* Table */}
    <div className="rounded-2xl border border-[#e6ebf2] overflow-hidden shadow-sm">
      <div className="grid grid-cols-[48px_1.6fr_150px_150px_150px_150px_90px] items-center px-5 h-14 bg-slate-50/70 border-b border-[#e6ebf2] text-[14px] font-semibold text-slate-600">
        <span><Check checked={false} /></span>
        <span>Content / Title</span>
        <span>Type</span>
        <span>Department</span>
        <span>Created</span>
        <span>Last Used</span>
        <span>Actions</span>
      </div>
      {MEMORIES.map((m, i) => (
        <div
          key={m.title}
          className={`grid grid-cols-[48px_1.6fr_150px_150px_150px_150px_90px] items-center px-5 h-[68px] cursor-pointer ${
            m.selected ? "bg-[#eef2ff]/70" : "hover:bg-slate-50/60"
          } ${i !== MEMORIES.length - 1 ? "border-b border-slate-100" : ""}`}
        >
          <span><Check checked={m.selected} /></span>
          <span className={`text-[15px] font-semibold ${m.selected ? "text-[#4f46e5]" : "text-slate-800"}`}>{m.title}</span>
          <span className="text-[14px] text-slate-500">{m.type}</span>
          <span className="text-[14px] text-[#4f46e5] font-medium">{m.dept}</span>
          <span className="text-[14px] text-slate-500">{m.created}</span>
          <span className="text-[14px] text-slate-500">{m.used}</span>
          <span>
            <button className="w-9 h-9 grid place-items-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"><MoreHorizontal size={20} /></button>
          </span>
        </div>
      ))}
    </div>

    {/* Pagination */}
    <div className="flex items-center justify-between mt-6 mb-7">
      <p className="text-[14px] text-slate-500">Showing 1–6 of 48 memories</p>
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4].map((p) => (
          <button key={p} className={`w-10 h-10 rounded-lg text-[14px] font-semibold grid place-items-center ${p === 1 ? "bg-[#eef2ff] text-[#4f46e5] border border-[#c7d2fe]" : "text-slate-500 hover:bg-slate-50"}`}>{p}</button>
        ))}
        <button className="w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-50 grid place-items-center"><ArrowRight size={17} /></button>
      </div>
    </div>

    {/* Selected Memory */}
    <div>
      <h2 className="text-[20px] font-bold text-[#0b1220] mb-4">Selected Memory</h2>
      <div className="rounded-2xl border border-[#e6ebf2] shadow-sm p-6">
        <div className="flex items-start gap-4">
          <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0"><FileText size={24} /></span>
          <div className="flex-1">
            <h3 className="text-[20px] font-bold text-[#0b1220]">Customer feedback summary</h3>
            <p className="text-[14px] mt-1 flex items-center gap-2">
              <span className="text-[#4f46e5] font-medium">Short-term</span>
              <span className="text-slate-300">•</span>
              <span className="text-[#4f46e5] font-medium">Sales</span>
              <span className="text-slate-300">•</span>
              <span className="text-slate-400">Sep 13, 2026, 2:30 PM</span>
            </p>
          </div>
          <button className="h-11 px-6 rounded-xl border border-[#e6ebf2] text-[14px] font-semibold text-[#4f46e5] hover:bg-slate-50">Edit</button>
          <button className="w-11 h-11 rounded-xl border border-[#e6ebf2] grid place-items-center text-slate-500 hover:bg-slate-50"><MoreHorizontal size={18} /></button>
        </div>

        <div className="rounded-xl bg-[#eef2ff]/50 border border-[#c7d2fe]/60 p-4 mt-5">
          <p className="text-[15px] text-slate-600 leading-relaxed">
            Users are requesting a simplified onboarding process and better customization options for dashboards.
            Common feedback includes improved mobile experience, faster load times, and more integration options.
          </p>
        </div>

        <div className="flex items-center gap-3 mt-5 pt-5 border-t border-slate-100">
          <span className="text-[14px] font-bold text-[#0b1220]">Tags</span>
          {["feedback", "customers", "product", "ux"].map((t) => (
            <span key={t} className="px-3.5 py-1.5 rounded-lg bg-[#eef2ff] text-[#4f46e5] text-[13px] font-medium">{t}</span>
          ))}
          <button className="px-3.5 py-1.5 rounded-lg border border-[#e6ebf2] text-slate-500 text-[13px] font-medium flex items-center gap-1">
            <Plus size={13} /> Add tag
          </button>
        </div>
      </div>
    </div>
  </div>
);
