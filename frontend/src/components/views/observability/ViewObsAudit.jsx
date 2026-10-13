import {
  ObsTitleBar, Pill, ObsPagination, ObsCard, pageShellCls, tableHeadCls, tableCellCls,
} from "./ObsShared.jsx";
import { Download, Calendar } from "lucide-react";

const ROWS = [
  { ts: "Sep 18, 10:24 AM", user: "abhishek@ori.ai", action: "Run Agent", resource: "Marketing Agent", details: "Started new run" },
  { ts: "Sep 18, 10:18 AM", user: "priya@ori.ai", action: "Update Settings", resource: "Agent Config", details: "Changed temperature" },
  { ts: "Sep 18, 09:55 AM", user: "rahul@ori.ai", action: "Add Tool", resource: "SerpAPI", details: "Added new integration" },
  { ts: "Sep 18, 08:32 AM", user: "system", action: "Run Failed", resource: "Sales Assistant", details: "Tool error: rate limit" },
  { ts: "Sep 18, 08:14 AM", user: "neha@ori.ai", action: "Delete Memory", resource: "Customer Data", details: "Deleted 12 memories" },
  { ts: "Sep 18, 08:02 AM", user: "amit@ori.ai", action: "Add Agent", resource: "Finance Agent", details: "Created new agent" },
  { ts: "Sep 18, 07:58 AM", user: "system", action: "Model Error", resource: "GPT-4o", details: "Model overloaded" },
  { ts: "Sep 18, 07:24 AM", user: "vikas@ori.ai", action: "Export Data", resource: "Logs", details: "Exported audit logs" },
];

const TH = ["Timestamp", "User", "Action", "Resource", "Details"];

export const ViewObsAudit = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1400px] mx-auto">
      <ObsTitleBar
        title="Audit Logs"
        subtitle="System and user activity logs"
        right={
          <>
            <Pill label="All Agents" />
            <Pill label="All Actions" />
            <Pill label="Sep 1, 2026 - Sep 18, 2026" icon={Calendar} />
            <Pill label="Export" dark icon={Download} />
          </>
        }
      />

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
              {ROWS.map((r, i) => (
                <tr key={i} className="hover:bg-[#f8fafc]">
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.ts}</td>
                  <td className={`${tableCellCls} text-[#334155]`}>{r.user}</td>
                  <td className={`${tableCellCls} font-semibold text-[#0b1220]`}>{r.action}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.resource}</td>
                  <td className={`${tableCellCls} text-[#64748b]`}>{r.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 pb-4">
          <ObsPagination label="Showing 1-8 of 1,246 logs" pages={5} active={1} />
        </div>
      </ObsCard>
    </div>
  </div>
);
