import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, Tabs, FilterBar, Pagination, StatusPill } from "./OpsShared.jsx";
import {
  Megaphone,
  MessageSquare,
  Users,
  CircleCheck,
  BarChart3,
  Plus,
  Download,
  MoreHorizontal,
  TrendingUp,
} from "lucide-react";

const STATS = [
  { title: "Total Campaigns", value: "24", trend: "20%", icon: MessageSquare, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Total Reach", value: "125.4K", trend: "32%", icon: Users, iconTint: "text-violet-600", iconBg: "bg-violet-50" },
  { title: "Conversions", value: "4,820", trend: "18%", icon: CircleCheck, iconTint: "text-emerald-600", iconBg: "bg-emerald-50" },
  { title: "Conversion Rate", value: "3.8%", trend: "6%", icon: BarChart3, iconTint: "text-orange-500", iconBg: "bg-orange-50" },
];

const ROWS = [
  { name: "Product Launch", channel: "Social Media", start: "Aug 01, 2026", end: "Sep 30, 2026", status: "Active", tone: "green" },
  { name: "Brand Awareness", channel: "Google Ads", start: "Aug 15, 2026", end: "Sep 15, 2026", status: "Completed", tone: "green" },
  { name: "Holiday Sale", channel: "Email", start: "Aug 20, 2026", end: "Sep 10, 2026", status: "Completed", tone: "green" },
  { name: "Retargeting", channel: "Meta Ads", start: "Sep 05, 2026", end: "Oct 05, 2026", status: "Active", tone: "green" },
  { name: "Community Growth", channel: "LinkedIn", start: "Sep 10, 2026", end: "Oct 10, 2026", status: "Scheduled", tone: "blue" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none mt-1.5">{m.value}</h3>
        <div className="mt-2.5 flex items-center gap-1 text-[13px] font-semibold text-emerald-600">
          <TrendingUp size={14} strokeWidth={2.6} />{m.trend}
        </div>
      </div>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={22} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewMarketingCampaigns = () => {
  const [tab, setTab] = useState("Campaigns");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Megaphone}
        title="Marketing"
        subtitle="Manage campaigns, channels and performance"
        iconTint="text-[#4f46e5]"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            <Plus size={18} strokeWidth={2.4} /> Create Campaign
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["Campaigns", "Channels", "Performance", "Audience"]} active={tab} onChange={setTab} />

      <FilterBar
        placeholder="Search campaigns..."
        filters={["All Channels", "All Status"]}
        action={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-slate-700 text-[15px] font-semibold hover:bg-slate-50">
            <Download size={18} strokeWidth={2} /> Export
          </button>
        }
      />

      <Card className="overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50/70 text-left text-[13px] font-bold text-slate-500">
              <th className="py-3.5 pl-5 w-12"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></th>
              <th className="py-3.5 font-bold">Campaign</th>
              <th className="py-3.5 font-bold">Channel</th>
              <th className="py-3.5 font-bold">Start Date</th>
              <th className="py-3.5 font-bold">End Date</th>
              <th className="py-3.5 font-bold">Status</th>
              <th className="py-3.5 pr-5 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ROWS.map((r, i) => (
              <tr key={i} className="text-[14px] hover:bg-slate-50/50">
                <td className="py-4 pl-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></td>
                <td className="py-4 font-bold text-[#0b1220]">{r.name}</td>
                <td className="py-4 text-blue-600 font-medium">{r.channel}</td>
                <td className="py-4 text-slate-500">{r.start}</td>
                <td className="py-4 text-slate-500">{r.end}</td>
                <td className="py-4"><StatusPill label={r.status} tone={r.tone} /></td>
                <td className="py-4 pr-5 text-right"><MoreHorizontal size={18} className="text-slate-400 inline-block" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Pagination label="Showing 1–5 of 24 campaigns" pages={5} active={1} />
    </div>
  );
};
