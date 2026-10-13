import { ObsTitleBar, KpiCard, Pill, StatusChip, ObsCard, PanelTitle, pageShellCls } from "./ObsShared.jsx";
import { Gauge, Timer, Activity, DollarSign, RefreshCw, AlertCircle, XCircle, Cpu, CheckCircle2 } from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const KPIS = [
  { icon: Gauge, label: "Success Rate", value: "98.2%", trend: "2.4%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: Timer, label: "Avg Latency", value: "842 ms", trend: "12.8%", up: true, iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: Activity, label: "Total Runs", value: "12.4K", trend: "16.8%", up: true, iconBg: "bg-[#f0edfe]", iconTint: "text-[#7c3aed]" },
  { icon: DollarSign, label: "Total Cost", value: "$24.6", trend: "6.4%", up: true, iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
];

const VOLUME = [
  ["12 AM", 1200], ["4 AM", 900], ["8 AM", 1600], ["12 PM", 2400],
  ["4 PM", 3200], ["8 PM", 2800], ["", 2100], ["", 1700],
].map(([t, v]) => ({ t, v }));

const LATENCY = [
  ["12 AM", 620], ["4 AM", 540], ["8 AM", 700], ["12 PM", 980],
  ["4 PM", 1150], ["8 PM", 900],
].map(([t, v]) => ({ t, v }));

const HEALTH = [
  { name: "Agents", value: "98.1%", tone: "green" },
  { name: "Tools & Integrations", value: "98.7%", tone: "green" },
  { name: "Vector DB", value: "99.3%", tone: "green" },
  { name: "LLM Providers", value: "98.9%", tone: "green" },
];

const ALERTS = [
  { icon: AlertCircle, tint: "text-[#ef4444]", title: "High latency detected", time: "2 mins ago" },
  { icon: XCircle, tint: "text-[#f59e0b]", title: "OpenAI API rate limit", time: "12 mins ago" },
  { icon: AlertCircle, tint: "text-[#ef4444]", title: "Agent run failed", time: "28 mins ago" },
  { icon: Cpu, tint: "text-[#f59e0b]", title: "Memory usage high", time: "1 hour ago" },
  { icon: CheckCircle2, tint: "text-[#16a34a]", title: "All systems operational", time: "2 hours ago" },
];

export const ViewObsDashboard = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Observability Dashboard"
        subtitle="Real-time insights into your agents, tools, and system performance."
        right={
          <>
            <Pill label="Last 24 hours" />
            <Pill label="Refresh" dark icon={RefreshCw} />
          </>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        <ObsCard className="p-5">
          <div className="flex items-center justify-between mb-4">
            <PanelTitle>Request Volume</PanelTitle>
            <Pill label="Last 24 hours" />
          </div>
          <div className="h-[220px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={VOLUME} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="t" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  width={34}
                  ticks={[0, 1000, 2000, 3000, 4000]}
                  tickFormatter={(v) => `${v / 1000}K`}
                  domain={[0, 4000]}
                />
                <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} />
                <Bar dataKey="v" fill="#4f46e5" radius={[4, 4, 0, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ObsCard>

        <ObsCard className="p-5">
          <div className="flex items-center justify-between mb-4">
            <PanelTitle>Latency (ms)</PanelTitle>
            <Pill label="Last 24 hours" />
          </div>
          <div className="h-[220px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={LATENCY} margin={{ top: 6, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="t" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  width={34}
                  ticks={[0, 500, 1000, 1500]}
                  domain={[0, 1500]}
                />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke="#16a34a"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#16a34a" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ObsCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ObsCard className="p-5">
          <PanelTitle className="mb-3">System Health</PanelTitle>
          <div className="divide-y divide-[#eef2f8]">
            {HEALTH.map((h) => (
              <div key={h.name} className="flex items-center justify-between py-3">
                <span className="text-[14px] text-[#334155]">{h.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[14px] font-bold text-[#0b1220]">{h.value}</span>
                  <StatusChip label="● Healthy" tone={h.tone} />
                </div>
              </div>
            ))}
          </div>
        </ObsCard>

        <ObsCard className="p-5">
          <div className="flex items-center justify-between mb-3">
            <PanelTitle>Recent Alerts</PanelTitle>
            <button className="text-[14px] font-semibold text-[#4f46e5] hover:text-[#4338ca]">
              View all
            </button>
          </div>
          <div className="divide-y divide-[#eef2f8]">
            {ALERTS.map((a, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <a.icon size={17} className={a.tint} strokeWidth={2.2} />
                <span className="flex-1 text-[14px] text-[#334155]">{a.title}</span>
                <span className="text-[13px] text-[#94a3b8]">{a.time}</span>
              </div>
            ))}
          </div>
        </ObsCard>
      </div>
    </div>
  </div>
);
