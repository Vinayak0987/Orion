import { Card } from "../ui/Card.jsx";
import { LiveAgentNetwork } from "../LiveAgentNetwork.jsx";
import {
  LayoutGrid,
  Users,
  ClipboardCheck,
  Target,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  FileText,
  CircleDot,
  TriangleAlert,
  CircleCheckBig,
  Lightbulb,
  Rocket,
  CheckCircle2,
  FileCheck,
} from "lucide-react";

const METRICS = [
  { title: "Active Missions", value: "12", trend: "+20%", LucideIcon: LayoutGrid, iconColors: "text-violet-600 bg-violet-100", trendColor: "text-emerald-600" },
  { title: "Agents Online", value: "28", trend: "+12%", LucideIcon: Users, iconColors: "text-teal-600 bg-teal-100", trendColor: "text-emerald-600" },
  { title: "Pending Approvals", value: "5", trend: "-40%", LucideIcon: ClipboardCheck, iconColors: "text-rose-500 bg-rose-100", trendColor: "text-rose-500" },
  { title: "System Health", value: "98%", text: "All systems operational", LucideIcon: Target, iconColors: "text-[#4f46e5] bg-[#eef2ff]" },
];

const ACTIVITY = [
  { title: "Market research completed", desc: "Cafe location analysis", time: "2m ago", LucideIcon: FileText, iconColors: "text-emerald-600 bg-emerald-100" },
  { title: "New subtask generated", desc: "Competitor deep dive", time: "12m ago", LucideIcon: CircleDot, iconColors: "text-blue-600 bg-blue-100" },
  { title: "Approval requested", desc: "Marketing budget Q4", time: "28m ago", LucideIcon: TriangleAlert, iconColors: "text-rose-500 bg-rose-100" },
  { title: "Agent deployed", desc: "Financial analyst agent", time: "1h ago", LucideIcon: FileCheck, iconColors: "text-blue-600 bg-blue-100" },
  { title: "Mission completed", desc: "Brand positioning study", time: "3h ago", LucideIcon: CircleCheckBig, iconColors: "text-white bg-emerald-500" },
];

const INSIGHTS = [
  { title: "Thane shows 35% lower rent compared to Mumbai average", desc: "Based on Q market reports", time: "2h ago", LucideIcon: Lightbulb, iconColors: "text-[#4f46e5] bg-[#eef2ff]" },
  { title: "Competitor analysis reveals 3 untapped customer segments", desc: "Based on research agents", time: "4h ago", LucideIcon: Rocket, iconColors: "text-[#4f46e5] bg-[#eef2ff]" },
];

const APPROVALS = [
  { title: "Marketing budget approval", desc: "₹2,50,000 for Q4 campaign", badge: "High", bColor: "text-rose-600 bg-rose-100", LucideIcon: CheckCircle2, iconColors: "text-violet-600 bg-violet-100" },
  { title: "Hire data analyst agent", desc: "For market research", badge: "Medium", bColor: "text-amber-600 bg-amber-100", LucideIcon: FileText, iconColors: "text-blue-600 bg-blue-100" },
  { title: "Tool access request", desc: "Web scraping for research", badge: "Low", bColor: "text-emerald-600 bg-emerald-100", LucideIcon: Target, iconColors: "text-violet-600 bg-violet-100" },
];

