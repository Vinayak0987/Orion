import { Copy, MoreHorizontal, ChevronDown } from "lucide-react";
import {
  Tabs,
  SettingsHeader,
  PrimaryButton,
  pageShellCls,
  cardCls,
  inputCls,
  labelCls,
} from "./SettingsShared.jsx";

const keys = [
  {
    name: "Production Key",
    value: "sk_live_••••••••••••••••4821",
    created: "Created Jan 12, 2026",
    used: "Last used 1 hour ago",
    status: "Active",
  },
  {
    name: "Development Key",
    value: "sk_dev_••••••••••••••••09fa",
    created: "Created Feb 3, 2026",
    used: "Last used 1 day ago",
    status: "Active",
  },
  {
    name: "Testing Key",
    value: "sk_test_••••••••••••••••7c3d",
    created: "Created Mar 10, 2026",
    used: "Last used 5 days ago",
    status: "Inactive",
  },
];

const KeyRow = ({ k, last }) => (
  <div className={`flex items-center gap-4 py-5 ${!last ? "border-b border-[#eef2f8]" : ""}`}>
    <div className="flex-1 min-w-0">
      <p className="text-[15px] font-bold text-[#0b1220] mb-1.5">{k.name}</p>
      <div className="flex items-center gap-2">
        <code className="text-[13px] font-mono text-[#64748b] truncate">{k.value}</code>
        <button className="text-[#94a3b8] hover:text-[#4f46e5] shrink-0">
          <Copy size={15} />
        </button>
      </div>
    </div>
    <div className="text-right shrink-0 hidden sm:block">
      <p className="text-[13px] text-[#64748b]">{k.created}</p>
      <p className="text-[12.5px] text-[#94a3b8] mt-0.5">{k.used}</p>
    </div>
    <span
      className={`px-3 py-1 rounded-full text-[13px] font-semibold shrink-0 ${
        k.status === "Active"
          ? "bg-[#e7f8ef] text-[#16a34a]"
          : "bg-[#eef2f8] text-[#64748b]"
      }`}
    >
      ● {k.status}
    </span>
    <button className="text-[#94a3b8] hover:text-[#4f46e5] shrink-0">
      <MoreHorizontal size={18} />
    </button>
  </div>
);

const Select = ({ value }) => (
  <button className={`${inputCls} flex items-center justify-between hover:bg-slate-50`}>
    {value} <ChevronDown size={15} className="text-[#94a3b8]" />
  </button>
);

export const ViewApiAccess = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1000px]">
      <SettingsHeader
        title="API Access"
        subtitle="Manage API keys and developer settings."
        action={<PrimaryButton>Create New Key</PrimaryButton>}
      />

      <Tabs tabs={["API Keys", "Webhooks", "Documentation"]} active={0} />

      <div className="flex flex-col gap-5">
        <section className={`${cardCls} px-6`}>
          {keys.map((k, i) => (
            <KeyRow key={k.name} k={k} last={i === keys.length - 1} />
          ))}
        </section>

        <section className={`${cardCls} p-6`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] mb-5">Developer Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <label className={labelCls}>Rate Limit</label>
              <Select value="100 requests/minute" />
            </div>
            <div>
              <label className={labelCls}>Default Version</label>
              <Select value="v1" />
            </div>
            <div>
              <label className={labelCls}>Webhook URL</label>
              <input
                className={inputCls}
                defaultValue="https://your-app.com/webhook"
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
);
