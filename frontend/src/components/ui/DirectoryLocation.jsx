import { ChevronRight } from "lucide-react";

/**
 * Directory-location breadcrumb — matches Knowledge & Memory pages.
 * items: [{ label, onClick? }] — last item is the current page (indigo).
 */
export const DirectoryLocation = ({ items = [], className = "" }) => {
  if (!items.length) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex items-center flex-wrap gap-2 text-[14px] font-medium mb-5 ${className}`}
    >
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={`${item.label}-${i}`} className="flex items-center gap-2 min-w-0">
            {i > 0 && <ChevronRight size={15} className="text-slate-300 shrink-0" />}
            {isLast ? (
              <span className="text-[#4f46e5] truncate">{item.label}</span>
            ) : item.onClick ? (
              <button
                type="button"
                onClick={item.onClick}
                className="text-slate-400 hover:text-[#4f46e5] transition-colors truncate"
              >
                {item.label}
              </button>
            ) : (
              <span className="text-slate-400 truncate">{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
};
