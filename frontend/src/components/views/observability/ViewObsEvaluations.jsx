import {
  ObsTitleBar, KpiCard, ObsTabs, ObsCard, PanelTitle, pageShellCls,
} from "./ObsShared.jsx";
import { CheckCircle2, Star, ClipboardList, TrendingUp } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";

const KPIS = [
  { icon: CheckCircle2, label: "Avg Success Rate", value: "92.4%", trend: "4.2%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: Star, label: "Avg Quality Score", value: "4.5/5", trend: "3.4%", up: true, iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
  { icon: ClipboardList, label: "Evaluation Runs", value: "12", iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: TrendingUp, label: "vs Last Month", value: "+8.2%", trend: "8.2%", up: true, iconBg: "bg-[#f0edfe]", iconTint: "text-[#7c3aed]" },
];

const TREND = [
  ["Sep 1", 3.6], ["Sep 5", 3.9], ["Sep 9", 4.1], ["Sep 13", 4.3], ["Sep 17", 4.5],
].map(([d, v]) => ({ d, v }));

const DONUT = [
  { name: "Passed", value: 67, color: "#16a34a" },
  { name: "Needs Review", value: 22, color: "#f59e0b" },
  { name: "Failed", value: 11, color: "#ef4444" },
];

export const ViewObsEvaluations = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar title="Evaluations" subtitle="Agent quality and performance metrics" />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <ObsTabs tabs={["Overview", "By Agent", "By Task Type", "Human Feedback"]} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ObsCard className="p-5">
          <PanelTitle className="mb-4">Quality Score Trend</PanelTitle>
          <div className="h-[240px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={TREND} margin={{ top: 6, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  width={26}
                  ticks={[1, 2, 3, 4, 5]}
                  domain={[1, 5]}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  dot={{ r: 3.5, fill: "#4f46e5" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ObsCard>

        <ObsCard className="p-5">
          <PanelTitle className="mb-3">Evaluation Breakdown</PanelTitle>
          <div className="flex items-center gap-6">
            <div className="relative w-[160px] h-[160px] shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={DONUT}
                    dataKey="value"
                    innerRadius={50}
                    outerRadius={76}
                    paddingAngle={2}
                    startAngle={90}
                    endAngle={-270}
                    stroke="none"
                  >
                    {DONUT.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-[22px] font-extrabold text-[#0b1220]">12</span>
                <span className="text-[12px] text-[#94a3b8]">Total</span>
              </div>
            </div>
            <div className="flex-1 flex flex-col gap-3">
              {DONUT.map((d) => (
                <div key={d.name} className="flex items-center gap-2 text-[14px]">
                  <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: d.color }} />
                  <span className="text-[#64748b] flex-1">{d.name}</span>
                  <span className="font-semibold text-[#0b1220]">{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </ObsCard>
      </div>
    </div>
  </div>
);
