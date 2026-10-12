import { TrendingUp, TrendingDown, ChevronDown, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { DirectoryLocation } from "../../ui/DirectoryLocation.jsx";

/* Shared shell — Agents / Tools baseline */
export const pageShellCls =
  "h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7";

export const cardCls =
  "bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]";

export const ObsCard = ({ children, className = "" }) => (
  <div className={`${cardCls} ${className}`}>{children}</div>
);

/* Page title — breadcrumb + H1 32px / 800, muted subtitle */
export const ObsTitleBar = ({ title, subtitle, right, crumb = "Observability" }) => (
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
        {subtitle && <p className="text-[15px] text-[#64748b] mt-2">{subtitle}</p>}
      </div>
      {right && <div className="flex items-center gap-2.5 shrink-0 flex-wrap justify-end">{right}</div>}
    </div>
  </div>
);

/* KPI card — icon tile + value + label + trend */
export const KpiCard = ({
  icon: Icon,
  label,
  value,
  trend,
  up = true,
  iconBg = "bg-[#eef2ff]",
  iconTint = "text-[#4f46e5]",
}) => (
  <div className={`${cardCls} p-5`}>
    <div className="flex items-center gap-4">
      <span className={`w-12 h-12 rounded-xl grid place-items-center shrink-0 ${iconBg} ${iconTint}`}>
        <Icon size={22} strokeWidth={2} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-medium text-[#64748b] mb-1">{label}</p>
        <div className="flex items-baseline gap-2 flex-wrap">
          <p className="text-[28px] font-extrabold text-[#0b1220] leading-none tracking-[-0.4px]">
            {value}
          </p>
          {trend && (
            <span
              className={`inline-flex items-center gap-0.5 text-[13px] font-bold ${
                up ? "text-[#16a34a]" : "text-[#ef4444]"
              }`}
            >
              {up ? <TrendingUp size={13} strokeWidth={2.6} /> : <TrendingDown size={13} strokeWidth={2.6} />}
              {trend}
            </span>
          )}
        </div>
      </div>
    </div>
  </div>
);

/* Pill control — outline or indigo primary */
export const Pill = ({ label, dark = false, icon: Icon }) => (
  <button
    className={`flex items-center gap-2 h-11 px-4 rounded-xl text-[14px] font-semibold whitespace-nowrap transition-colors ${
      dark
        ? "bg-[#4f46e5] text-white hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)]"
        : "border border-[#e6ebf2] bg-white text-[#334155] hover:bg-[#f5f8fc]"
    }`}
  >
    {Icon && <Icon size={16} strokeWidth={2.2} />}
    {label}
    {!Icon && !dark && <ChevronDown size={15} className="text-[#94a3b8]" />}
  </button>
);

/* Tabs — indigo underline like Agents/Tools */
export const ObsTabs = ({ tabs, active = 0 }) => (
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

export const SearchInput = ({ placeholder = "Search..." }) => (
  <div className="relative flex-1">
    <Search
      size={17}
      className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94a3b8]"
      strokeWidth={2.1}
    />
    <input
      placeholder={placeholder}
      className="w-full h-12 rounded-xl border border-[#e6ebf2] bg-white pl-11 pr-4 text-[15px] text-[#1e293b] placeholder:text-[#94a3b8] outline-none focus:border-[#a5b4fc] focus:ring-2 focus:ring-[#eef2ff]"
    />
  </div>
);

export const StatusChip = ({ label, tone = "green" }) => {
  const map = {
    green: "bg-[#e7f8ef] text-[#16a34a]",
    amber: "bg-[#fef3e2] text-[#f59e0b]",
    red: "bg-[#fdeaea] text-[#ef4444]",
    blue: "bg-[#eef2ff] text-[#4f46e5]",
    gray: "bg-[#eef2f8] text-[#64748b]",
  };
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-[13px] font-semibold ${
        map[tone] || map.gray
      }`}
    >
      {label}
    </span>
  );
};

export const ObsPagination = ({ label, pages = 5, active = 1 }) => (
  <div className="flex items-center justify-between pt-4">
    <p className="text-[13px] text-[#64748b]">{label}</p>
    <div className="flex items-center gap-1.5">
      <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] bg-white grid place-items-center text-[#64748b] hover:bg-[#f5f8fc]">
        <ChevronLeft size={15} />
      </button>
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
        <button
          key={n}
          className={`w-9 h-9 rounded-lg text-[13px] font-semibold grid place-items-center transition-colors ${
            n === active
              ? "bg-[#4f46e5] text-white"
              : "border border-[#e6ebf2] bg-white text-[#64748b] hover:bg-[#f5f8fc]"
          }`}
        >
          {n}
        </button>
      ))}
      <span className="text-[#94a3b8] px-1">…</span>
      <button className="w-9 h-9 rounded-lg border border-[#e6ebf2] bg-white grid place-items-center text-[#64748b] hover:bg-[#f5f8fc]">
        <ChevronRight size={15} />
      </button>
    </div>
  </div>
);

export const PanelTitle = ({ children, className = "" }) => (
  <h2 className={`text-[18px] font-extrabold text-[#0b1220] ${className}`}>{children}</h2>
);

export const tableHeadCls =
  "px-4 py-3 text-[12px] font-bold text-[#64748b] uppercase tracking-wide";
export const tableCellCls = "px-4 py-3.5 text-[14px]";
export const linkCls = "text-[#4f46e5] font-semibold hover:text-[#4338ca]";
