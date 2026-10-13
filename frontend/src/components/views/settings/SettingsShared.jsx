import { ChevronDown } from "lucide-react";
import { DirectoryLocation } from "../../ui/DirectoryLocation.jsx";

/* Design tokens aligned with Agents / Tools pages */
export const settingsTokens = {
  bg: "#f8fafc",
  ink: "#0b1220",
  muted: "#64748b",
  soft: "#94a3b8",
  line: "#e6ebf2",
  indigo: "#4f46e5",
  indigoDark: "#4338ca",
  cardRadius: "16px",
};

export const pageShellCls =
  "h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7";

export const cardCls =
  "rounded-2xl border border-[#e6ebf2] bg-white shadow-[0_8px_26px_rgba(36,45,64,0.045)]";

export const inputCls =
  "w-full h-12 rounded-xl border border-[#e6ebf2] bg-white px-4 text-[15px] text-[#1e293b] outline-none focus:border-[#a5b4fc] focus:ring-2 focus:ring-[#eef2ff]";

export const labelCls = "block text-[14px] font-semibold text-[#64748b] mb-2";

export const Field = ({ label, children }) => (
  <div>
    <label className={labelCls}>{label}</label>
    {children}
  </div>
);

/* Indigo toggle — matches Agents/Tools accent */
export const Toggle = ({ on = false }) => (
  <span
    className={`w-11 h-6 rounded-full relative transition-colors shrink-0 ${
      on ? "bg-[#4f46e5]" : "bg-slate-300"
    }`}
  >
    <span
      className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${
        on ? "right-0.5" : "left-0.5"
      }`}
    />
  </span>
);

/* Horizontal tabs — indigo underline like Agents/Tools subtabs */
export const Tabs = ({ tabs, active = 0 }) => (
  <div className="flex items-center gap-1 border-b border-[#eef2f8] mb-6 overflow-x-auto scrollbar-hide">
    {tabs.map((t, i) => (
      <button
        key={t}
        className={`pb-3.5 pt-1 px-4 text-[14px] font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors ${
          i === active
            ? "text-[#4f46e5] border-[#4f46e5]"
            : "text-[#64748b] border-transparent hover:text-[#4f46e5]"
        }`}
      >
        {t}
      </button>
    ))}
  </div>
);

export const SettingsHeader = ({ title, subtitle, action, crumb = "Settings & Profile" }) => (
  <div className="mb-6">
    <DirectoryLocation
      className="mb-5"
      items={[{ label: crumb }, { label: title }]}
    />
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[32px] leading-none font-extrabold tracking-[-0.6px] text-[#0b1220]">
          {title}
        </h1>
        <p className="text-[15px] text-[#64748b] mt-2">{subtitle}</p>
      </div>
      {action}
    </div>
  </div>
);

export const SaveButton = ({ label = "Save Changes" }) => (
  <button className="h-12 px-6 rounded-xl bg-[#4f46e5] text-white text-[15px] font-bold shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca] shrink-0 transition-colors">
    {label}
  </button>
);

export const PrimaryButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl bg-[#4f46e5] text-white text-[15px] font-bold shadow-[0_4px_12px_rgba(79,70,229,0.28)] hover:bg-[#4338ca] transition-colors ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const OutlineButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-[15px] font-semibold text-[#1e293b] hover:bg-[#f1f4f9] transition-colors ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const GhostButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-2 h-9 px-4 rounded-lg border border-[#e6ebf2] bg-white text-[13.5px] font-semibold text-[#334155] hover:bg-[#f5f8fc] transition-colors ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const SelectField = ({ label, value }) => (
  <div>
    {label && <label className={labelCls}>{label}</label>}
    <button className={`${inputCls} flex items-center justify-between hover:bg-slate-50`}>
      <span>{value}</span>
      <ChevronDown size={17} className="text-[#94a3b8]" />
    </button>
  </div>
);

export const IconTile = ({ children, className = "" }) => (
  <span
    className={`w-11 h-11 rounded-xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center shrink-0 ${className}`}
  >
    {children}
  </span>
);
