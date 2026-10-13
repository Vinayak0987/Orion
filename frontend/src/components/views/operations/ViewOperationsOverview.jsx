import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, DropdownPill } from "./OpsShared.jsx";
import {
  Network,
  BarChart3,
  Play,
  CircleCheck,
  TrendingUp,
  FileText,
  RefreshCw,
  Plus,
  Settings,
  ListChecks,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const STATS = [
  { title: "Total Operations", value: "128", trend: "12%", icon: BarChart3, iconTint: "text-[#4f46e5]", iconBg: "bg-[#eef2ff]" },
  { title: "Active Workflows", value: "24", trend: "6%", icon: Play, iconTint: "text-[#7c3aed]", iconBg: "bg-[#f0edfe]" },
  { title: "Tasks Completed", value: "1,240", trend: "15%", icon: CircleCheck, iconTint: "text-[#16a34a]", iconBg: "bg-[#e7f8ef]" },
  { title: "Success Rate", value: "96.2%", trend: "2%", icon: TrendingUp, iconTint: "text-[#f59e0b]", iconBg: "bg-[#fef3e2]" },
];

const CHART = [
  { d: "Sep 1", v: 8 }, { d: "", v: 30 }, { d: "", v: 26 }, { d: "Sep 5", v: 31 },
  { d: "", v: 58 }, { d: "", v: 72 }, { d: "Sep 10", v: 85 }, { d: "", v: 101 },
  { d: "", v: 62 }, { d: "Sep 15", v: 44 }, { d: "", v: 60 }, { d: "", v: 86 },
  { d: "Sep 20", v: 92 }, { d: "", v: 114 }, { d: "", v: 84 }, { d: "Sep 25", v: 62 },
  { d: "", v: 108 }, { d: "", v: 99 }, { d: "", v: 133 }, { d: "Sep 30", v: 160 },
];

const RECENT = [
  { title: "Inventory sync completed", time: "2 minutes ago", icon: Play, tint: "text-emerald-600" },
  { title: "New order processed", time: "12 minutes ago", icon: FileText, tint: "text-slate-700" },
  { title: "Supplier data updated", time: "1 hour ago", icon: RefreshCw, tint: "text-slate-700" },
  { title: "Monthly report generated", time: "2 hours ago", icon: FileText, tint: "text-slate-700" },
];

const ACTIONS = [
  { label: "Run Workflow", icon: Play, primary: true },
  { label: "View All Operations", icon: ListChecks },
  { label: "Create Operation", icon: Plus },
  { label: "Operation Settings", icon: Settings },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
    <div className="flex items-end justify-between mt-1.5">
      <div>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none">{m.value}</h3>
        <div className="mt-2.5 flex items-center gap-1 text-[13px] font-semibold text-emerald-600">
          <TrendingUp size={14} strokeWidth={2.6} />
          {m.trend}
        </div>
      </div>
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={20} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewOperationsOverview = () => {
  const [range] = useState("Daily");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Network}
        title="Operations Overview"
        subtitle="Run and monitor business operations"
        right={<DropdownPill label="Last 30 days" />}
      />

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      {/* Activity chart */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#0b1220]">Operations Activity</h2>
          <DropdownPill label={range} className="h-9" />
        </div>
        <div className="h-[280px] -ml-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={CHART} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="opsArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} interval={0} />
              <YAxis domain={[0, 200]} ticks={[0, 50, 100, 150, 200]} tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} width={40} />
              <Tooltip />
              <Area type="linear" dataKey="v" stroke="#4f46e5" strokeWidth={2.5} fill="url(#opsArea)" dot={{ r: 3, fill: "#4f46e5", strokeWidth: 0 }} activeDot={{ r: 5 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Recent + Quick actions */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-2 p-6 !rounded-2xl !border-[#e6ebf2]">
          <h2 className="text-lg font-bold text-[#0b1220] mb-2">Recent Operations</h2>
          <div className="flex flex-col divide-y divide-[#eef2f8]">
            {RECENT.map((r, i) => (
              <div key={i} className="flex items-center gap-4 py-4">
                <div className="w-10 h-10 rounded-xl bg-[#e7f8ef] flex items-center justify-center shrink-0">
                  <r.icon size={18} strokeWidth={2} className={r.tint} />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-[15px] font-semibold text-[#0b1220] leading-tight">{r.title}</h4>
                  <p className="text-[13px] text-[#94a3b8] mt-0.5">{r.time}</p>
                </div>
                <span className="px-3 py-1 rounded-full text-[13px] font-semibold bg-[#e7f8ef] text-[#16a34a]">Success</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="col-span-1 p-6 !rounded-2xl !border-[#e6ebf2]">
          <h2 className="text-lg font-bold text-[#0b1220] mb-4">Quick Actions</h2>
          <div className="flex flex-col gap-3">
            {ACTIONS.map((a, i) => (
              <button
                key={i}
                className={`flex items-center gap-3 h-[52px] px-4 rounded-xl text-[15px] font-semibold transition-colors ${
                  a.primary
                    ? "bg-[#4f46e5] text-white hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)]"
                    : "border border-[#e6ebf2] text-[#334155] hover:bg-[#f5f8fc]"
                }`}
              >
                <a.icon size={19} strokeWidth={2} className={a.primary ? "text-white" : "text-[#64748b]"} />
                {a.label}
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
