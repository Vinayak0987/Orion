import { Card } from "../../ui/Card.jsx";
import { OpsHeader, DropdownPill } from "./OpsShared.jsx";
import {
  Network,
  BarChart3,
  FlaskConical,
  TrendingUp,
  FileText,
  Users,
  ClipboardCheck,
  Settings,
  CheckCircle2,
  Lightbulb,
  BookOpen,
  Search,
  Target,
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
  { title: "Active Projects", value: "12", trend: "20%", up: true, icon: FlaskConical, iconTint: "text-indigo-600", iconBg: "bg-indigo-50" },
  { title: "Research Papers", value: "48", trend: "15%", up: true, icon: BookOpen, iconTint: "text-blue-600", iconBg: "bg-blue-50" },
  { title: "Insights Generated", value: "156", trend: "24%", up: true, icon: Lightbulb, iconTint: "text-emerald-600", iconBg: "bg-emerald-50" },
  { title: "Data Sources", value: "23", trend: "8%", up: true, icon: Search, iconTint: "text-purple-600", iconBg: "bg-purple-50" },
];

// Projects vs Papers progress
const BARS = [
  ["Sep 1", 2, 5], ["", 3, 6], ["", 4, 7], ["Sep 5", 5, 8],
  ["", 6, 9], ["", 7, 10], ["", 8, 11], ["Sep 10", 9, 12],
  ["", 8, 11], ["", 10, 13], ["", 11, 14], ["Sep 15", 10, 12],
  ["", 11, 13], ["", 9, 11], ["", 12, 15], ["Sep 20", 11, 14],
  ["", 12, 15], ["", 10, 13], ["", 11, 14], ["Sep 25", 12, 16],
  ["", 13, 17], ["", 11, 14], ["", 14, 18], ["Sep 30", 12, 16],
].map(([d, projects, papers]) => ({ d, projects, papers }));

const DONUT = [
  { name: "Market Research", value: 30, color: "#4f46e5" },
  { name: "Product Research", value: 25, color: "#22c55e" },
  { name: "Competitor Analysis", value: 20, color: "#f59e0b" },
  { name: "Data Analysis", value: 15, color: "#8b5cf6" },
  { name: "Others", value: 10, color: "#94a3b8" },
];

const PROJECTS = [
  { date: "Sep 15", desc: "Market Analysis Q4", icon: Target, type: "Active", status: "In Progress" },
  { date: "Sep 14", desc: "Competitor Deep Dive", icon: Search, type: "Active", status: "In Progress" },
  { date: "Sep 13", desc: "Product Feasibility", icon: FlaskConical, type: "Active", status: "In Progress" },
  { date: "Sep 12", desc: "Customer Research", icon: Users, type: "Completed", status: "Completed" },
];

const ACTIONS = [
  { label: "New Research Project", icon: FlaskConical, primary: true },
  { label: "Generate Report", icon: FileText },
  { label: "View Papers", icon: BookOpen },
  { label: "Research Settings", icon: Settings },
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

export const ViewResearch = () => (
  <div className="space-y-6 max-w-[1400px] mx-auto pb-20 min-h-full bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7">
    <OpsHeader
      icon={Network}
      title="Research"
      subtitle="Drive innovation through data-driven insights"
      iconTint="text-[#4338ca]"
      right={<DropdownPill label="Last 30 days" />}
    />

    <div className="grid grid-cols-4 gap-4">
      {STATS.map((m, i) => <StatCard key={i} m={m} />)}
    </div>

    {/* Charts row */}
    <div className="grid grid-cols-3 gap-6">
      {/* Projects vs Papers */}
      <Card className="col-span-2 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#0b1220]">Projects vs Papers</h2>
          <div className="flex items-center gap-5 text-[13px] font-medium text-slate-600">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-indigo-600" />Projects</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-indigo-300" />Papers</span>
          </div>
        </div>
        <div className="h-[300px] -ml-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={BARS} barGap={-6} margin={{ top: 10, right: 6, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} interval={0} />
              <YAxis
                domain={[0, 20]}
                ticks={[0, 5, 10, 15, 20]}
                tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 13 }} width={44}
              />
              <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} />
              <Bar dataKey="papers" fill="#a5b4fc" radius={[3, 3, 0, 0]} barSize={9} />
              <Bar dataKey="projects" fill="#4f46e5" radius={[3, 3, 0, 0]} barSize={9} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Research Areas donut */}
      <Card className="col-span-1 p-6">
        <h2 className="text-lg font-bold text-[#0b1220] mb-2">Research Areas</h2>
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
              <span className="text-[18px] font-extrabold text-[#0b1220]">23</span>
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

    {/* Projects + Quick actions */}
    <div className="grid grid-cols-3 gap-6">
      <Card className="col-span-2 p-6">
        <h2 className="text-lg font-bold text-[#0b1220] mb-4">Research Projects</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e6ebf2] text-left text-[13px] font-bold text-slate-500">
              <th className="pb-3 font-bold">Date</th>
              <th className="pb-3 font-bold">Project</th>
              <th className="pb-3 font-bold">Type</th>
              <th className="pb-3 font-bold">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#eef2f8]">
            {PROJECTS.map((t, i) => (
              <tr key={i} className="text-[14px]">
                <td className="py-3.5 text-slate-500">{t.date}</td>
                <td className="py-3.5">
                  <span className="flex items-center gap-2.5 text-[#0b1220] font-medium">
                    <t.icon size={17} strokeWidth={2} className="text-slate-500" />
                    {t.desc}
                  </span>
                </td>
                <td className="py-3.5 text-slate-500">{t.type}</td>
                <td className="py-3.5">
                  <span className={`inline-flex items-center gap-1.5 font-semibold text-[13px] ${
                    t.status === "Completed" ? "text-emerald-600" : "text-indigo-600"
                  }`}>
                    <CheckCircle2 size={15} strokeWidth={2.4} />
                    {t.status}
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