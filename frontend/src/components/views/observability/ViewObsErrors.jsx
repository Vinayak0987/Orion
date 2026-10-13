import {
  ObsTitleBar, KpiCard, Pill, ObsTabs, ObsPagination, ObsCard, pageShellCls, tableHeadCls, tableCellCls,
} from "./ObsShared.jsx";
import { AlertTriangle, Percent, Timer, RotateCcw } from "lucide-react";

const KPIS = [
  { icon: AlertTriangle, label: "Total Failures", value: "892", trend: "15.4%", up: false, iconBg: "bg-[#fdeaea]", iconTint: "text-[#ef4444]" },
  { icon: Percent, label: "Failure Rate", value: "7.1%", trend: "1.2%", up: false, iconBg: "bg-[#fef3e2]", iconTint: "text-[#f59e0b]" },
  { icon: Timer, label: "Avg Time to Fail", value: "3m 24s", trend: "16.4%", up: true, iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: RotateCcw, label: "Recovery Rate", value: "98.2%", trend: "4.1%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
];

const ERR_TONE = {
  "Tool Error": "bg-[#fdeaea] text-[#ef4444]",
  "LLM Error": "bg-[#fef3e2] text-[#f59e0b]",
  "Validation Error": "bg-[#f0edfe] text-[#7c3aed]",
  Timeout: "bg-[#eef2ff] text-[#4f46e5]",
};

const ROWS = [
  { id: "run_91a2", agent: "Marketing Agent", type: "Tool Error", msg: "SerpAPI rate limit exceeded", time: "12 mins ago" },
  { id: "run_b3c0", agent: "Sales Assistant", type: "LLM Error", msg: "Context length exceeded", time: "1 hour ago" },
  { id: "run_d4e1", agent: "Finance Agent", type: "Validation Error", msg: "Invalid date format", time: "2 hours ago" },
  { id: "run_9fb2", agent: "HR Assistant", type: "Timeout", msg: "Request timed out", time: "3 hours ago" },
  { id: "run_c0b3", agent: "Content Generator", type: "Tool Error", msg: "Notion API returned 403", time: "4 hours ago" },
  { id: "run_e714", agent: "Support Agent", type: "LLM Error", msg: "Model overloaded", time: "6 hours ago" },
];

const TH = ["Run ID", "Agent", "Error Type", "Error Message", "Time", "Actions"];

export const ViewObsErrors = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Errors & Failures"
        subtitle="Failed runs and debugging"
        right={<Pill label="Last 7 days" />}
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {KPIS.map((k) => (
          <KpiCard key={k.label} {...k} />
        ))}
      </div>

      <ObsTabs tabs={["Failures", "Error Types", "Trends", "Recovery Actions"]} active={0} />

      <ObsCard className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left min-w-[760px]">
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
                <tr key={r.id} className="hover:bg-[#f8fafc]">
                  <td className={`${tableCellCls} font-semibold text-[#4f46e5]`}>{r.id}</td>
                  <td className={`${tableCellCls} text-[#334155]`}>{r.agent}</td>
                  <td className={tableCellCls}>
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-[13px] font-semibold ${ERR_TONE[r.type]}`}
                    >
                      {r.type}
                    </span>
                  </td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.msg}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.time}</td>
                  <td className={tableCellCls}>
                    <button className="text-[14px] font-semibold text-[#4f46e5] hover:text-[#4338ca]">
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 pb-4">
          <ObsPagination label="Showing 1-6 of 892 failures" pages={5} active={1} />
        </div>
      </ObsCard>
    </div>
  </div>
);
