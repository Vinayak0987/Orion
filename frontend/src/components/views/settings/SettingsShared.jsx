import { ChevronDown } from "lucide-react";
import { DirectoryLocation } from "../../ui/DirectoryLocation.jsx";

/* ============================================================================
   Orion Settings — Design System
   A cohesive set of high-quality primitives. Tight modern type scale, soft
   surfaces, indigo accent, consistent 10/12px radii, subtle motion.
   ========================================================================== */

export const T = {
  bg: "#f7f8fb",
  surface: "#ffffff",
  ink: "#0f172a",
  sub: "#64748b",
  faint: "#94a3b8",
  line: "#eceff4",
  lineStrong: "#e2e8f0",
  indigo: "#4f46e5",
  indigoSoft: "#eef2ff",
};

export const pageShellCls =
  "h-full overflow-y-auto scrollbar-hide bg-[#f7f8fb] px-6 py-7 sm:px-9 sm:py-8";

/* --- Page header ---------------------------------------------------------- */
export const SettingsHeader = ({ title, subtitle, action, crumb = "Settings" }) => (
  <div className="mb-7">
    <DirectoryLocation className="mb-4" items={[{ label: crumb }, { label: title }]} />
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[23px] leading-tight font-semibold tracking-[-0.3px] text-[#0f172a]">
          {title}
        </h1>
        <p className="text-[14px] text-[#64748b] mt-1.5">{subtitle}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  </div>
);

/* --- Card with optional header + footer ----------------------------------- */
export const SettingsCard = ({ title, description, headerAction, children, footer, className = "", bodyClassName = "p-5" }) => (
  <section className={`rounded-2xl border border-[#eceff4] bg-white shadow-[0_1px_2px_rgba(15,23,42,0.03),0_8px_24px_-16px_rgba(15,23,42,0.12)] ${className}`}>
    {(title || headerAction) && (
      <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-4 border-b border-[#f1f4f9]">
        <div className="min-w-0">
          {title && <h2 className="text-[15px] font-semibold text-[#0f172a]">{title}</h2>}
          {description && <p className="text-[13px] text-[#64748b] mt-0.5 leading-snug">{description}</p>}
        </div>
        {headerAction}
      </div>
    )}
    <div className={bodyClassName}>{children}</div>
    {footer && <div className="px-5 py-4 bg-[#f8fafc] border-t border-[#f1f4f9] rounded-b-2xl">{footer}</div>}
  </section>
);

export const cardCls =
  "rounded-2xl border border-[#eceff4] bg-white shadow-[0_1px_2px_rgba(15,23,42,0.03),0_8px_24px_-16px_rgba(15,23,42,0.12)]";

export const cardHoverCls =
  cardCls + " transition-all duration-200 hover:shadow-[0_10px_30px_-12px_rgba(15,23,42,0.22)] hover:border-[#d7dcf7]";

/* --- Row (icon · title/sub · action) -------------------------------------- */
export const Row = ({ icon: Icon, iconTint, title, sub, action, last }) => (
  <div className={`flex items-center gap-3.5 py-4 ${!last ? "border-b border-[#f1f4f9]" : ""}`}>
    {Icon && (
      <span className={`w-9 h-9 rounded-[10px] grid place-items-center shrink-0 ${iconTint || "bg-[#eef2ff] text-[#4f46e5]"}`}>
        <Icon size={17} strokeWidth={2} />
      </span>
    )}
    <div className="flex-1 min-w-0">
      <p className="text-[14px] font-semibold text-[#0f172a] leading-tight">{title}</p>
      {sub && <p className="text-[12.5px] text-[#64748b] mt-0.5 leading-snug">{sub}</p>}
    </div>
    {action && <div className="shrink-0 flex items-center gap-2.5">{action}</div>}
  </div>
);

/* --- Inputs --------------------------------------------------------------- */
export const inputCls =
  "w-full h-10 rounded-[10px] border border-[#e2e8f0] bg-white px-3.5 text-[14px] text-[#1e293b] " +
  "outline-none transition-all duration-150 placeholder:text-[#9aa6b8] " +
  "focus:border-[#a5b4fc] focus:ring-[3px] focus:ring-[#eef2ff] hover:border-[#cbd5e1] " +
  "disabled:bg-[#f8fafc] disabled:text-[#94a3b8]";

export const labelCls = "block text-[12.5px] font-medium text-[#475569] mb-1.5";

export const Field = ({ label, hint, children }) => (
  <div>
    {label && <label className={labelCls}>{label}</label>}
    {children}
    {hint && <p className="text-[12px] text-[#94a3b8] mt-1.5">{hint}</p>}
  </div>
);

/* --- Native select, styled ------------------------------------------------ */
export const Select = ({ value, onChange, options, className = "" }) => (
  <div className={`relative ${className}`}>
    <select
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      className={`${inputCls} appearance-none pr-9 cursor-pointer`}
    >
      {options.map((o) =>
        typeof o === "string" ? (
          <option key={o} value={o}>{o}</option>
        ) : (
          <option key={o.value} value={o.value}>{o.label}</option>
        )
      )}
    </select>
    <ChevronDown size={15} className="text-[#94a3b8] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
  </div>
);

/* --- Segmented control (e.g. theme) --------------------------------------- */
export const SegmentedControl = ({ value, onChange, options }) => (
  <div className="inline-flex items-center p-1 rounded-[11px] bg-[#f1f4f9] border border-[#eceff4]">
    {options.map((o) => {
      const val = typeof o === "string" ? o : o.value;
      const label = typeof o === "string" ? o : o.label;
      const Icon = typeof o === "object" ? o.icon : null;
      const active = value === val;
      return (
        <button
          key={val}
          type="button"
          onClick={() => onChange?.(val)}
          className={`inline-flex items-center gap-1.5 h-8 px-3.5 rounded-[8px] text-[13px] font-medium transition-all duration-150 ${
            active ? "bg-white text-[#4f46e5] shadow-[0_1px_2px_rgba(15,23,42,0.08)]" : "text-[#64748b] hover:text-[#334155]"
          }`}
        >
          {Icon && <Icon size={14} strokeWidth={2.2} />}
          {label}
        </button>
      );
    })}
  </div>
);

/* --- Toggle --------------------------------------------------------------- */
export const Toggle = ({ on = false, onChange }) => (
  <button
    type="button"
    onClick={() => onChange?.(!on)}
    className={`w-[42px] h-[24px] rounded-full relative transition-colors duration-200 shrink-0 ${
      on ? "bg-[#4f46e5]" : "bg-[#cbd5e1]"
    } active:scale-95`}
    role="switch"
    aria-checked={on}
  >
    <span
      className={`absolute top-[3px] w-[18px] h-[18px] rounded-full bg-white shadow-[0_1px_3px_rgba(15,23,42,0.25)] transition-all duration-200 ease-out ${
        on ? "left-[21px]" : "left-[3px]"
      }`}
    />
  </button>
);

/* --- Buttons -------------------------------------------------------------- */
export const PrimaryButton = ({ children, className = "", size = "md", ...props }) => {
  const h = size === "sm" ? "h-9 px-3.5 text-[13px]" : "h-10 px-4 text-[14px]";
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 ${h} rounded-[10px] bg-[#4f46e5] text-white font-semibold
        shadow-[0_1px_2px_rgba(79,70,229,0.35)] transition-all duration-150
        hover:bg-[#4338ca] active:scale-[0.98]
        focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#dfe3fb]
        disabled:opacity-55 disabled:cursor-not-allowed disabled:active:scale-100 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export const OutlineButton = ({ children, className = "", size = "md", ...props }) => {
  const h = size === "sm" ? "h-9 px-3.5 text-[13px]" : "h-10 px-4 text-[14px]";
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 ${h} rounded-[10px] border border-[#e2e8f0] bg-white font-semibold text-[#334155]
        transition-all duration-150 hover:bg-[#f8fafc] hover:border-[#cbd5e1] active:scale-[0.98]
        focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#eceff4]
        disabled:opacity-55 disabled:cursor-not-allowed ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export const GhostButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-1.5 h-9 px-3.5 rounded-[10px] border border-[#e2e8f0] bg-white text-[13px] font-semibold text-[#334155]
      transition-all duration-150 hover:bg-[#f8fafc] hover:border-[#c7d2fe] hover:text-[#4f46e5] active:scale-[0.97]
      focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[#eceff4] ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const DangerButton = ({ children, className = "", ...props }) => (
  <button
    className={`inline-flex items-center justify-center gap-1.5 h-9 px-3.5 rounded-[10px] border border-rose-200 bg-white text-[13px] font-semibold text-rose-600
      transition-all duration-150 hover:bg-rose-50 hover:border-rose-300 active:scale-[0.97]
      focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-rose-100 ${className}`}
    {...props}
  >
    {children}
  </button>
);

/* --- Icon tile ------------------------------------------------------------ */
export const IconTile = ({ children, tint = "bg-[#eef2ff] text-[#4f46e5]", size = "md", className = "" }) => {
  const s = size === "lg" ? "w-11 h-11 rounded-xl" : "w-9 h-9 rounded-[10px]";
  return <span className={`${s} grid place-items-center shrink-0 ${tint} ${className}`}>{children}</span>;
};

/* --- Status chip / soon badge --------------------------------------------- */
export const Chip = ({ children, tone = "neutral" }) => {
  const tones = {
    neutral: "bg-[#f1f4f9] text-[#64748b]",
    indigo: "bg-[#eef2ff] text-[#4f46e5]",
    green: "bg-[#e7f8ef] text-[#16a34a]",
    amber: "bg-[#fef3e2] text-[#d97706]",
    rose: "bg-[#fdeaea] text-[#e11d48]",
  };
  return (
    <span className={`inline-flex items-center gap-1 text-[11.5px] font-semibold rounded-full px-2.5 py-0.5 ${tones[tone]}`}>
      {children}
    </span>
  );
};

export const SoonBadge = ({ label = "Coming soon" }) => <Chip tone="neutral">{label}</Chip>;

/* --- Section label (outside cards) ---------------------------------------- */
export const SectionLabel = ({ children, className = "" }) => (
  <h2 className={`text-[13px] font-semibold uppercase tracking-wide text-[#94a3b8] mb-3 ${className}`}>
    {children}
  </h2>
);

/* Back-compat aliases used by older imports */
export const SaveButton = ({ label = "Save Changes", ...props }) => (
  <PrimaryButton {...props}>{label}</PrimaryButton>
);
export const IconTileStatic = IconTile;
export const SectionTitle = ({ children, className = "" }) => (
  <h2 className={`text-[15px] font-semibold text-[#0f172a] ${className}`}>{children}</h2>
);
export const Tabs = ({ tabs, active = 0, onSelect }) => (
  <div className="flex items-center gap-1 border-b border-[#eceff4] mb-6 overflow-x-auto scrollbar-hide">
    {tabs.map((t, i) => (
      <button
        key={t}
        type="button"
        onClick={() => onSelect?.(i)}
        className={`pb-3 pt-1 px-3.5 text-[13.5px] whitespace-nowrap border-b-2 -mb-px transition-colors duration-150 ${
          i === active ? "text-[#4f46e5] border-[#4f46e5] font-semibold" : "text-[#64748b] border-transparent font-medium hover:text-[#334155]"
        }`}
      >
        {t}
      </button>
    ))}
  </div>
);
export const SelectField = ({ label, value }) => (
  <Field label={label}>
    <button className={`${inputCls} flex items-center justify-between hover:bg-slate-50`}>
      <span>{value}</span>
      <ChevronDown size={15} className="text-[#94a3b8]" />
    </button>
  </Field>
);

/* ============================================================
   Neumorphic primitives (soft UI) — opt-in, used by Profile /
   Workspace. Classes defined in index.css.
   ============================================================ */

export const neuInput =
  "neu-input w-full h-11 px-4 text-[14px] text-[#334155] placeholder:text-[#9aa6b8]";

export const NeuField = ({ label, hint, children }) => (
  <div>
    {label && <label className="block text-[12.5px] font-semibold text-[#5b6678] mb-2">{label}</label>}
    {children}
    {hint && <p className="text-[12px] text-[#9aa6b8] mt-1.5">{hint}</p>}
  </div>
);

export const NeuButton = ({ children, className = "", ...props }) => (
  <button
    className={`neu-btn inline-flex items-center justify-center gap-2 h-10 px-5 text-[14px] font-semibold text-[#4f46e5] disabled:opacity-55 ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const NeuPrimaryButton = ({ children, className = "", ...props }) => (
  <button
    className={`neu-btn-primary inline-flex items-center justify-center gap-2 h-10 px-5 text-[14px] font-semibold disabled:opacity-55 ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const NeuIconButton = ({ children, className = "", ...props }) => (
  <button
    className={`neu-circle grid place-items-center rounded-full text-[#4f46e5] ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const NeuGhostButton = ({ children, className = "", ...props }) => (
  <button
    className={`neu-btn-ghost inline-flex items-center justify-center gap-1.5 h-9 px-4 text-[13px] font-semibold ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const NeuDangerButton = ({ children, className = "", ...props }) => (
  <button
    className={`neu-btn-danger inline-flex items-center justify-center gap-1.5 h-9 px-4 text-[13px] font-semibold ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const neuSelect = `neu-input neu-select w-full h-11 px-4 text-[14px] text-[#334155]`;

/* Neumorphic toggle */
export const NeuToggle = ({ on = false, onChange }) => (
  <button
    type="button"
    role="switch"
    aria-checked={on}
    onClick={() => onChange?.(!on)}
    className={`neu-toggle ${on ? "neu-toggle-on" : ""} w-[46px] h-[26px] relative shrink-0`}
  >
    <span
      className={`neu-toggle-knob absolute top-[3px] w-[20px] h-[20px] rounded-full ${on ? "left-[23px]" : "left-[3px]"}`}
    />
  </button>
);

/* Neumorphic segmented control */
export const NeuSegmented = ({ value, onChange, options }) => (
  <div className="neu-seg inline-flex items-center p-1">
    {options.map((o) => {
      const val = typeof o === "string" ? o : o.value;
      const label = typeof o === "string" ? o : o.label;
      const Icon = typeof o === "object" ? o.icon : null;
      const active = value === val;
      return (
        <button
          key={val}
          type="button"
          onClick={() => onChange?.(val)}
          className={`neu-seg-item ${active ? "neu-seg-item-active" : ""} inline-flex items-center gap-1.5 h-8 px-3.5 text-[13px] font-medium`}
        >
          {Icon && <Icon size={14} strokeWidth={2.2} />}
          {label}
        </button>
      );
    })}
  </div>
);

/* Neumorphic chip */
export const NeuChip = ({ children, className = "" }) => (
  <span className={`neu-chip inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#5b6678] px-2.5 py-1 ${className}`}>
    {children}
  </span>
);

/* Neumorphic row (icon well · title/sub · action) */
export const NeuRow = ({ icon: Icon, title, sub, action, last }) => (
  <div className={`flex items-center gap-3.5 py-4 ${!last ? "border-b border-[#e2e6ee]" : ""}`}>
    {Icon && (
      <span className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#4f46e5] shrink-0">
        <Icon size={17} strokeWidth={2} />
      </span>
    )}
    <div className="flex-1 min-w-0">
      <p className="text-[14px] font-semibold text-[#334155] leading-tight">{title}</p>
      {sub && <p className="text-[12.5px] text-[#8792a6] mt-0.5 leading-snug">{sub}</p>}
    </div>
    {action && <div className="shrink-0 flex items-center gap-2.5">{action}</div>}
  </div>
);

/* Neumorphic page shell */
export const neuShellCls = "neu-surface h-full overflow-y-auto scrollbar-hide px-6 py-7 sm:px-9 sm:py-8";

/* Neumorphic section heading */
export const NeuSectionTitle = ({ children, className = "" }) => (
  <h2 className={`text-[15px] font-semibold text-[#334155] ${className}`}>{children}</h2>
);
