import {
  ObsTitleBar, KpiCard, Pill, ObsTabs, ObsCard, PanelTitle, pageShellCls,
} from "./ObsShared.jsx";
import { Users, Eye, Target, Gauge, UserPlus, FileText, Send } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const KPIS = [
  { icon: Users, label: "Monthly Visitors", value: "48.2K", trend: "12.4%", up: true, iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: Eye, label: "Page Views", value: "3.4M", trend: "16.0%", up: true, iconBg: "bg-[#f0edfe]", iconTint: "text-[#7c3aed]" },
  { icon: Target, label: "Conversion Rate", value: "2.8%", trend: "0.0%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: Gauge, label: "Avg Load Time", value: "1.2s", trend: "18.4%", up: true, iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
];

const TRAFFIC = [
  ["Sep 1", 22], ["Sep 5", 28], ["Sep 9", 34], ["Sep 13", 41], ["Sep 17", 48],
].map(([d, v]) => ({ d, v }));

const TOP = [
  { page: "/", views: "12.4K" },
  { page: "/features", views: "8.1K" },
  { page: "/pricing", views: "6.1K" },
  { page: "/blog", views: "4.8K" },
  { page: "/contact", views: "3.2K" },
];

const ACTIVITY = [
  { icon: UserPlus, tint: "text-[#16a34a]", title: "New signup from India", time: "2 mins ago" },
  { icon: FileText, tint: "text-[#4f46e5]", title: "Blog post published", time: "1 hour ago" },
  { icon: Send, tint: "text-[#7c3aed]", title: "Contact form submission", time: "3 hours ago" },
];

const ACTIONS = ["View Live Site", "Edit Content", "Manage SEO", "View Analytics"];

export const ViewObsWebsite = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Website"
        subtitle="Website analytics, content, and SEO"
        right={<Pill label="Last 30 days" />}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <ObsTabs tabs={["Traffic", "Content", "SEO", "Forms", "Settings"]} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-5">
        <ObsCard className="p-5">
          <PanelTitle className="mb-4">Website Traffic</PanelTitle>
          <div className="h-[240px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={TRAFFIC} margin={{ top: 6, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="d" tickLine={false} axisLine={false} tick={{ fill: "#94a3b8", fontSize: 12 }} interval={0} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  width={40}
                  ticks={[0, 10, 20, 30, 40, 50]}
                  tickFormatter={(v) => `${v}K`}
                  domain={[0, 50]}
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
          <PanelTitle className="mb-3">Top Pages</PanelTitle>
          <div className="divide-y divide-[#eef2f8]">
            {TOP.map((t) => (
              <div key={t.page} className="flex items-center justify-between py-2.5">
                <span className="text-[14px] text-[#334155] font-medium">{t.page}</span>
                <span className="text-[14px] font-semibold text-[#0b1220]">{t.views}</span>
              </div>
            ))}
          </div>
        </ObsCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr] gap-5 mt-5">
        <ObsCard className="p-5">
          <PanelTitle className="mb-3">Recent Activity</PanelTitle>
          <div className="divide-y divide-[#eef2f8]">
            {ACTIVITY.map((a, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <a.icon size={17} className={a.tint} strokeWidth={2.2} />
                <span className="flex-1 text-[14px] text-[#334155]">{a.title}</span>
                <span className="text-[13px] text-[#94a3b8]">{a.time}</span>
              </div>
            ))}
          </div>
        </ObsCard>

        <ObsCard className="p-5">
          <PanelTitle className="mb-3">Quick Actions</PanelTitle>
          <div className="grid grid-cols-2 gap-3">
            {ACTIONS.map((a, i) => (
              <button
                key={a}
                className={`h-11 rounded-xl text-[14px] font-semibold transition-colors ${
                  i === 0
                    ? "bg-[#4f46e5] text-white hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)]"
                    : "border border-[#e6ebf2] text-[#334155] hover:bg-[#f5f8fc]"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
        </ObsCard>
      </div>
    </div>
  </div>
);
