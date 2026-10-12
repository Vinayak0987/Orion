import { Mail, Smartphone, Megaphone, ChevronDown } from "lucide-react";
import {
  SettingsHeader,
  SaveButton,
  Toggle,
  IconTile,
  pageShellCls,
  cardCls,
  inputCls,
} from "./SettingsShared.jsx";

const Radio = ({ label, checked }) => (
  <label className="flex items-center gap-2 cursor-pointer">
    <span
      className={`w-[18px] h-[18px] rounded-full border-2 grid place-items-center ${
        checked ? "border-[#4f46e5]" : "border-slate-300"
      }`}
    >
      {checked && <span className="w-2.5 h-2.5 rounded-full bg-[#4f46e5]" />}
    </span>
    <span className="text-[14px] font-medium text-[#334155]">{label}</span>
  </label>
);

const PrefRow = ({ label, control, last }) => (
  <div
    className={`flex items-center justify-between gap-6 py-4 ${
      !last ? "border-b border-[#eef2f8]" : ""
    }`}
  >
    <span className="text-[14px] font-bold text-[#0b1220]">{label}</span>
    <div className="shrink-0">{control}</div>
  </div>
);

const Select = ({ value }) => (
  <button className={`w-72 ${inputCls} flex items-center justify-between hover:bg-slate-50`}>
    {value} <ChevronDown size={15} className="text-[#94a3b8]" />
  </button>
);

const NotifRow = ({ icon: Icon, title, sub, on, last }) => (
  <div className={`flex items-center gap-4 py-4 ${!last ? "border-b border-[#eef2f8]" : ""}`}>
    <IconTile>
      <Icon size={19} strokeWidth={2} />
    </IconTile>
    <div className="flex-1 min-w-0">
      <p className="text-[15px] font-bold text-[#0b1220]">{title}</p>
      <p className="text-[13px] text-[#64748b] mt-0.5">{sub}</p>
    </div>
    <Toggle on={on} />
  </div>
);

export const ViewPreferences = () => (
  <div className={pageShellCls}>
    <div className="max-w-[920px]">
      <SettingsHeader
        title="Preferences"
        subtitle="Customize your Orion experience."
        action={<SaveButton />}
      />

      <div className="flex flex-col gap-5">
        <section className={`${cardCls} px-6 pb-2`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] pt-6 mb-2">Appearance</h2>
          <PrefRow
            label="Theme"
            control={
              <div className="flex items-center gap-6">
                <Radio label="Light" checked />
                <Radio label="Dark" />
                <Radio label="System" />
              </div>
            }
          />
          <PrefRow label="Primary Language" control={<Select value="English (US)" />} />
          <PrefRow label="Timezone" control={<Select value="(GMT+05:30) Asia/Kolkata" />} />
          <PrefRow label="Date Format" control={<Select value="Sep 15, 2026" />} />
          <PrefRow label="Time Format" control={<Select value="12 hour (AM/PM)" />} last />
        </section>

        <section className={`${cardCls} px-6 pb-2`}>
          <h2 className="text-[18px] font-extrabold text-[#0b1220] pt-6 mb-2">Notifications</h2>
          <NotifRow icon={Mail} title="Email Notifications" sub="Receive updates via email" on />
          <NotifRow
            icon={Smartphone}
            title="In-App Notifications"
            sub="Show notifications in the app"
            on
          />
          <NotifRow
            icon={Megaphone}
            title="Marketing Updates"
            sub="Product updates and newsletters"
            on={false}
            last
          />
        </section>
      </div>
    </div>
  </div>
);
