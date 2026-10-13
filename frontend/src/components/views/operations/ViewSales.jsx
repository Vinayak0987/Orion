import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, Tabs } from "./OpsShared.jsx";
import { TrendingUp, ShoppingCart, Target, Plus, ChevronDown, MoreVertical, Flag } from "lucide-react";

const STATS = [
  { title: "Total Orders", value: "1,248", trend: "18%", icon: ShoppingCart, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
  { title: "Pipeline Value", value: "₹ 42.6L", trend: "24%", icon: Target, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
  { title: "Active Deals", value: "86", trend: "12%", icon: TrendingUp, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
  { title: "Conversion Rate", value: "28%", trend: "6%", icon: TrendingUp, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
];

const COLUMNS = [
  {
    title: "Leads", count: 24, value: "₹ 8.2L",
    cards: [
      { name: "TechCorp", amt: "₹ 1.2L", note: "Initial discussion", flag: true },
      { name: "InnovateX", amt: "₹ 9.0K", note: "Needs analysis" },
      { name: "GreenField", amt: "₹ 60K", note: "Contacted" },
    ],
  },
  {
    title: "Qualified", count: 18, value: "₹ 12.4L",
    cards: [
      { name: "NextGen", amt: "₹ 2.4L", note: "Proposal sent" },
      { name: "BrightSoft", amt: "₹ 1.8L", note: "Negotiation" },
      { name: "CloudWorks", amt: "₹ 1.2L", note: "Technical review" },
    ],
  },
  {
    title: "Proposal", count: 12, value: "₹ 15.6L",
    cards: [
      { name: "DataMind", amt: "₹ 3.2L", note: "Proposal sent" },
      { name: "AI Studio", amt: "₹ 2.8L", note: "Pricing discussion" },
      { name: "FutureTech", amt: "₹ 1.6L", note: "Legal review" },
    ],
  },
  {
    title: "Closed", count: 8, value: "₹ 6.4L",
    cards: [
      { name: "GlobalMart", amt: "₹ 2.0L", won: true },
      { name: "HealthPlus", amt: "₹ 1.2L", won: true },
      { name: "EduCore", amt: "₹ 1.2L", won: true },
    ],
  },
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

export const ViewSales = () => {
  const [tab, setTab] = useState("Pipeline");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={TrendingUp}
        title="Sales"
        subtitle="Track orders, pipeline and deals"
        iconTint="text-[#0b1220]"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
            <Plus size={18} strokeWidth={2.4} /> Create Deal
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["Pipeline", "Orders", "Deals", "Customers"]} active={tab} onChange={setTab} />

      {/* Kanban */}
      <div className="grid grid-cols-4 gap-4">
        {COLUMNS.map((col, ci) => (
          <div key={ci} className="flex flex-col gap-3">
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-[15px] font-bold text-[#0b1220]">{col.title} ({col.count})</h3>
                <ChevronDown size={16} className="text-slate-400" strokeWidth={2.2} />
              </div>
              <p className="text-[14px] font-semibold text-slate-500 mt-1">{col.value}</p>
            </Card>
            {col.cards.map((c, i) => (
              <Card key={i} className="p-4">
                <div className="flex items-start justify-between">
                  <h4 className="text-[15px] font-bold text-[#0b1220]">{c.name}</h4>
                  {c.flag
                    ? <Flag size={15} className="text-slate-400" strokeWidth={2} />
                    : <MoreVertical size={15} className="text-slate-400" strokeWidth={2} />}
                </div>
                <p className="text-[14px] font-semibold text-slate-600 mt-1.5">{c.amt}</p>
                {c.won
                  ? <span className="inline-block mt-2 px-2.5 py-0.5 rounded-full text-[12px] font-semibold bg-emerald-50 text-emerald-600">Won</span>
                  : <p className="text-[13px] text-slate-400 mt-1.5">{c.note}</p>}
              </Card>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
