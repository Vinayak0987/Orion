import { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

// Global toast notifications. Wrap the app in <ToastProvider> once, then call
// useToast() anywhere: toast.success("Saved"), toast.error("..."), toast.info("...").

const ToastContext = createContext(null);

let _id = 0;

const VARIANTS = {
  success: { Icon: CheckCircle2, bar: "bg-emerald-500", iconCls: "text-emerald-500" },
  error: { Icon: AlertCircle, bar: "bg-rose-500", iconCls: "text-rose-500" },
  info: { Icon: Info, bar: "bg-[#4f46e5]", iconCls: "text-[#4f46e5]" },
};

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (variant, message, duration = 3500) => {
      const id = ++_id;
      setToasts((t) => [...t, { id, variant, message }]);
      if (duration > 0) setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss]
  );

  const toast = {
    success: (m, d) => push("success", m, d),
    error: (m, d) => push("error", m, d ?? 5000),
    info: (m, d) => push("info", m, d),
    dismiss,
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-5 right-5 z-[1000] flex flex-col gap-3 w-[360px] max-w-[calc(100vw-2.5rem)] pointer-events-none">
        {toasts.map((t) => {
          const v = VARIANTS[t.variant] || VARIANTS.info;
          return (
            <div
              key={t.id}
              className="pointer-events-auto flex items-stretch overflow-hidden rounded-xl bg-white shadow-[0_10px_40px_rgba(15,23,42,0.18)] border border-[#e6ebf2] animate-[toastIn_.22s_ease-out]"
              role="status"
            >
              <span className={`w-1.5 shrink-0 ${v.bar}`} />
              <div className="flex items-start gap-3 px-4 py-3.5 flex-1 min-w-0">
                <v.Icon size={19} className={`${v.iconCls} shrink-0 mt-0.5`} strokeWidth={2.2} />
                <p className="text-[14px] text-slate-700 leading-snug flex-1 min-w-0">
                  {t.message}
                </p>
                <button
                  onClick={() => dismiss(t.id)}
                  className="text-slate-300 hover:text-slate-500 shrink-0"
                  aria-label="Dismiss"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Fail soft — if a component renders outside the provider, no-op rather than crash.
    return { success() {}, error() {}, info() {}, dismiss() {} };
  }
  return ctx;
}
