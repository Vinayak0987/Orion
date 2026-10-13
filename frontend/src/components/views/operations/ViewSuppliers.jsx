import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, Tabs, FilterBar } from "./OpsShared.jsx";
import { Truck, Briefcase, Power, Trophy, CalendarPlus, Plus, Download, MoreHorizontal, TrendingUp, Star } from "lucide-react";

const STATS = [
  { title: "Total Suppliers", value: "86", trend: "12%", icon: Briefcase },
  { title: "Active Suppliers", value: "72", icon: Power },
  { title: "Pending Approval", value: "8", icon: Trophy },
  { title: "Total Spend", value: "₹ 28.4L", trend: "10%", icon: CalendarPlus },
];

const ROWS = [
  { name: "TechSupply Co.", cat: "Electronics", contact: "Rahul Verma", perf: "4.8" },
  { name: "OfficeHub", cat: "Furniture", contact: "Priya Nair", perf: "4.5" },
  { name: "StationeryMart", cat: "Stationery", contact: "Amit Shah", perf: "4.2" },
  { name: "LogiTrans", cat: "Logistics", contact: "Neha Kapoor", perf: "4.0" },
  { name: "CloudServices", cat: "IT Services", contact: "Vikram Mehta", perf: "4.7" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
        <h3 className="text-[30px] font-extrabold text-slate-900 leading-none mt-1.5">{m.value}</h3>
        {m.trend && (
          <div className="mt-2.5 flex items-center gap-1 text-[13px] font-semibold text-emerald-600">
            <TrendingUp size={14} strokeWidth={2.6} />{m.trend}
          </div>
        )}
      </div>
      <m.icon size={24} strokeWidth={1.8} className="text-slate-900 shrink-0" />
    </div>
  </div>
);

export const ViewSuppliers = () => {
  const [tab, setTab] = useState("All Suppliers");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Truck}
        title="Suppliers"
        subtitle="Manage supplier information and relationships"
        iconTint="text-slate-900"
        right={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-slate-900 text-white text-[15px] font-semibold hover:bg-slate-800">
            <Plus size={18} strokeWidth={2.4} /> Add Supplier
          </button>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["All Suppliers", "Categories", "Performance", "Contracts"]} active={tab} onChange={setTab} />

      <FilterBar
        placeholder="Search suppliers..."
        filters={["All Categories", "All Status"]}
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
              <th className="py-3.5 pl-5 w-12"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-slate-800" /></th>
              <th className="py-3.5 font-bold">Name</th>
              <th className="py-3.5 font-bold">Category</th>
              <th className="py-3.5 font-bold">Contact Person</th>
              <th className="py-3.5 font-bold">Status</th>
              <th className="py-3.5 font-bold">Performance</th>
              <th className="py-3.5 pr-5 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ROWS.map((r, i) => (
              <tr key={i} className="text-[14px] hover:bg-slate-50/50">
                <td className="py-4 pl-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-slate-800" /></td>
                <td className="py-4 font-semibold text-slate-900">{r.name}</td>
                <td className="py-4 text-slate-500">{r.cat}</td>
                <td className="py-4 text-slate-500">{r.contact}</td>
                <td className="py-4"><span className="text-emerald-600 font-bold text-[14px]">Active</span></td>
                <td className="py-4">
                  <span className="inline-flex items-center gap-1 font-bold text-orange-500">
                    {r.perf} <Star size={14} className="fill-orange-400 text-orange-400" />
                  </span>
                </td>
                <td className="py-4 pr-5 text-right"><MoreHorizontal size={18} className="text-slate-400 inline-block" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};
