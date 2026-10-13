import {
  ObsTitleBar, KpiCard, Pill, ObsTabs, ObsCard, PanelTitle, pageShellCls,
} from "./ObsShared.jsx";
import { Layers, ArrowDownToLine, ArrowUpFromLine, DollarSign, Download, Calendar } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";

const KPIS = [
  { icon: Layers, label: "Total Tokens", value: "2.4M", trend: "12.4%", up: true, iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: ArrowDownToLine, label: "Input Tokens", value: "1.8M", trend: "0.1%", up: true, iconBg: "bg-[#f0edfe]", iconTint: "text-[#7c3aed]" },
  { icon: ArrowUpFromLine, label: "Output Tokens", value: "0.6M", trend: "15.6%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: DollarSign, label: "Total Cost", value: "$324.12", trend: "6.3%", up: true, iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
];

const DATA = [
  ["Sep 1", 60, 24], ["Sep 3", 72, 30], ["Sep 5", 66, 26], ["Sep 7", 90, 36],
  ["Sep 9", 84, 34], ["Sep 11", 110, 44], ["Sep 13", 130, 52], ["Sep 15", 120, 48], ["Sep 17", 150, 60],
].map(([d, input, output]) => ({ d, input, output }));

const DONUT = [
  { name: "GPT-4o", value: 40, color: "#4f46e5" },
  { name: "Claude 3.5", value: 28, color: "#7c3aed" },
  { name: "Gemini 1.5", value: 18, color: "#16a34a" },
  { name: "Others", value: 14, color: "#94a3b8" },
];

export const ViewObsLLM = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="LLM Usage & Costs"
        subtitle="Token usage and cost tracking"
        right={
          <>
            <Pill label="Sep 1, 2026 - Sep 18, 2026" icon={Calendar} />
            <Pill label="Export" dark icon={Download} />
          </>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <ObsTabs tabs={["Usage", "Costs", "By Model", "By Agent", "By Department"]} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-5">
        <ObsCard className="p-5">
          <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
            <PanelTitle>Token Usage Over Time</PanelTitle>
            <div className="flex items-center gap-4 text-[13px] font-medium text-[#64748b]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#4f46e5]" />
                Input Tokens
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#a5a2f0]" />
                Output Tokens
              </span>
            </div>
          </div>
          <div className="h-[260px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DATA} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  width={40}
                  ticks={[0, 50, 100, 150, 200]}
                  tickFormatter={(v) => `${v}K`}
                  domain={[0, 200]}
                />
                <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} />
                <Bar dataKey="input" stackId="a" fill="#4f46e5" barSize={18} />
                <Bar dataKey="output" stackId="a" fill="#a5a2f0" radius={[3, 3, 0, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ObsCard>

        <ObsCard className="p-5">
          <PanelTitle className="mb-3">Cost Breakdown</PanelTitle>
          <div className="relative w-[170px] h-[170px] mx-auto">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={DONUT}
                  dataKey="value"
                  innerRadius={55}
                  outerRadius={82}
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
              <span className="text-[20px] font-extrabold text-[#0b1220]">$324.12</span>
              <span className="text-[12px] text-[#94a3b8]">Total</span>
            </div>
          </div>
          <div className="flex flex-col gap-2.5 mt-4">
            {DONUT.map((d) => (
              <div key={d.name} className="flex items-center gap-2 text-[14px]">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: d.color }} />
                <span className="text-[#64748b] flex-1">{d.name}</span>
                <span className="font-semibold text-[#0b1220]">{d.value}%</span>
              </div>
            ))}
          </div>
        </ObsCard>
      </div>
    </div>
  </div>
);
