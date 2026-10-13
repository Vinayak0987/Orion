import {
  ObsTitleBar, KpiCard, Pill, ObsCard, pageShellCls, tableHeadCls, tableCellCls,
} from "./ObsShared.jsx";
import { Wrench, PhoneCall, CheckCircle2, Timer, Download, MoreHorizontal } from "lucide-react";

const KPIS = [
  { icon: Wrench, label: "Total Tools", value: "18", iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: PhoneCall, label: "Total Calls", value: "48.2K", trend: "3.8%", up: true, iconBg: "bg-[#f0edfe]", iconTint: "text-[#7c3aed]" },
  { icon: CheckCircle2, label: "Success Rate", value: "96.4%", iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: Timer, label: "Avg Latency", value: "842 ms", iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
];

const ROWS = [
  { tool: "SerpAPI", cat: "Search", calls: "12,482", rate: "98.1%", lat: "723 ms" },
  { tool: "Notion", cat: "Productivity", calls: "8,241", rate: "96.4%", lat: "843 ms" },
  { tool: "Google Drive", cat: "Storage", calls: "6,128", rate: "99.2%", lat: "421 ms" },
  { tool: "Shopify", cat: "E-commerce", calls: "5,672", rate: "97.8%", lat: "612 ms" },
  { tool: "PostgreSQL", cat: "Database", calls: "4,981", rate: "99.5%", lat: "312 ms" },
  { tool: "Slack", cat: "Communication", calls: "3,842", rate: "98.7%", lat: "545 ms" },
  { tool: "SendGrid", cat: "Email", calls: "2,931", rate: "97.1%", lat: "624 ms" },
  { tool: "Custom API", cat: "Other", calls: "1,204", rate: "94.8%", lat: "1.2s" },
];

const TH = ["Tool Name", "Category", "Total Calls", "Success Rate", "Avg Latency", "Actions"];

export const ViewObsTools = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Tool Usage"
        subtitle="Tool call analytics"
        right={
          <>
            <Pill label="Last 30 days" />
            <Pill label="Export" dark icon={Download} />
          </>
        }
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <ObsCard className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left min-w-[700px]">
            <thead>
              <tr className="bg-[#f8fafc] border-b border-[#eef2f8]">
                {TH.map((h) => (
                  <th key={h} className={tableHeadCls}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eef2f8]">
              {ROWS.map((r) => (
                <tr key={r.tool} className="hover:bg-[#f8fafc]">
                  <td className={`${tableCellCls} font-semibold text-[#0b1220]`}>{r.tool}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.cat}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.calls}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.rate}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.lat}</td>
                  <td className={tableCellCls}>
                    <button className="text-[#94a3b8] hover:text-[#4f46e5]">
                      <MoreHorizontal size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ObsCard>
    </div>
  </div>
);
