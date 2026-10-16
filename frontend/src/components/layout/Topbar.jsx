import { useEffect, useRef, useState } from "react";
import { CalendarDays, User, Settings, LogOut, ChevronDown, Search, Sun, Bell } from "lucide-react";

import { Icon } from "../ui/Icon.jsx";
import { authApi } from "../../auth/authApi.js";

function initials(name) {
  if (!name) return "AM";
  const p = name.trim().split(/\s+/);
  return ((p[0]?.[0] || "") + (p[1]?.[0] || "")).toUpperCase() || "AM";
}

export const Topbar = ({ onLogout, onNavigate }) => {
  const [user, setUser] = useState(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    authApi.me().then(setUser).catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onDoc = (e) => menuRef.current && !menuRef.current.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const name = user?.full_name || "Account";
  const email = user?.email || "";
  const avatarUrl = user?.avatar_url || null;
  const firstName = name.split(/\s+/)[0];

  const today = new Date().toLocaleDateString("en-US", { weekday: "short", day: "numeric", month: "short", year: "numeric" });

  function go(tab) {
    setOpen(false);
    onNavigate?.(tab);
  }

  return (
    <header className="h-16 neu-surface flex items-center justify-between px-6 shrink-0 z-10 relative border-b border-[#e2e6ee]">
      {/* mobile brand */}
      <div className="flex items-center gap-2 md:hidden">
        <span className="neu-circle w-8 h-8 rounded-lg flex items-center justify-center text-[#4f46e5]">
          <Icon name="bars" className="text-xs" />
        </span>
        <span className="font-semibold text-[#334155] text-lg ml-1">Orion AI</span>
      </div>

      {/* Search — inset well */}
      <div className="relative hidden md:block w-full max-w-md ml-1">
        <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#9aa6b8]" />
        <input
          type="text"
          placeholder="Search or type a command…"
          className="neu-input w-full h-10 pl-10 pr-14 text-[14px] text-[#334155]"
        />
        <span className="neu-chip absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-[#8792a6] px-1.5 py-0.5">
          Ctrl K
        </span>
      </div>

      <div className="flex items-center gap-3.5 ml-auto">
        {/* Date — soft raised card */}
        <div className="neu-raised hidden lg:flex items-center gap-3 px-3.5 py-1.5">
          <span className="neu-circle w-8 h-8 rounded-lg grid place-items-center text-[#4f46e5] shrink-0">
            <CalendarDays size={15} strokeWidth={2} />
          </span>
          <div>
            <p className="text-[12px] font-semibold text-[#334155] leading-tight">{today}</p>
            <p className="text-[10px] text-[#9aa6b8] leading-tight mt-0.5">Let&apos;s build what&apos;s next.</p>
          </div>
        </div>

        {/* Theme + bell — raised circle buttons */}
        <button className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#64748b] hover:text-[#4f46e5]" title="Theme">
          <Sun size={17} strokeWidth={2} />
        </button>
        <button className="neu-circle w-9 h-9 rounded-full grid place-items-center text-[#64748b] hover:text-[#4f46e5] relative" title="Notifications">
          <Bell size={17} strokeWidth={2} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-[#eef1f6]" />
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className={`neu-nav ${open ? "neu-nav-active" : ""} flex items-center gap-2.5 pl-1.5 pr-3 py-1.5`}
          >
            {avatarUrl ? (
              <img src={avatarUrl} alt={name} className="w-8 h-8 rounded-full object-cover" />
            ) : (
              <span className="w-8 h-8 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-[12px] font-semibold text-white">
                {initials(name)}
              </span>
            )}
            <span className="text-[13.5px] font-semibold text-[#334155] hidden md:block">{firstName}</span>
            <ChevronDown size={14} className={`text-[#8792a6] hidden md:block transition-transform ${open ? "rotate-180" : ""}`} />
          </button>

          {open && (
            <div className="absolute right-0 top-[calc(100%+10px)] w-64 neu-card py-2 z-50 animate-[toastIn_.15s_ease-out] overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 mb-1.5 border-b border-[#e2e6ee]">
                {avatarUrl ? (
                  <img src={avatarUrl} alt={name} className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <span className="w-10 h-10 rounded-full bg-gradient-to-br from-[#6366f1] to-[#4338ca] grid place-items-center text-[13px] font-semibold text-white">
                    {initials(name)}
                  </span>
                )}
                <div className="min-w-0">
                  <p className="text-[14px] font-semibold text-[#334155] truncate">{name}</p>
                  <p className="text-[12px] text-[#8792a6] truncate">{email}</p>
                </div>
              </div>

              <div className="px-1.5 flex flex-col gap-0.5">
                <MenuItem icon={User} label="Profile" onClick={() => go("settings")} />
                <MenuItem icon={Settings} label="Settings" onClick={() => go("settings-preferences")} />
              </div>

              <div className="mt-1.5 pt-1.5 px-1.5 border-t border-[#e2e6ee]">
                <MenuItem icon={LogOut} label="Log out" danger onClick={() => { setOpen(false); onLogout?.(); }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

function MenuItem({ icon: Icon, label, onClick, danger }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`neu-nav w-full flex items-center gap-3 px-3 py-2.5 text-left text-[14px] font-medium ${
        danger ? "text-[#e11d48]" : "text-[#4a5568]"
      }`}
    >
      <Icon size={17} strokeWidth={2} className={danger ? "text-[#e11d48]" : "text-[#8792a6]"} />
      {label}
    </button>
  );
}
