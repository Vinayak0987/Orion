import {
  Search,
  Filter,
  ChevronDown,
  User,
  FileText,
  UsersRound,
  Megaphone,
  Briefcase,
  CircleAlert,
} from "lucide-react";

const TABS = ["Pending (5)", "Approved (12)", "Rejected (2)", "All (19)"];

// priority pill styles
const PRIORITY = {
  High: "text-rose-600 bg-rose-100",
  Medium: "text-amber-600 bg-amber-100",
  Low: "text-emerald-600 bg-emerald-100",
};

const REQUESTS = [
  { title: "Marketing Budget Approval", agent: "Marketing Agent", desc: "Q4 2026 campaign for Thane launch", badge: "High", active: true, LucideIcon: FileText, iconColors: "text-violet-600 bg-violet-100" },
  { title: "Hire Data Analyst Agent", agent: "HR Agent", desc: "New team member for market research", badge: "Medium", LucideIcon: UsersRound, iconColors: "text-violet-600 bg-violet-100" },
  { title: "Tool Access Request", agent: "Research Agent", desc: "Web scraping for competitor analysis", badge: "Medium", LucideIcon: FileText, iconColors: "text-blue-600 bg-blue-100" },
  { title: "Content Strategy Plan", agent: "Content Agent", desc: "Blog and social media for launch", badge: "Low", LucideIcon: FileText, iconColors: "text-violet-600 bg-violet-100" },
  { title: "Partnership Agreement", agent: "Business Agent", desc: "Collaboration with local suppliers", badge: "High", LucideIcon: Briefcase, iconColors: "text-violet-600 bg-violet-100" },
];

const BUDGET = [
  { label: "Digital Advertising", amount: "₹1,00,000" },
  { label: "Local Print & Outdoor", amount: "₹75,000" },
  { label: "Influencer Partnerships", amount: "₹50,000" },
  { label: "Content Creation", amount: "₹25,000" },
];

const IMPACT = [
  "Increase brand awareness in Thane by 60%",
  "Drive 2,000+ footfall at first month",
  "Est. 1.5X higher revenue in first quarter",
];

const FILES = [
  { name: "marketing_plan.pdf", tag: "PDF", tagColor: "bg-rose-500", size: "2.4 MB" },
  { name: "competitor_benchmarks.xlsx", tag: "XLS", tagColor: "bg-emerald-500", size: "1.1 MB" },
  { name: "roi_projection.pdf", tag: "PDF", tagColor: "bg-rose-500", size: "800 KB" },
];

