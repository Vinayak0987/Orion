import { useEffect } from "react";
import { X } from "lucide-react";

// Reusable modal. Backdrop blur, scale-in animation, Esc to close, click-outside
// to close, body-scroll lock. Sizes: sm | md | lg.
//
//   <Modal open={open} onClose={...} title="..." icon={Icon} size="md">
//     ...content...
//   </Modal>

const SIZES = { sm: "max-w-sm", md: "max-w-md", lg: "max-w-lg", xl: "max-w-2xl" };

export function Modal({ open, onClose, title, subtitle, icon: Icon, size = "md", children, footer }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] bg-slate-900/50 grid place-items-center p-4 animate-[toastIn_.15s_ease-out]"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div
        className={`w-full ${SIZES[size] || SIZES.md} bg-[#eef1f6] rounded-2xl shadow-[0_20px_60px_rgba(15,23,42,0.35)] overflow-hidden animate-[modalPop_.18s_cubic-bezier(.16,1,.3,1)]`}
        role="dialog"
        aria-modal="true"
      >
        {(title || Icon) && (
          <div className="flex items-start gap-3 px-6 pt-6 pb-4">
            {Icon && (
              <span className="neu-circle w-10 h-10 rounded-xl grid place-items-center text-[#4f46e5] shrink-0 mt-0.5">
                <Icon size={18} strokeWidth={2} />
              </span>
            )}
            <div className="flex-1 min-w-0">
              {title && <h3 className="text-[16px] font-semibold text-[#334155] leading-tight">{title}</h3>}
              {subtitle && <p className="text-[13px] text-[#8792a6] mt-1">{subtitle}</p>}
            </div>
            <button
              onClick={onClose}
              className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#8792a6] hover:text-[#334155] shrink-0"
              aria-label="Close"
            >
              <X size={17} />
            </button>
          </div>
        )}

        <div className="px-6 pb-6 text-[14px] text-[#5b6678] leading-relaxed">{children}</div>

        {footer && (
          <div className="px-6 py-4 flex items-center justify-end gap-2.5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
