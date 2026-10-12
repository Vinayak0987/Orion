import {
  BellRing,
  LineChart,
  TriangleAlert,
  CircleCheck,
  FileText,
  FileWarning,
  Target,
  CircleAlert,
  ArrowRight,
} from "lucide-react";

const TABS = ["All (20)", "Missions (8)", "Approvals (5)", "Agents (4)", "System (3)"];

const NOTIFS = [
  { title: "Mission Update", desc: '"Expand to New City" progress updated to 70%', time: "2 hours ago", LucideIcon: LineChart, color: "text-blue-600 bg-blue-100", active: true },
  { title: "Approval Required", desc: "Marketing budget approval requested", time: "4 hours ago", LucideIcon: TriangleAlert, color: "text-rose-500 bg-rose-100" },
  { title: "Agent Activity", desc: "Research Agent completed data collection", time: "6 hours ago", LucideIcon: CircleCheck, color: "text-emerald-600 bg-emerald-100" },
  { title: "New Subtask Generated", desc: "Competitor deep-dive task created", time: "8 hours ago", LucideIcon: FileText, color: "text-blue-600 bg-blue-100" },
  { title: "Evidence Found", desc: "12 new documents added to knowledge base", time: "12 hours ago", LucideIcon: FileWarning, color: "text-rose-500 bg-rose-100" },
  { title: "Mission Completed", desc: "Brand Positioning analysis has been completed", time: "1 day ago", LucideIcon: CircleCheck, color: "text-emerald-600 bg-emerald-100" },
  { title: "System Update", desc: "New integration available: Shopify", time: "2 days ago", LucideIcon: Target, color: "text-blue-600 bg-blue-100" },
  { title: "Approval Approved", desc: "Hiring request for Data Analyst approved", time: "3 days ago", LucideIcon: CircleCheck, color: "text-emerald-600 bg-emerald-100" },
  { title: "Agent Error (Recovered)", desc: "Web scraping task failed, auto-retry successful", time: "3 days ago", LucideIcon: TriangleAlert, color: "text-amber-500 bg-amber-100" },
  { title: "Weekly Summary", desc: "Your weekly activity report is ready", time: "1 week ago", LucideIcon: CircleAlert, color: "text-rose-500 bg-rose-100" },
];

const TASKS = [
  { label: "Market Research", per: 100, dot: "bg-emerald-500", bar: "bg-emerald-500" },
  { label: "Competitor Analysis", per: 80, dot: "bg-blue-500", bar: "bg-blue-500" },
  { label: "Financial Analysis", per: 50, dot: "bg-[#4f46e5]", bar: "bg-[#4f46e5]" },
  { label: "Execution Planning", per: 0, dot: "bg-amber-500", bar: "bg-slate-200" },
];

const META = [
  { label: "Mission:", value: "Expand to New City (Thane)" },
  { label: "Status:", value: "In Progress", pill: true },
  { label: "Progress:", value: "70%" },
  { label: "Updated by:", value: "Orion System" },
];

export const ViewNotifications = () => (
  <div className="h-full flex flex-col p-6 sm:p-7 max-w-[1400px] mx-auto min-h-0 bg-[#f8fafc]">
    {/* Header */}
    <div className="flex justify-between items-start mb-6 shrink-0">
      <div>
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220] mb-2">Notifications</h1>
        <p className="text-[15px] text-[#64748b]">Stay updated with your missions and system activity.</p>
      </div>
      <button className="bg-[#4f46e5] hover:bg-[#4338ca] text-white font-bold h-12 px-5 rounded-xl text-[15px] transition-colors shadow-md whitespace-nowrap flex items-center gap-2">
        <BellRing size={16} strokeWidth={2.2} /> Mark all as read
      </button>
    </div>

    {/* Tabs */}
    <div className="flex items-center gap-2 mb-5 shrink-0 overflow-x-auto scrollbar-hide">
      {TABS.map((tab, i) => (
        <button key={i} className={`px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap transition-colors ${i === 0 ? "text-[#4f46e5] bg-[#eef2ff] border-b-2 border-[#4f46e5] rounded-b-none" : "text-slate-500 bg-slate-50 hover:bg-slate-100"}`}>
          {tab}
        </button>
      ))}
    </div>

    <div className="flex-1 flex gap-6 min-h-0">
      {/* List Column */}
      <div className="flex-1 flex flex-col shrink-0 bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] overflow-y-auto scrollbar-hide divide-y divide-[#eef2f8]">
        {NOTIFS.map((n, i) => (
          <div key={i} className={`p-4 flex items-center gap-3.5 cursor-pointer transition-colors ${n.active ? "bg-[#eef2ff]/50" : "hover:bg-slate-50"}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${n.color}`}>
              <n.LucideIcon size={19} strokeWidth={2} />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-bold text-slate-800">{n.title}</h4>
              <p className="text-sm text-slate-500 truncate">{n.desc}</p>
            </div>
            <span className="text-xs font-medium text-slate-400 whitespace-nowrap">{n.time}</span>
          </div>
        ))}
      </div>

      {/* Detail Column */}
      <div className="w-[420px] flex flex-col shrink-0 bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] p-6 overflow-y-auto scrollbar-hide">
        <h2 className="text-lg font-bold text-slate-900 mb-5">Notification Details</h2>

        <div className="flex items-start gap-3 mb-4">
          <div className="w-11 h-11 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
            <LineChart size={20} strokeWidth={2} />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-slate-800">Mission Update</h3>
            <p className="text-xs text-slate-400">2 hours ago</p>
          </div>
          <button className="text-xs font-semibold text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-[#e6ebf2] hover:bg-slate-100">Mark as unread</button>
        </div>

        <p className="text-sm text-slate-600 font-medium mb-5">"Expand to New City" progress updated to 70%</p>

        <div className="space-y-2.5 mb-6">
          {META.map((m, i) => (
            <div key={i} className="flex items-center text-sm">
              <span className="w-28 font-semibold text-slate-500">{m.label}</span>
              {m.pill ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold text-blue-600 bg-blue-100">{m.value}</span>
              ) : (
                <span className="font-semibold text-slate-800">{m.value}</span>
              )}
            </div>
          ))}
        </div>

        <div className="border-t border-slate-100 pt-5 mb-5">
          <h4 className="text-sm font-bold text-slate-800 mb-2">Details</h4>
          <p className="text-sm text-slate-500 leading-relaxed">
            The mission has made significant progress. Market research and competitor analysis phases are 80% complete. Financial analysis is in progress.
          </p>
        </div>

        <div className="space-y-3 mb-6">
          {TASKS.map((t, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className={`w-2 h-2 rounded-full shrink-0 ${t.dot}`}></span>
              <span className="text-sm text-slate-600 w-36 shrink-0">{t.label}</span>
              <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                <div className={`h-2 rounded-full ${t.bar}`} style={{ width: `${t.per}%` }}></div>
              </div>
              <span className="text-xs font-bold text-slate-600 w-9 text-right">{t.per}%</span>
            </div>
          ))}
        </div>

        <button className="mt-auto w-full py-3 bg-[#eef2ff] text-[#4f46e5] font-bold rounded-xl text-sm hover:bg-[#eef2ff] transition-colors flex items-center justify-center gap-2">
          View Mission <ArrowRight size={16} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  </div>
);
