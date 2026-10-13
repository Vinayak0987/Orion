import {
  ObsTitleBar, KpiCard, Pill, StatusChip, ObsPagination, ObsCard, pageShellCls, tableHeadCls, tableCellCls,
} from "./ObsShared.jsx";
import { Activity, CheckCircle2, XCircle, Ban, Download, Calendar, MoreHorizontal } from "lucide-react";

const KPIS = [
  { icon: Activity, label: "Total Runs", value: "12,481", trend: "18.1%", up: true, iconBg: "bg-[#eef2ff]", iconTint: "text-[#4f46e5]" },
  { icon: CheckCircle2, label: "Successful", value: "11,246", trend: "9.1%", up: true, iconBg: "bg-[#e7f8ef]", iconTint: "text-[#16a34a]" },
  { icon: XCircle, label: "Failed", value: "892", trend: "8.6%", up: false, iconBg: "bg-[#fdeaea]", iconTint: "text-[#ef4444]" },
  { icon: Ban, label: "Canceled", value: "343", trend: "2.3%", up: true, iconBg: "bg-[#eef2f8]", iconTint: "text-[#64748b]" },
];

const ROWS = [
  { id: "run_7f1e2", agent: "Research Agent", input: "Analyze market…", status: "Success", tone: "green", dur: "1m 24s", cost: "$0.012", started: "2 mins ago" },
  { id: "run_9bc1", agent: "Marketing Agent", input: "Create campa…", status: "Success", tone: "green", dur: "3m 12s", cost: "$0.034", started: "8 mins ago" },
  { id: "run_4d2e", agent: "Sales Assistant", input: "Find leads…", status: "Failed", tone: "red", dur: "52s", cost: "$0.007", started: "12 mins ago" },
  { id: "run_0h67", agent: "Data Analyst", input: "Generate repor…", status: "Success", tone: "green", dur: "4m 21s", cost: "$0.056", started: "20 mins ago" },
  { id: "run_d1h7", agent: "Finance Agent", input: "Analyze spend…", status: "Running", tone: "blue", dur: "2m 8s", cost: "$0.021", started: "32 mins ago" },
  { id: "run_e6b4", agent: "HR Assistant", input: "Screen resume…", status: "Failed", tone: "red", dur: "1m 11s", cost: "$0.011", started: "1 hour ago" },
  { id: "run_f7b0", agent: "Content Generator", input: "Write blog…", status: "Success", tone: "green", dur: "3m 46s", cost: "$0.028", started: "2 hours ago" },
  { id: "run_611c5", agent: "Customer Support", input: "Resolve ticket…", status: "Canceled", tone: "amber", dur: "6m 2s", cost: "$0.041", started: "2 hours ago" },
];

const TH = ["Run ID", "Agent / Workflow", "Input", "Status", "Duration", "Cost", "Started At", "Actions"];

export const ViewObsRuns = ({ onOpenTrace }) => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Runs / Sessions"
        subtitle="List of all agent runs"
        right={
          <>
            <Pill label="All Agents" />
            <Pill label="All Status" />
            <Pill label="Sep 1, 2026 - Sep 18, 2026" icon={Calendar} />
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
          <table className="w-full text-left min-w-[860px]">
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
                <tr
                  key={r.id}
                  className="hover:bg-[#f8fafc] cursor-pointer"
                  onClick={onOpenTrace}
                >
                  <td className={`${tableCellCls} font-semibold text-[#4f46e5]`}>{r.id}</td>
                  <td className={`${tableCellCls} text-[#334155]`}>{r.agent}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.input}</td>
                  <td className={tableCellCls}>
                    <StatusChip label={r.status} tone={r.tone} />
                  </td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.dur}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.cost}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.started}</td>
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
        <div className="px-4 pb-4">
          <ObsPagination label="Showing 1-8 of 12,481 runs" pages={5} active={1} />
        </div>
      </ObsCard>
    </div>
  </div>
);
