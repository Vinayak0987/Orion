import { useState } from "react";
import { Card } from "../../ui/Card.jsx";
import { OpsHeader, Tabs, FilterBar, Pagination, StatusPill } from "./OpsShared.jsx";
import {
  Package,
  BarChart3,
  TriangleAlert,
  CalendarDays,
  Plus,
  Download,
  ChevronDown,
  MoreHorizontal,
  TrendingUp,
} from "lucide-react";

const STATS = [
  { title: "Total Items", value: "2,480", icon: BarChart3, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Low Stock", value: "120", icon: TriangleAlert, iconTint: "text-rose-500", iconBg: "bg-rose-50" },
  { title: "Out of Stock", value: "24", icon: TriangleAlert, iconTint: "text-rose-500", iconBg: "bg-rose-50" },
  { title: "Inventory Value", value: "₹ 12.4L", icon: CalendarDays, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
];

const ITEMS = [
  { item: "Wireless Mouse", sku: "WM-001", cat: "Electronics", stock: 120, stockTone: "text-emerald-600", status: "In Stock", tone: "green", img: "computer mouse" },
  { item: "Office Chair", sku: "OC-002", cat: "Furniture", stock: 8, stockTone: "text-rose-500", status: "Low Stock", tone: "amber", img: "office chair" },
  { item: "USB-C Cable", sku: "UC-003", cat: "Electronics", stock: 0, stockTone: "text-rose-500", status: "Out of Stock", tone: "red", img: "usb cable" },
  { item: "Notebook", sku: "NB-004", cat: "Stationery", stock: 250, stockTone: "text-emerald-600", status: "In Stock", tone: "green", img: "notebook" },
  { item: 'Monitor 24"', sku: "MN-005", cat: "Electronics", stock: 15, stockTone: "text-amber-500", status: "Low Stock", tone: "amber", img: "computer monitor" },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
    <div className="flex items-end justify-between mt-1.5">
      <div>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none">{m.value}</h3>
        <div className="mt-2.5 flex items-center gap-1 text-[13px] font-semibold text-emerald-600">
          <TrendingUp size={14} strokeWidth={2.6} />0%
        </div>
      </div>
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={22} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewInventory = () => {
  const [tab, setTab] = useState("All Items");
  return (
    <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
      <OpsHeader
        icon={Package}
        title="Inventory Management"
        subtitle="Track and manage inventory across business units"
        iconTint="text-blue-600"
        right={
          <>
            <button className="flex items-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-slate-700 text-[15px] font-semibold hover:bg-slate-50">
              <Plus size={18} strokeWidth={2.4} /> Import
            </button>
            <button className="flex items-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-semibold hover:bg-[#4338ca]">
              <Plus size={18} strokeWidth={2.4} /> Add Item
            </button>
          </>
        }
      />

      <div className="grid grid-cols-4 gap-4">
        {STATS.map((m, i) => <StatCard key={i} m={m} />)}
      </div>

      <Tabs tabs={["All Items", "Low Stock", "Out of Stock", "Categories", "Suppliers"]} active={tab} onChange={setTab} />

      <FilterBar
        placeholder="Search items..."
        filters={["All Categories", "All Suppliers"]}
        action={
          <button className="flex items-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-slate-700 text-[15px] font-semibold hover:bg-slate-50">
            <Download size={18} strokeWidth={2} /> Export
          </button>
        }
      />

      {/* Table */}
      <Card className="overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50/70 text-left text-[13px] font-bold text-slate-500">
              <th className="py-3.5 pl-5 w-12"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></th>
              <th className="py-3.5 font-bold">Item</th>
              <th className="py-3.5 font-bold"><span className="inline-flex items-center gap-1">SKU <ChevronDown size={13} /></span></th>
              <th className="py-3.5 font-bold">Category</th>
              <th className="py-3.5 font-bold">Stock</th>
              <th className="py-3.5 font-bold">Status</th>
              <th className="py-3.5 pr-5 font-bold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {ITEMS.map((it, i) => (
              <tr key={i} className="text-[14px] hover:bg-slate-50/50">
                <td className="py-4 pl-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 accent-indigo-600" /></td>
                <td className="py-4">
                  <span className="flex items-center gap-3">
                    <span className="w-10 h-10 rounded-lg bg-slate-100 border border-[#e6ebf2] overflow-hidden shrink-0" data-img={it.img} />
                    <span className="font-semibold text-[#0b1220]">{it.item}</span>
                  </span>
                </td>
                <td className="py-4 text-blue-600 font-medium">{it.sku}</td>
                <td className="py-4 text-slate-500">{it.cat}</td>
                <td className={`py-4 font-bold ${it.stockTone}`}>{it.stock}</td>
                <td className="py-4"><StatusPill label={it.status} tone={it.tone} /></td>
                <td className="py-4 pr-5 text-right"><MoreHorizontal size={18} className="text-slate-400 inline-block" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Pagination label="Showing 1–5 of 2,480 items" pages={5} active={1} />
    </div>
  );
};
