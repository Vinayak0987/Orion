import {
  Plus,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  User,
  Sparkles,
  BarChart3,
  Rocket,
} from "lucide-react";

const TABS = ["All (12)", "Research (4)", "Planning (2)", "Operations (3)", "Completed (2)"];
const FILTERS = ["Status", "Priority", "Department", "Owner", "Date"];

// Type pill colors
const TYPE_STYLES = {
  Planning: "text-blue-600 bg-blue-50",
  Research: "text-amber-600 bg-amber-50",
  Operations: "text-emerald-600 bg-emerald-50",
};

// Status pill colors
const STATUS_STYLES = {
  "In Progress": "text-blue-600 bg-blue-50",
  Completed: "text-emerald-600 bg-emerald-50",
  "Not Started": "text-slate-500 bg-slate-100",
};

const ROWS = [
  { id: 1, title: "Expand to New City (Thane)", desc: "Research and execution plan", type: "Planning", agents: 2, extra: "+3", prog: 70, status: "In Progress", time: "2 hours ago", active: true },
  { id: 2, title: "Grocery Recommendation System", desc: "Build and deploy ML model", type: "Research", agents: 2, extra: "+2", prog: 45, status: "In Progress", time: "5 hours ago" },
  { id: 3, title: "Competitor Analysis", desc: "Analyze top 5 competitors", type: "Research", agents: 2, extra: "+1", prog: 100, status: "Completed", time: "1 day ago" },
  { id: 4, title: "User Research Study", desc: "Customer behaviour analysis", type: "Research", agents: 2, extra: "+2", prog: 60, status: "In Progress", time: "2 days ago" },
  { id: 5, title: "Funding Strategy", desc: "Investor outreach and deck", type: "Planning", agents: 2, extra: "+2", prog: 35, status: "In Progress", time: "3 days ago" },
  { id: 6, title: "Operations Optimization", desc: "Improve internal workflows", type: "Operations", agents: 2, extra: "+1", prog: 20, status: "Not Started", time: "4 days ago" },
  { id: 7, title: "Brand Positioning", desc: "Develop new brand strategy", type: "Planning", agents: 2, extra: "+2", prog: 100, status: "Completed", time: "5 days ago" },
  { id: 8, title: "Market Entry - Pune", desc: "Research and go-to-market plan", type: "Planning", agents: 2, extra: "+2", prog: 0, status: "Not Started", time: "6 days ago" },
];

const PIPELINE = [
  { name: "Research", tasks: "3 tasks", LucideIcon: Sparkles, iconColors: "text-[#4f46e5] bg-[#eef2ff]", arrow: "text-slate-300" },
  { name: "Analysis", tasks: "4 tasks", LucideIcon: BarChart3, iconColors: "text-blue-600 bg-blue-100", arrow: "text-emerald-400" },
  { name: "Execution", tasks: "3 tasks", LucideIcon: Rocket, iconColors: "text-emerald-600 bg-emerald-100" },
];

const AgentAvatars = ({ extra }) => (
  <div className="flex items-center -space-x-2">
    <div className="w-7 h-7 rounded-full bg-blue-100 border-2 border-white flex items-center justify-center z-20">
      <User size={13} className="text-blue-600" strokeWidth={2.4} />
    </div>
    <div className="w-7 h-7 rounded-full bg-rose-100 border-2 border-white flex items-center justify-center z-10">
      <User size={13} className="text-rose-500" strokeWidth={2.4} />
    </div>
    <div className="w-7 h-7 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[10px] font-bold text-slate-500 z-0">
      {extra}
    </div>
  </div>
);

