import { Pencil, ImageUp } from "lucide-react";
import {
  Tabs,
  SettingsHeader,
  SaveButton,
  SelectField,
  Field,
  pageShellCls,
  cardCls,
  inputCls,
} from "./SettingsShared.jsx";

const InfoStat = ({ label, value }) => (
  <div>
    <p className="text-[13px] text-[#64748b] font-medium">{label}</p>
    <p className="text-[20px] font-extrabold text-[#0b1220] mt-1 tracking-[-0.3px]">{value}</p>
  </div>
);

export const ViewWorkspaceSettings = () => (
  <div className={pageShellCls}>
    <div className="max-w-[1100px]">
      <SettingsHeader
        title="Workspace Settings"
        subtitle="Manage your workspace configuration and team members."
        action={<SaveButton />}
      />

      <Tabs tabs={["Overview", "Members", "Roles", "Teams", "Usage"]} active={0} />

      <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_1fr] gap-5">
        <section className="flex flex-col gap-5">
          <Field label="Workspace Name">
            <input className={inputCls} defaultValue="Orion AI" />
          </Field>
          <Field label="Workspace Description">
            <input className={inputCls} defaultValue="A powerful business automation platform" />
          </Field>
          <Field label="Workspace Logo">
            <button className="w-full h-[100px] rounded-2xl border border-dashed border-[#c7d2e5] bg-white flex flex-col items-center justify-center gap-1.5 hover:bg-[#f5f8fc] hover:border-[#4f46e5]/70 transition-colors">
              <ImageUp size={22} className="text-[#4f46e5]" />
              <span className="text-[14px] font-semibold text-[#1e293b]">Click to upload</span>
              <span className="text-[12px] text-[#94a3b8]">PNG, JPG up to 5MB</span>
            </button>
          </Field>
          <SelectField label="Default Timezone" value="(GMT+05:30) Asia/Kolkata" />
          <SelectField label="Default Language" value="English (US)" />
        </section>

        <section className={`${cardCls} p-6 h-fit`}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-[18px] font-extrabold text-[#0b1220]">Workspace Info</h2>
            <button className="flex items-center gap-1.5 text-[13px] font-semibold text-[#64748b] hover:text-[#4f46e5]">
              <Pencil size={14} /> Edit
            </button>
          </div>

          <div className="flex items-center gap-3.5 mb-6">
            <div className="w-12 h-12 rounded-xl bg-[#4f46e5] grid place-items-center text-white shrink-0 shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
              <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
                <path d="M12 2 15 9l7 3-7 3-3 7-3-7-7-3 7-3z" />
              </svg>
            </div>
            <div>
              <p className="text-[16px] font-bold text-[#0b1220]">Orion AI</p>
              <p className="text-[13px] text-[#64748b]">A powerful business automation platform</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-y-6 gap-x-4 border-t border-[#eef2f8] pt-6">
            <InfoStat label="Members" value="12" />
            <InfoStat label="Teams" value="4" />
            <InfoStat label="Created On" value="Jan 12, 2026" />
            <InfoStat label="Plan" value="Pro" />
          </div>
        </section>
      </div>
    </div>
  </div>
);