export const ViewApprovals = () => (
  <div className="h-full flex flex-col p-6 sm:p-7 max-w-[1400px] mx-auto min-h-0 bg-[#f8fafc]">
    {/* Header */}
    <div className="mb-6 shrink-0">
      <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220] mb-2">Approvals</h1>
      <p className="text-[15px] text-[#64748b]">Review and manage action requests from your AI agents.</p>
    </div>

    {/* Tabs + search + filter */}
    <div className="flex items-center gap-3 mb-5 shrink-0">
      <div className="flex items-center gap-2">
        {TABS.map((tab, i) => (
          <button key={i} className={`px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap transition-colors ${i === 0 ? "bg-[#eef2ff] text-[#4f46e5]" : "text-slate-500 bg-slate-50 hover:bg-slate-100"}`}>
            {tab}
          </button>
        ))}
      </div>
      <div className="ml-auto relative w-72">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input type="text" placeholder="Search requests..." className="w-full bg-white border border-[#e6ebf2] rounded-lg py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:border-[#a5b4fc] focus:ring-1 focus:ring-[#c7d2fe] shadow-sm" />
      </div>
      <button className="bg-white border border-[#e6ebf2] rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 flex items-center gap-2 shadow-sm hover:bg-slate-50 shrink-0">
        <Filter size={15} /> Filter <ChevronDown size={14} className="text-slate-400" />
      </button>
    </div>

    <div className="flex-1 flex gap-6 min-h-0">
      {/* List Column */}
      <div className="w-[440px] flex flex-col shrink-0 overflow-y-auto scrollbar-hide gap-3 pr-1">
        {REQUESTS.map((item, i) => (
          <div key={i} className={`p-4 rounded-2xl cursor-pointer transition-all border ${item.active ? "border-[#a5b4fc] bg-[#eef2ff]/50 shadow-sm" : "border-[#e6ebf2] bg-white hover:border-[#c7d2fe]"}`}>
            <div className="flex items-start gap-3">
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${item.iconColors}`}>
                <item.LucideIcon size={20} strokeWidth={2} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-[15px] font-bold text-slate-800">{item.title}</h4>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold shrink-0 ${PRIORITY[item.badge]}`}>{item.badge}</span>
                </div>
                <p className="text-xs text-slate-500 font-medium flex items-center gap-1.5 mt-1">
                  <User size={13} className="text-slate-400" /> {item.agent}
                </p>
                <p className="text-sm text-slate-500 mt-1.5">{item.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Column */}
      <div className="flex-1 flex flex-col overflow-hidden bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
        <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          {/* Detail header */}
          <div className="flex justify-between items-start mb-6">
            <h2 className="text-xl font-bold text-slate-900">Approval Details</h2>
            <div className="flex items-center gap-1.5 text-rose-600 bg-rose-100 px-3 py-1.5 rounded-full text-xs font-bold">
              <CircleAlert size={14} /> High Priority
            </div>
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-full bg-violet-100 text-violet-600 flex items-center justify-center shrink-0">
              <Megaphone size={22} strokeWidth={2} />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-800">Marketing Budget Approval</h4>
              <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5"><User size={13} className="text-slate-400" /> Marketing Agent</p>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">&#128337; 2 hours ago</p>
            </div>
          </div>

          {/* Business Context */}
          <section className="mb-6">
            <h3 className="text-base font-bold text-slate-800 mb-2">Business Context</h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Requesting approval for Q4 2026 marketing campaign to launch Thane café. This includes digital marketing, local advertising, and influencer partnerships.
            </p>
          </section>

          {/* Proposed Action */}
          <section className="mb-6">
            <h3 className="text-base font-bold text-slate-800 mb-2">Proposed Action</h3>
            <p className="text-sm text-slate-500 mb-3">Allocate ₹3,50,000 for Q4 marketing campaign</p>
            <div className="bg-[#f8fafc] rounded-xl border border-[#e6ebf2] divide-y divide-[#eef2f8]">
              {BUDGET.map((b, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-2.5">
                  <span className="text-sm text-slate-600 flex items-center gap-2"><span className="text-slate-300">•</span> {b.label}</span>
                  <span className="text-sm font-semibold text-slate-800">{b.amount}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Expected Impact */}
          <section className="mb-6">
            <h3 className="text-base font-bold text-slate-800 mb-2">Expected Impact</h3>
            <ul className="space-y-1.5">
              {IMPACT.map((item, i) => (
                <li key={i} className="text-sm text-slate-500 flex items-start gap-2">
                  <span className="text-slate-300 mt-0.5">•</span> {item}
                </li>
              ))}
            </ul>
          </section>

          {/* Supporting Evidence */}
          <section>
            <h3 className="text-base font-bold text-slate-800 mb-3">Supporting Evidence</h3>
            <div className="space-y-2">
              {FILES.map((f, i) => (
                <div key={i} className="flex items-center gap-3 py-1.5">
                  <span className={`text-[9px] font-bold text-white px-1.5 py-1 rounded ${f.tagColor}`}>{f.tag}</span>
                  <span className="text-sm font-medium text-slate-700 flex-1">{f.name}</span>
                  <span className="text-xs text-slate-400 font-medium">{f.size}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Footer buttons */}
        <div className="p-5 border-t border-[#e6ebf2] flex items-center justify-end gap-3 shrink-0">
          <button className="px-6 py-2.5 bg-rose-50 text-rose-600 font-semibold rounded-xl text-sm hover:bg-rose-100 transition-colors">Reject</button>
          <button className="px-6 py-2.5 bg-white border border-[#e6ebf2] text-slate-700 font-semibold rounded-xl text-sm hover:bg-slate-50 transition-colors">Request Changes</button>
          <button className="px-8 py-2.5 bg-[#4f46e5] text-white font-semibold rounded-xl text-sm hover:bg-[#4338ca] transition-colors shadow-[0_4px_12px_rgba(79,70,229,0.28)]">Approve</button>
        </div>
      </div>
    </div>
  </div>
);