export const ViewDashboard = () => (
  <div className="p-6 sm:p-7 space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc]">
    {/* Welcome card — full width */}
    <div>
      <div className="mb-6">
        {/* Welcome back card — full width */}
        <div className="relative w-full overflow-hidden rounded-2xl border border-[#e6ebf2] bg-white shadow-[0_8px_26px_rgba(36,45,64,0.045)] px-6 py-4 sm:px-7">
          {/* Exact indigo wave circuit — flat image, no glass */}
          <img
            src="/welcome-circuit.png"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 w-full h-full object-cover object-center select-none"
            draggable={false}
          />

          <div className="relative z-[1] flex items-center justify-between gap-6 min-h-[88px]">
            <div className="min-w-0">
              <h1 className="text-[26px] sm:text-[28px] leading-[1.1] font-extrabold tracking-[-0.6px] text-[#0b1220]">
                Welcome back, Abhishek!
              </h1>
              <p className="text-[#7c89a8] mt-2 text-[14px] leading-snug">
                Plan, execute, and grow with your AI workforce.
              </p>
            </div>

            <div className="min-w-0 max-w-[200px] text-right shrink-0">
              <p className="text-[15px] font-bold text-[#0b1220] leading-snug tracking-[-0.2px]">
                &ldquo;Turn ideas into execution with AI agents.&rdquo;
              </p>
              <p className="text-[#94a3b8] mt-1.5 text-[13px]">— OrionAI</p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        {METRICS.map((m, i) => (
          <div key={i} className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)] flex flex-col">
            <div className="flex justify-between items-start mb-5">
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${m.iconColors}`}>
                <m.LucideIcon size={22} strokeWidth={2} />
              </div>
              <ChevronRight size={16} className="text-slate-300" strokeWidth={2} />
            </div>
            <h3 className="text-[28px] font-extrabold text-[#0b1220] leading-none">{m.value}</h3>
            <p className="text-slate-500 text-sm font-medium mt-1.5">{m.title}</p>
            <div className="mt-2 text-xs font-semibold">
              {m.trend && (
                <span className={`inline-flex items-center gap-1 ${m.trendColor}`}>
                  {m.trend.startsWith("+") ? <TrendingUp size={13} strokeWidth={2.5} /> : <TrendingDown size={13} strokeWidth={2.5} />}
                  {m.trend}
                </span>
              )}
              {m.text && <span className="text-slate-400 font-medium">{m.text}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>

    {/* Middle Row */}
    <div className="grid grid-cols-3 gap-6">
      <LiveAgentNetwork />
      {/* Recent Activity */}
      <Card className="col-span-1 p-6 flex flex-col">
        <div className="flex justify-between items-center mb-5">
          <h2 className="text-lg font-bold text-slate-800">Recent Activity</h2>
          <a href="#" className="text-sm font-medium text-[#4f46e5] hover:text-[#4338ca] flex items-center gap-1">View all <ChevronRight size={14} strokeWidth={2.5} /></a>
        </div>
        <div className="flex-1 flex flex-col gap-1">
          {ACTIVITY.map((item, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5">
              <div className={`w-9 h-9 rounded-lg shrink-0 flex items-center justify-center ${item.iconColors}`}>
                <item.LucideIcon size={18} strokeWidth={2} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-slate-800 leading-tight">{item.title}</h4>
                <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
              </div>
              <div className="text-xs font-medium text-slate-400 whitespace-nowrap">{item.time}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>

    {/* Bottom Row */}
    <div className="grid grid-cols-2 gap-6">
      {/* Key Insights */}
      <Card className="p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">Key Insights</h2>
        <div className="flex flex-col divide-y divide-[#eef2f8]">
          {INSIGHTS.map((item, i) => (
            <div key={i} className="flex items-start gap-3 py-3.5 first:pt-0">
              <div className={`w-9 h-9 rounded-full shrink-0 flex items-center justify-center ${item.iconColors}`}>
                <item.LucideIcon size={17} strokeWidth={2} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-slate-800 leading-snug">{item.title}</h4>
                <p className="text-xs text-slate-400 mt-1">{item.desc}</p>
              </div>
              <div className="text-xs font-medium text-slate-400 whitespace-nowrap mt-0.5">{item.time}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Pending Approvals */}
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-slate-800">Pending Approvals</h2>
          <a href="#" className="text-sm font-medium text-[#4f46e5] hover:text-[#4338ca] flex items-center gap-1">View all <ChevronRight size={14} strokeWidth={2.5} /></a>
        </div>
        <div className="flex flex-col gap-1">
          {APPROVALS.map((item, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 group cursor-pointer">
              <div className={`w-10 h-10 rounded-full shrink-0 flex items-center justify-center ${item.iconColors}`}>
                <item.LucideIcon size={18} strokeWidth={2} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-slate-800 group-hover:text-[#4f46e5] transition-colors leading-tight">{item.title}</h4>
                <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${item.bColor}`}>{item.badge}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  </div>
);
