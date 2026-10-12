import { CreditCard } from "lucide-react";
import { Tabs, SettingsHeader, PrimaryButton, pageShellCls, cardCls } from "./SettingsShared.jsx";

const UsageBar = ({ label, value, pct }) => (
  <div>
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-[14px] font-medium text-[#64748b]">{label}</span>
      <span className="text-[13px] font-semibold text-[#64748b]">{value}</span>
    </div>
    <div className="h-2 rounded-full bg-[#eef2f8] overflow-hidden">
      <div className="h-full rounded-full bg-[#4f46e5]" style={{ width: `${pct}%` }} />
    </div>
  </div>
);

const invoices = [
  { id: "INV-2026-001", date: "Sep 1, 2026", amount: "₹1,999", status: "Paid", action: "Download" },
  { id: "INV-2026-002", date: "Aug 1, 2026", amount: "₹1,999", status: "Paid", action: "Download" },
  { id: "INV-2026-003", date: "Jul 1, 2026", amount: "₹1,999", status: "Paid", action: "Download" },
  { id: "INV-2026-004", date: "Jun 1, 2026", amount: "₹1,999", status: "Failed", action: "Retry" },
];

export const ViewBilling = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1100px]">
      <SettingsHeader
        title="Billing & Subscription"
        subtitle="Manage your plan, usage and invoices."
      />

      <Tabs tabs={["Overview", "Invoices", "Payment Methods", "Usage"]} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <section className={`${cardCls} p-6`}>
          <div className="flex items-center gap-3 mb-4">
            <span className="w-12 h-12 rounded-xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0">
              <CreditCard size={22} strokeWidth={2} />
            </span>
            <div>
              <p className="text-[12px] text-[#64748b] font-semibold uppercase tracking-wide">
                Current Plan
              </p>
              <p className="text-[18px] font-extrabold text-[#0b1220]">Orion Pro</p>
            </div>
          </div>
          <p className="text-[14px] text-[#64748b] mb-4">Full access to all agents and automations</p>
          <p className="text-[32px] font-extrabold text-[#0b1220] mb-5 tracking-[-0.5px]">
            ₹1,999 <span className="text-[15px] font-medium text-[#94a3b8]">/ month</span>
          </p>
          <PrimaryButton className="w-full">Upgrade Plan</PrimaryButton>
        </section>

        <section className={`${cardCls} p-6`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] mb-5">Usage This Month</h2>
          <div className="flex flex-col gap-4">
            <UsageBar label="Agent Runs" value="12 / 50" pct={24} />
            <UsageBar label="API Calls" value="2,480 / 10K" pct={25} />
            <UsageBar label="Storage" value="14.2 GB / 100 GB" pct={14} />
            <UsageBar label="Team Members" value="12 / 50" pct={24} />
          </div>
        </section>
      </div>

      <section className={`${cardCls} mt-5 overflow-hidden`}>
        <div className="flex items-center justify-between px-6 py-5">
          <h2 className="text-[18px] font-extrabold text-[#0b1220]">Recent Invoices</h2>
          <button className="text-[14px] font-semibold text-[#4f46e5] hover:text-[#4338ca]">
            View All
          </button>
        </div>
        <table className="w-full text-left">
          <thead>
            <tr className="border-y border-[#eef2f8] bg-[#f8fafc]">
              {["Invoice #", "Date", "Amount", "Status", "Action"].map((h) => (
                <th
                  key={h}
                  className="px-6 py-3 text-[12px] font-bold text-[#64748b] uppercase tracking-wide"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv, i) => (
              <tr
                key={inv.id}
                className={i < invoices.length - 1 ? "border-b border-[#eef2f8]" : ""}
              >
                <td className="px-6 py-4 text-[14px] font-semibold text-[#0b1220]">{inv.id}</td>
                <td className="px-6 py-4 text-[14px] text-[#64748b]">{inv.date}</td>
                <td className="px-6 py-4 text-[14px] text-[#64748b]">{inv.amount}</td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-[13px] font-semibold ${
                      inv.status === "Paid"
                        ? "bg-[#e7f8ef] text-[#16a34a]"
                        : "bg-[#fdeaea] text-[#ef4444]"
                    }`}
                  >
                    {inv.status}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button
                    className={`text-[14px] font-semibold ${
                      inv.action === "Retry"
                        ? "text-[#ef4444]"
                        : "text-[#4f46e5] hover:text-[#4338ca]"
                    }`}
                  >
                    {inv.action}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  </div>
);
