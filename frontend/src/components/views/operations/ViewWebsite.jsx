import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, Tabs, DropdownPill } from "./OpsShared.jsx";
import { Globe, BarChart3, Clock, TrendingUp, ExternalLink } from "lucide-react";
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
  { title: "Total Visitors", value: "24.8K", trend: "18%", icon: BarChart3, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Page Views", value: "62.1K", trend: "22%", icon: BarChart3, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Avg. Session", value: "2m 14s", trend: "12%", icon: Clock, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
  { title: "Bounce Rate", value: "28%", trend: "6%", up: false, icon: TrendingUp, iconTint: "text-rose-500", iconBg: "bg-rose-50" },
];

const CHART = [
  { d: "Sep 1", v: 860 }, { d: "", v: 1000 }, { d: "Sep 5", v: 1400 },
  { d: "", v: 2200 }, { d: "", v: 2600 }, { d: "Sep 10", v: 2800 },
  { d: "", v: 2700 }, { d: "", v: 2900 }, { d: "Sep 15", v: 1900 },
  { d: "", v: 2100 }, { d: "Sep 20", v: 2500 }, { d: "", v: 2700 },
  { d: "", v: 2300 }, { d: "Sep 25", v: 2800 }, { d: "", v: 3300 },
  { d: "Sep 30", v: 3500 },
];

const PAGES = [
  { page: "/", views: "12.4K" },
  { page: "/features", views: "6.2K" },
  { page: "/pricing", views: "6.1K" },
  { page: "/blog", views: "4.8K" },
  { page: "/contact", views: "2.9K" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none mt-1.5">{m.value}</h3>
        <div className={`mt-2.5 flex items-center gap-1 text-[13px] font-semibold ${m.up === false ? "text-rose-500" : "text-emerald-600"}`}>
          <TrendingUp size={14} strokeWidth={2.6} className={m.up === false ? "rotate-180" : ""} />{m.trend}
        </div>
      </div>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={22} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewWebsite = () => {
  const [tab, setTab] = useState("Overview");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Globe}
        title="Website"
        subtitle="Track website analytics, content and SEO"
        iconTint="text-slate-700"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            <ExternalLink size={18} strokeWidth={2} /> View Site
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["Overview", "Content", "SEO", "Performance", "Settings"]} active={tab} onChange={setTab} />

      <div className="grid grid-cols-3 gap-6">
        {/* Traffic chart */}
        <Card className="col-span-2 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-[#0b1220]">Website Traffic</h2>
            <DropdownPill label="Daily" className="h-9" />
          </div>
          <div className="h-[280px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={CHART} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="webArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0f172a" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#0f172a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} interval={0} />
                <YAxis
                  domain={[0, 4000]}
                  ticks={[0, 1000, 2000, 3000, 4000]}
                  tickFormatter={(v) => (v === 0 ? "0" : `${v / 1000}K`)}
                  tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} width={40}
                />
                <Tooltip />
                <Area type="linear" dataKey="v" stroke="#0f172a" strokeWidth={2.5} fill="url(#webArea)" dot={{ r: 3, fill: "#0f172a", strokeWidth: 0 }} activeDot={{ r: 5 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Top Pages */}
        <Card className="col-span-1 p-6">
          <h2 className="text-lg font-bold text-[#0b1220] mb-4">Top Pages</h2>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#e6ebf2] text-left text-[13px] font-bold text-slate-500">
                <th className="pb-3 font-bold">Page</th>
                <th className="pb-3 font-bold text-right">Views</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eef2f8]">
              {PAGES.map((p, i) => (
                <tr key={i} className="text-[14px]">
                  <td className="py-3 text-slate-700 font-medium">{p.page}</td>
                  <td className="py-3 text-slate-500 text-right font-semibold">{p.views}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
};
