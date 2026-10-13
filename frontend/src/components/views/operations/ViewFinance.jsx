import { Card } from "../../ui/Card.jsx";
import { OpsHeader, DropdownPill } from "./OpsShared.jsx";
import {
  Network,
  BarChart3,
  Coins,
  TrendingUp,
  Wallet,
  FileText,
  Users,
  ClipboardCheck,
  Settings,
  CheckCircle2,
  Megaphone,
  CreditCard,
  Receipt,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const STATS = [
  { title: "Total Revenue", value: "₹ 12.4L", trend: "16%", up: true, icon: BarChart3, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Total Expenses", value: "₹ 8.2L", trend: "12%", up: false, icon: Coins, iconTint: "text-slate-700", iconBg: "bg-slate-100" },
  { title: "Net Profit", value: "₹ 4.2L", trend: "24%", up: true, icon: TrendingUp, iconTint: "text-emerald-600", iconBg: "bg-emerald-50" },
  { title: "Cash Flow", value: "₹ 6.8L", trend: "16%", up: true, icon: Wallet, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
];

// Revenue (front, dark blue) vs Expenses (back, light blue)
const BARS = [
  ["Sep 1", 30, 22], ["", 32, 24], ["", 34, 20], ["Sep 5", 46, 30],
  ["", 55, 40], ["", 70, 52], ["", 92, 62], ["Sep 10", 118, 80],
  ["", 105, 70], ["", 130, 88], ["", 150, 100], ["Sep 15", 108, 74],
  ["", 118, 82], ["", 100, 70], ["", 172, 118], ["Sep 20", 110, 78],
  ["", 122, 84], ["", 100, 70], ["", 105, 72], ["Sep 25", 118, 82],
  ["", 130, 90], ["", 100, 70], ["", 160, 110], ["Sep 30", 118, 100],
].map(([d, revenue, expenses]) => ({ d, revenue, expenses }));

const DONUT = [
  { name: "Operations", value: 35, color: "#4f46e5" },
  { name: "Marketing", value: 20, color: "#22c55e" },
  { name: "Salaries", value: 18, color: "#f59e0b" },
  { name: "Suppliers", value: 15, color: "#8b5cf6" },
  { name: "Others", value: 12, color: "#94a3b8" },
];

const TX = [
  { date: "Sep 15", desc: "Office Supplies", icon: FileText, type: "Expense", amount: "- ₹ 12,450", neg: true },
  { date: "Sep 14", desc: "Client Payment", icon: Coins, type: "Revenue", amount: "+ ₹ 28,000", neg: false },
  { date: "Sep 14", desc: "Marketing Ads", icon: Megaphone, type: "Expense", amount: "- ₹ 8,200", neg: true },
  { date: "Sep 13", desc: "Subscription", icon: CreditCard, type: "Expense", amount: "- ₹ 5,999", neg: true },
];

const ACTIONS = [
  { label: "Add Transaction", icon: Users, primary: true },
  { label: "Generate Report", icon: FileText },
  { label: "View Invoices", icon: ClipboardCheck },
  { label: "Finance Settings", icon: Settings },
];

const StatCard = ({ m }) => (
  <div className="bg-white rounded-2xl p-5 border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]">
    <p className="text-slate-500 text-[15px] font-medium">{m.title}</p>
    <div className="flex items-end justify-between mt-1.5">
      <div>
        <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-none">{m.value}</h3>
        <div className={`mt-2.5 flex items-center gap-1 text-[13px] font-semibold ${m.up ? "text-emerald-600" : "text-rose-500"}`}>
          <TrendingUp size={14} strokeWidth={2.6} className={m.up ? "" : "rotate-180"} />
          {m.trend}
        </div>
      </div>
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${m.iconBg}`}>
        <m.icon size={20} strokeWidth={2} className={m.iconTint} />
      </div>
    </div>
  </div>
);

export const ViewFinance = () => (
  <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <OpsHeader
      icon={Network}
      title="Finance"
      subtitle="Track revenue, expenses and cash flow"
      iconTint="text-[#4338ca]"
      right={<DropdownPill label="Last 30 days" />}
    />

    <div className="grid grid-cols-4 gap-4">
      {STATS.map((m, i) => <StatCard key={i} m={m} />)}
    </div>

    {/* Charts row */}
    <div className="grid grid-cols-3 gap-6">
      {/* Revenue vs Expenses */}
      <Card className="col-span-2 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#0b1220]">Revenue vs Expenses</h2>
          <div className="flex items-center gap-5 text-[13px] font-medium text-slate-600">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-600" />Revenue</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-300" />Expenses</span>
          </div>
        </div>
        <div className="h-[300px] -ml-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={BARS} barGap={-6} margin={{ top: 10, right: 6, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} interval={0} />
              <YAxis
                domain={[0, 200]}
                ticks={[0, 50, 100, 150, 200]}
                tickFormatter={(v) => (v === 0 ? "0" : v >= 100 ? `${v / 100}.0L` : `${v}K`)}
                tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} width={44}
              />
              <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} />
              <Bar dataKey="expenses" fill="#bfdbfe" radius={[3, 3, 0, 0]} barSize={9} />
              <Bar dataKey="revenue" fill="#2563eb" radius={[3, 3, 0, 0]} barSize={9} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Expense Breakdown donut */}
      <Card className="col-span-1 p-6">
        <h2 className="text-lg font-bold text-[#0b1220] mb-2">Expense Breakdown</h2>
        <div className="flex items-center gap-4">
          <div className="relative w-[150px] h-[150px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={DONUT} dataKey="value" innerRadius={48} outerRadius={72} paddingAngle={2} startAngle={90} endAngle={-270} stroke="none">
                  {DONUT.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[18px] font-extrabold text-[#0b1220]">₹ 8.2L</span>
            </div>
          </div>
          <div className="flex-1 flex flex-col gap-2.5">
            {DONUT.map((d, i) => (
              <div key={i} className="flex items-center gap-2 text-[14px]">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.color }} />
                <span className="text-slate-600 flex-1">{d.name}</span>
                <span className="font-semibold text-[#0b1220]">{d.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>

    {/* Transactions + Quick actions */}
    <div className="grid grid-cols-3 gap-6">
      <Card className="col-span-2 p-6">
        <h2 className="text-lg font-bold text-[#0b1220] mb-4">Recent Transactions</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e6ebf2] text-left text-[13px] font-bold text-slate-500">
              <th className="pb-3 font-bold">Date</th>
              <th className="pb-3 font-bold">Description</th>
              <th className="pb-3 font-bold">Type</th>
              <th className="pb-3 font-bold">Amount</th>
              <th className="pb-3 font-bold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {TX.map((t, i) => (
              <tr key={i} className="text-[14px]">
                <td className="py-3.5 text-slate-500">{t.date}</td>
                <td className="py-3.5">
                  <span className="flex items-center gap-2.5 text-[#0b1220] font-medium">
                    <t.icon size={17} strokeWidth={2} className="text-slate-500" />
                    {t.desc}
                  </span>
                </td>
                <td className="py-3.5 text-slate-500">{t.type}</td>
                <td className={`py-3.5 font-semibold ${t.neg ? "text-slate-700" : "text-emerald-600"}`}>{t.amount}</td>
                <td className="py-3.5">
                  <span className="inline-flex items-center gap-1.5 text-emerald-600 font-semibold text-[13px]">
                    <CheckCircle2 size={15} strokeWidth={2.4} />
                    Completed
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="col-span-1 p-6">
        <h2 className="text-lg font-bold text-[#0b1220] mb-4">Quick Actions</h2>
        <div className="flex flex-col gap-3">
          {ACTIONS.map((a, i) => (
            <button
              key={i}
              className={`flex items-center gap-3 h-[52px] px-4 rounded-xl text-[15px] font-semibold transition-colors ${
                a.primary ? "bg-[#4f46e5] text-white hover:bg-[#4338ca]" : "border border-[#e6ebf2] text-slate-700 hover:bg-slate-50"
              }`}
            >
              <a.icon size={19} strokeWidth={2} className={a.primary ? "text-white" : "text-slate-500"} />
              {a.label}
            </button>
          ))}
        </div>
      </Card>
    </div>
  </div>
);
