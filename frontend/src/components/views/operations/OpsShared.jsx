import { TrendingUp, TrendingDown } from "lucide-react";
import { DirectoryLocation } from "../../ui/DirectoryLocation.jsx";

/* Agents / Tools design baseline for Operations */
export const pageShellCls =
  "min-h-full overflow-y-auto scrollbar-hide bg-[#f8fafc] px-6 py-6 sm:px-7 sm:py-7 space-y-6 max-w-[1400px] mx-auto pb-20";

export const cardCls =
  "bg-white rounded-2xl border border-[#e6ebf2] shadow-[0_8px_26px_rgba(36,45,64,0.045)]";

/**
 * Page header: breadcrumb + icon tile + title + subtitle left, actions right.
 */
export const OpsHeader = ({
  icon: IconEl,
  title,
  subtitle,
  iconTint = "text-[#4f46e5]",
  iconBg = "bg-[#eef2ff]",
  right,
  crumb = "Operations",
}) => (
  <div className="space-y-5">
    <DirectoryLocation
      className="mb-0"
      items={[{ label: crumb }, { label: title }]}
    />
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-center gap-4 min-w-0">
        <div
          className={`w-14 h-14 rounded-2xl ${iconBg} border border-[#e6ebf2] flex items-center justify-center shrink-0`}
        >
          <IconEl size={26} strokeWidth={2} className={iconTint} />
        </div>
        <div className="min-w-0">
          <h1 className="text-[32px] leading-none font-extrabold text-[#0b1220] tracking-[-0.6px]">
            {title}
          </h1>
          <p className="text-[#64748b] mt-2 text-[15px]">{subtitle}</p>
        </div>
      </div>
      {right && <div className="flex items-center gap-3 shrink-0 flex-wrap justify-end">{right}</div>}
    </div>
  </div>
);

