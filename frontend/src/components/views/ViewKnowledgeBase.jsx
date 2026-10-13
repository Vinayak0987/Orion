import {
  FileText, Folder, Plus, Search, ChevronDown, ChevronRight, List, LayoutGrid,
  MoreHorizontal, ArrowRight,
} from "lucide-react";
import { DirectoryLocation } from "../ui/DirectoryLocation.jsx";

const TABS = ["All Documents", "Categories", "Tags", "Access Control"];

const DOCS = [
  { name: "Company Overview", Icon: FileText, folder: false, type: "PDF", dept: "General", updated: "Sep 15, 2026", status: "Active" },
  { name: "Business Strategy 2026", Icon: FileText, folder: false, type: "PDF", dept: "Strategy", updated: "Sep 14, 2026", status: "Active" },
  { name: "Product Documentation", Icon: Folder, folder: true, type: "Folder", dept: "Product", updated: "Sep 12, 2026", status: "Active" },
  { name: "HR Policies", Icon: FileText, folder: false, type: "PDF", dept: "HR", updated: "Sep 10, 2026", status: "Active" },
  { name: "Market Research", Icon: FileText, folder: false, type: "DOC", dept: "Research", updated: "Sep 08, 2026", status: "Review" },
  { name: "Financial Reports", Icon: FileText, folder: false, type: "XLS", dept: "Finance", updated: "Sep 06, 2026", status: "Active" },
];

const StatusBadge = ({ status }) => {
  const map = {
    Active: "bg-emerald-100 text-emerald-700",
    Review: "bg-orange-100 text-orange-600",
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-[12px] font-semibold ${map[status]}`}>
      {status}
    </span>
  );
};

const Dropdown = ({ label }) => (
  <button className="h-11 px-4 rounded-xl border border-[#e6ebf2] bg-white text-[14px] font-medium text-slate-600 flex items-center gap-6 hover:bg-slate-50">
    {label}
    <ChevronDown size={16} className="text-slate-400" />
  </button>
);

export const ViewKnowledgeBase = ({ onOpenDoc, onUpload }) => (
  <div className="h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <DirectoryLocation items={[{ label: "Knowledge & Memory" }, { label: "Knowledge Base" }]} />

    {/* Header */}
    <div className="flex items-start gap-4 mb-7">
      <span className="w-14 h-14 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
        <FileText size={26} />
      </span>
      <div className="flex-1 pt-0.5">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">Knowledge Base</h1>
        <p className="text-[15px] text-slate-500 mt-2">Company documents, files, and data sources</p>
      </div>
      <button
        onClick={onUpload}
        className="h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold flex items-center gap-2 shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca]"
      >
        <Plus size={18} strokeWidth={2.5} />
        Add Document
      </button>
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-8 border-b border-[#e6ebf2] mb-6">
      {TABS.map((t, i) => (
        <button
          key={t}
          className={`pb-3.5 text-[15px] font-semibold border-b-2 -mb-px transition-colors ${
            i === 0 ? "text-[#4f46e5] border-[#4f46e5]" : "text-[#64748b] border-transparent hover:text-[#4f46e5]"
          }`}
        >
          {t}
        </button>
      ))}
    </div>

    {/* Filter bar */}
    <div className="flex items-center gap-3 mb-5">
      <div className="relative flex-1 max-w-[340px]">
        <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          placeholder="Search documents..."
          className="w-full h-11 rounded-xl border border-[#e6ebf2] bg-white pl-10 pr-3 text-[14px] text-slate-700 placeholder:text-slate-400 outline-none focus:border-[#a5b4fc] focus:ring-2 focus:ring-[#eef2ff]"
        />
      </div>
      <Dropdown label="All Types" />
      <Dropdown label="All Departments" />
      <Dropdown label="Latest" />
      <div className="ml-auto flex items-center rounded-xl border border-[#e6ebf2] overflow-hidden">
        <button className="w-11 h-11 grid place-items-center text-slate-500 hover:bg-slate-50">
          <List size={18} />
        </button>
        <button className="w-11 h-11 grid place-items-center bg-[#eef2ff] text-[#4f46e5] border-l border-[#e6ebf2]">
          <LayoutGrid size={18} />
        </button>
      </div>
    </div>

    {/* Table */}
    <div className="rounded-2xl border border-[#e6ebf2] overflow-hidden shadow-sm">
      {/* Head */}
      <div className="grid grid-cols-[48px_1fr_120px_150px_150px_130px_90px] items-center px-5 h-14 bg-slate-50/70 border-b border-[#e6ebf2] text-[14px] font-semibold text-slate-600">
        <span><span className="w-[18px] h-[18px] rounded-[5px] border-2 border-slate-300 inline-block" /></span>
        <span>Name</span>
        <span>Type</span>
        <span>Department</span>
        <span>Updated</span>
        <span>Status</span>
        <span>Actions</span>
      </div>
      {/* Rows */}
      {DOCS.map((d, i) => (
        <div
          key={d.name}
          onClick={onOpenDoc}
          className={`grid grid-cols-[48px_1fr_120px_150px_150px_130px_90px] items-center px-5 h-[74px] cursor-pointer hover:bg-slate-50/60 ${
            i !== DOCS.length - 1 ? "border-b border-slate-100" : ""
          }`}
        >
          <span onClick={(e) => e.stopPropagation()}>
            <span className="w-[18px] h-[18px] rounded-[5px] border-2 border-slate-300 inline-block" />
          </span>
          <span className="flex items-center gap-3">
            <span className={`${d.folder ? "text-[#0b1220]" : "text-slate-700"}`}>
              <d.Icon size={20} fill={d.folder ? "currentColor" : "none"} />
            </span>
            <span className="text-[15px] font-semibold text-slate-800">{d.name}</span>
          </span>
          <span className="text-[14px] text-slate-500">{d.type}</span>
          <span className="text-[14px] text-[#4f46e5] font-medium">{d.dept}</span>
          <span className="text-[14px] text-slate-500">{d.updated}</span>
          <span><StatusBadge status={d.status} /></span>
          <span onClick={(e) => e.stopPropagation()}>
            <button className="w-9 h-9 grid place-items-center text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
              <MoreHorizontal size={20} />
            </button>
          </span>
        </div>
      ))}
    </div>

    {/* Pagination */}
    <div className="flex items-center justify-between mt-6 mb-2">
      <p className="text-[14px] text-slate-500">Showing 1–6 of 24 documents</p>
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4].map((p) => (
          <button
            key={p}
            className={`w-10 h-10 rounded-lg text-[14px] font-semibold grid place-items-center ${
              p === 1 ? "bg-[#eef2ff] text-[#4f46e5] border border-[#c7d2fe]" : "text-slate-500 hover:bg-slate-50"
            }`}
          >
            {p}
          </button>
        ))}
        <button className="w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-50 grid place-items-center">
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  </div>
);