export const ViewMissions = ({ onViewDetails }) => (
  <div className="p-6 sm:p-7 max-w-[1400px] mx-auto h-full flex flex-col bg-[#f8fafc]">
    {/* Header */}
    <div className="flex justify-between items-start mb-6 shrink-0">
      <div>
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220] mb-2">Missions</h1>
        <p className="text-[15px] text-[#64748b]">Plan, track, and manage all your missions.</p>
      </div>
      <button className="bg-[#4f46e5] hover:bg-[#4338ca] text-white font-bold h-12 px-5 rounded-xl text-[15px] transition-colors shadow-[0_4px_12px_rgba(79,70,229,0.28)] whitespace-nowrap flex items-center gap-2">
        <Plus size={18} strokeWidth={2.5} /> New Mission
      </button>
    </div>

    <div className="flex-1 flex flex-col min-h-0">
      {/* Tabs + search */}
      <div className="flex items-center gap-3 mb-4 shrink-0">
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
          {TABS.map((tab, i) => (
            <button
              key={i}
              className={`px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap transition-colors ${
                i === 0
                  ? "text-[#4f46e5] bg-[#eef2ff] border-b-2 border-[#4f46e5] rounded-b-none"
                  : "text-slate-500 bg-slate-50 hover:bg-slate-100"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="ml-auto relative w-64 shrink-0">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input type="text" placeholder="Search missions..." className="w-full bg-white border border-[#e6ebf2] rounded-lg py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:border-[#a5b4fc] focus:ring-1 focus:ring-[#c7d2fe] shadow-sm" />
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4 shrink-0">
        {FILTERS.map((f, i) => (
          <button key={i} className="bg-white border border-[#e6ebf2] rounded-lg px-4 py-2 text-sm font-medium text-slate-600 flex items-center gap-2 shadow-sm hover:bg-slate-50">
            {f} <ChevronDown size={14} className="text-slate-400" />
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#e6ebf2]">
              <th className="py-3 px-4 text-sm font-semibold text-slate-500 w-12">#</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500">Mission / Objective</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500">Type</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500">Agents</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500 w-40">Progress</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500">Status</th>
              <th className="py-3 px-4 text-sm font-semibold text-slate-500 text-right">Last Activity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ROWS.map((row) => (
              <tr
                key={row.id}
                onClick={() => row.id === 1 && onViewDetails()}
                className={`group cursor-pointer transition-colors ${row.active ? "bg-[#eef2ff]/40" : "hover:bg-slate-50"}`}
              >
                <td className="py-4 px-4 text-sm text-slate-400 font-medium">{row.id}</td>
                <td className="py-4 px-4">
                  <h4 className="text-sm font-bold text-slate-800">{row.title}</h4>
                  <p className="text-xs mt-0.5 text-slate-400">{row.desc}</p>
                </td>
                <td className="py-4 px-4">
                  <span className={`inline-block px-3 py-1 rounded-md text-xs font-semibold ${TYPE_STYLES[row.type]}`}>{row.type}</span>
                </td>
                <td className="py-4 px-4">
                  <AgentAvatars extra={row.extra} />
                </td>
                <td className="py-4 px-4">
                  <div className="flex items-center gap-2.5">
                    <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div className={`h-2 rounded-full ${row.prog === 100 ? "bg-blue-500" : "bg-[#4f46e5]"}`} style={{ width: `${row.prog}%` }}></div>
                    </div>
                    <span className="text-xs font-bold text-slate-600 w-9 text-right">{row.prog}%</span>
                  </div>
                </td>
                <td className="py-4 px-4">
                  <span className={`inline-block px-3 py-1.5 rounded-lg text-xs font-semibold ${STATUS_STYLES[row.status]}`}>{row.status}</span>
                </td>
                <td className="py-4 px-4 text-right text-sm font-medium text-slate-400 whitespace-nowrap">{row.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center py-4 shrink-0 text-sm text-slate-500 font-medium">
        <span>Showing 1-8 of 12 missions</span>
        <div className="flex items-center gap-2">
          <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] flex items-center justify-center hover:bg-slate-50 text-slate-400"><ChevronLeft size={16} /></button>
          <button className="w-9 h-9 rounded-lg bg-[#eef2ff] text-[#4f46e5] font-bold flex items-center justify-center">1</button>
          <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] bg-white hover:bg-slate-50 flex items-center justify-center text-slate-600">2</button>
          <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] bg-white hover:bg-slate-50 flex items-center justify-center text-slate-600">3</button>
          <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] flex items-center justify-center hover:bg-slate-50 text-slate-400"><ChevronRight size={16} /></button>
        </div>
      </div>

      {/* Selected Mission Preview */}
      <div className="bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-5 shrink-0">
        <h4 className="text-base font-bold text-slate-800 mb-4">Selected Mission Preview</h4>
        <div className="flex items-center gap-3">
          {/* Orion tile */}
          <div className="flex items-center gap-3 bg-[#eef2ff]/60 rounded-xl px-4 py-3 border border-[#c7d2fe]">
            <div className="w-9 h-9 rounded-lg bg-[#4f46e5] text-white flex items-center justify-center">
              <Sparkles size={18} strokeWidth={2.2} />
            </div>
            <span className="font-bold text-slate-800">Orion</span>
          </div>

          {/* Pipeline */}
          {PIPELINE.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="flex items-center gap-2.5 flex-col">
                <div className="flex items-center gap-2.5 bg-white rounded-xl px-4 py-2.5 border border-[#e6ebf2]">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${step.iconColors}`}>
                    <step.LucideIcon size={16} strokeWidth={2.2} />
                  </div>
                  <span className="text-sm font-semibold text-slate-700">{step.name}</span>
                </div>
                <span className="text-xs text-slate-400">{step.tasks}</span>
              </div>
              {i < PIPELINE.length - 1 && <ChevronRight size={20} className={step.arrow} strokeWidth={2.5} />}
            </div>
          ))}

          <button className="ml-auto w-9 h-9 rounded-full border border-[#e6ebf2] text-slate-400 flex items-center justify-center hover:bg-slate-50" onClick={onViewDetails}>
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </div>
  </div>
);