export const DropdownPill = ({ label, className = "", dark = false }) => (
  <button
    className={`flex items-center gap-2 h-11 px-4 rounded-xl text-[14px] font-semibold transition-colors ${
      dark
        ? "bg-[#4f46e5] text-white hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)]"
        : "border border-[#e6ebf2] bg-white text-[#334155] hover:bg-[#f5f8fc]"
    } ${className}`}
  >
    {label}
    {!dark && (
      <svg
        viewBox="0 0 24 24"
        className="w-4 h-4 text-[#94a3b8]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    )}
  </button>
);

export const PrimaryButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-2 h-12 px-5 rounded-xl bg-[#4f46e5] text-white text-[15px] font-bold hover:bg-[#4338ca] shadow-[0_4px_12px_rgba(79,70,229,0.28)] transition-colors ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const OutlineButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-2 h-12 px-5 rounded-xl border border-[#e6ebf2] bg-white text-[15px] font-semibold text-[#1e293b] hover:bg-[#f5f8fc] transition-colors ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const StatCards = ({ items }) => (
  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
    {items.map((m, i) => (
      <div key={i} className={`${cardCls} p-5`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[#64748b] text-[14px] font-medium">{m.title}</p>
            <h3 className="text-[30px] font-extrabold text-[#0b1220] leading-tight mt-1.5 tracking-[-0.4px]">
              {m.value}
            </h3>
            {m.trend && (
              <div className="mt-2 flex items-center gap-1 text-[13px] font-semibold">
                {m.trendDir === "down" ? (
                  <TrendingDown
                    size={14}
                    strokeWidth={2.6}
                    className={m.trendColor || "text-[#ef4444]"}
                  />
                ) : (
                  <TrendingUp
                    size={14}
                    strokeWidth={2.6}
                    className={m.trendColor || "text-[#16a34a]"}
                  />
                )}
                <span
                  className={
                    m.trendColor ||
                    (m.trendDir === "down" ? "text-[#ef4444]" : "text-[#16a34a]")
                  }
                >
                  {m.trend}
                </span>
              </div>
            )}
          </div>
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
              m.iconBg || "bg-[#eef2ff]"
            }`}
          >
            <m.icon size={22} strokeWidth={2} className={m.iconTint || "text-[#4f46e5]"} />
          </div>
        </div>
      </div>
    ))}
  </div>
);

export const Tabs = ({ tabs, active, onChange }) => (
  <div className="border-b border-[#eef2f8]">
    <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
      {tabs.map((t) => (
        <button
          key={t}
          onClick={() => onChange && onChange(t)}
          className={`relative pb-3.5 pt-1 px-4 text-[14px] font-semibold whitespace-nowrap transition-colors ${
            active === t
              ? "text-[#4f46e5]"
              : "text-[#64748b] hover:text-[#4f46e5]"
          }`}
        >
          {t}
          {active === t && (
            <span className="absolute -bottom-px left-0 right-0 h-0.5 bg-[#4f46e5] rounded-full" />
          )}
        </button>
      ))}
    </div>
  </div>
);

export const FilterBar = ({ placeholder = "Search...", filters = [], action }) => (
  <div className="flex items-center gap-3 flex-wrap">
    <div className="relative flex-1 min-w-[200px]">
      <svg
        viewBox="0 0 24 24"
        className="w-[18px] h-[18px] absolute left-4 top-1/2 -translate-y-1/2 text-[#94a3b8]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        type="text"
        placeholder={placeholder}
        className="w-full h-12 rounded-xl border border-[#e6ebf2] bg-white pl-11 pr-4 text-[15px] text-[#1e293b] placeholder:text-[#94a3b8] outline-none focus:border-[#a5b4fc] focus:ring-2 focus:ring-[#eef2ff]"
      />
    </div>
    {filters.map((f, i) => (
      <button
        key={i}
        className="flex items-center justify-between gap-6 h-12 px-4 rounded-xl border border-[#e6ebf2] bg-white text-[15px] font-medium text-[#64748b] hover:bg-[#f5f8fc] whitespace-nowrap"
      >
        {f}
        <svg
          viewBox="0 0 24 24"
          className="w-4 h-4 text-[#94a3b8]"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
    ))}
    {action}
  </div>
);

export const Pagination = ({ label, pages = 5, active = 1 }) => (
  <div className="flex items-center justify-between pt-1">
    <p className="text-[14px] text-[#64748b]">{label}</p>
    <div className="flex items-center gap-2">
      <button className="w-10 h-10 rounded-lg border border-[#e6ebf2] bg-white flex items-center justify-center text-[#64748b] hover:bg-[#f5f8fc]">
        <svg
          viewBox="0 0 24 24"
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
        <button
          key={n}
          className={`w-10 h-10 rounded-lg text-[14px] font-semibold flex items-center justify-center transition-colors ${
            n === active
              ? "bg-[#4f46e5] text-white border border-[#4f46e5]"
              : "border border-[#e6ebf2] bg-white text-[#64748b] hover:bg-[#f5f8fc]"
          }`}
        >
          {n}
        </button>
      ))}
      <button className="w-10 h-10 rounded-lg border border-[#e6ebf2] bg-white flex items-center justify-center text-[#64748b] hover:bg-[#f5f8fc]">
        <svg
          viewBox="0 0 24 24"
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>
    </div>
  </div>
);

export const StatusPill = ({ label, tone = "green" }) => {
  const tones = {
    green: "bg-[#e7f8ef] text-[#16a34a]",
    amber: "bg-[#fef3e2] text-[#f59e0b]",
    red: "bg-[#fdeaea] text-[#ef4444]",
    blue: "bg-[#eef2ff] text-[#4f46e5]",
    gray: "bg-[#eef2f8] text-[#64748b]",
  };
  const dots = {
    green: "bg-[#16a34a]",
    amber: "bg-[#f59e0b]",
    red: "bg-[#ef4444]",
    blue: "bg-[#4f46e5]",
    gray: "bg-[#94a3b8]",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[13px] font-semibold ${
        tones[tone] || tones.gray
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dots[tone] || dots.gray}`} />
      {label}
    </span>
  );
};
