import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { Avatar } from "../../ui/Avatar.jsx";
import { OpsHeader, Tabs, FilterBar, Pagination, StatusPill } from "./OpsShared.jsx";
import { Users, UsersRound, Flag, BarChart3, Plus, Download, MoreHorizontal, TrendingUp } from "lucide-react";

const STATS = [
  { title: "Total Customers", value: "1,024", trend: "+14%", up: true, icon: Users, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Active Customers", value: "842", trend: "+10%", up: true, icon: UsersRound, iconTint: "text-emerald-600", iconBg: "bg-emerald-50" },
  { title: "New This Month", value: "48", trend: "+20%", up: true, icon: Flag, iconTint: "text-violet-600", iconBg: "bg-violet-50" },
  { title: "Churn Rate", value: "2.4%", trend: "6%", up: false, icon: BarChart3, iconTint: "text-rose-500", iconBg: "bg-rose-50" },
];

const ROWS = [
  { name: "Rahul Sharma", company: "TechCorp", segment: "Enterprise", active: "Sep 15, 2026", status: "Active", tone: "green", img: "https://i.pravatar.cc/80?img=12" },
  { name: "Priya Mehta", company: "InnovateX", segment: "SME", active: "Sep 14, 2026", status: "Active", tone: "green", img: "https://i.pravatar.cc/80?img=45" },
  { name: "Amit Patel", company: "GreenField", segment: "Startup", active: "Sep 13, 2026", status: "Active", tone: "green", img: "https://i.pravatar.cc/80?img=13" },
  { name: "Sneha Kapoor", company: "NextGen", segment: "Enterprise", active: "Sep 12, 2026", status: "Inactive", tone: "amber", initials: "SK", color: "bg-violet-100 text-violet-600" },
  { name: "Vikram Singh", company: "DataMind", segment: "Enterprise", active: "Sep 10, 2026", status: "Active", tone: "green", img: "https://i.pravatar.cc/80?img=14" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none mt-1.5">{m.value}</h3>
        <div className={`mt-2.5 flex items-center gap-1 text-[13px] font-semibold ${m.up ? "text-emerald-600" : "text-rose-500"}`}>
          <TrendingUp size={14} strokeWidth={2.6} className={m.up ? "" : "rotate-180"} />{m.trend}
        </div>
      </div>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={22} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewCustomersCRM = () => {
  const [tab, setTab] = useState("All Customers");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Users}
        title="Customers / CRM"
        subtitle="Manage customer data and relationships"
        iconTint="text-[#4f46e5]"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            <Plus size={18} strokeWidth={2.4} /> Add Customer
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["All Customers", "Segments", "Interactions", "Activities"]} active={tab} onChange={setTab} />

      <FilterBar
        placeholder="Search customers..."
        filters={["All Segments", "All Status"]}
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
              <th className="py-3.5 font-bold">Name</th>
              <th className="py-3.5 font-bold">Company</th>
              <th className="py-3.5 font-bold">Segment</th>
              <th className="py-3.5 font-bold">Last Active</th>
              <th className="py-3.5 font-bold">Status</th>
              <th className="py-3.5 pr-5 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ROWS.map((r, i) => (
              <tr key={i} className="text-[14px] hover:bg-slate-50/50">
                <td className="py-4 pl-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></td>
                <td className="py-4">
                  <span className="flex items-center gap-3">
                    <Avatar src={r.img} initials={r.initials} color={r.color} size="w-9 h-9" />
                    <span className="font-semibold text-[#0b1220]">{r.name}</span>
                  </span>
                </td>
                <td className="py-4 text-blue-600 font-medium">{r.company}</td>
                <td className="py-4 text-slate-500">{r.segment}</td>
                <td className="py-4 text-slate-500">{r.active}</td>
                <td className="py-4"><StatusPill label={r.status} tone={r.tone} /></td>
                <td className="py-4 pr-5 text-right"><MoreHorizontal size={18} className="text-slate-400 inline-block" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Pagination label="Showing 1–5 of 1,024 customers" pages={5} active={1} />
    </div>
  );
};
