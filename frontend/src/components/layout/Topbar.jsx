import { Icon, OutlineIcon } from "../ui/Icon.jsx";
import { Avatar } from "../ui/Avatar.jsx";
import { CalendarDays } from "lucide-react";

export const Topbar = ({ onLogout }) => (
  <header className="h-16 bg-white border-b border-[#eef2f8] flex items-center justify-between px-6 shrink-0 z-10 shadow-sm relative">
    <div className="flex items-center gap-2">
      <div className="w-6 h-6 rounded bg-[#4f46e5] text-white flex items-center justify-center shadow-sm md:hidden">
        <Icon name="bars" className="text-xs" />
      </div>
      <span className="font-bold text-slate-800 text-lg md:hidden ml-2">Orion AI</span>
    </div>

    {/* Search moved here from the sidebar */}
    <div className="relative hidden md:block w-full max-w-md ml-2">
      <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm" />
      <input
        type="text"
        placeholder="Search or type a command..."
        className="w-full bg-[#f5f7fb] border border-[#eef2f8] rounded-lg py-2 pl-9 pr-12 text-sm focus:outline-none focus:bg-white focus:border-[#a5b4fc] focus:ring-1 focus:ring-[#c7d2fe] transition-shadow"
      />
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400 border border-[#e6ebf2] rounded px-1.5 py-0.5 bg-white">
        Ctrl K
      </div>
    </div>

    <div className="flex items-center gap-5 ml-auto">
      {/* Calendar card */}
      <div className="flex items-center gap-3 bg-white px-4 py-2 rounded-xl border border-[#e6ebf2] shadow-sm">
        <div className="w-8 h-8 rounded-lg bg-[#eef2ff] text-[#4f46e5] flex items-center justify-center shrink-0">
          <CalendarDays size={16} strokeWidth={2} />
        </div>
        <div>
          <p className="text-xs font-bold text-slate-800 leading-tight">Thu, 19 Sep 2026</p>
          <p className="text-[10px] text-slate-400 leading-tight mt-0.5">Let&apos;s build what&apos;s next.</p>
        </div>
      </div>

      <button className="text-slate-400 hover:text-slate-600 transition-colors">
        <OutlineIcon name="sun" className="text-xl" />
      </button>
      <div className="relative">
        <button className="text-slate-400 hover:text-slate-600 transition-colors">
          <OutlineIcon name="bell" className="text-xl" />
        </button>
        <div className="absolute top-0 right-0 -mt-1 -mr-1 w-2.5 h-2.5 bg-rose-500 border-2 border-white rounded-full"></div>
      </div>

      <div className="h-6 w-px bg-slate-200 mx-1"></div>

      <button
        type="button"
        onClick={onLogout}
        title="Account — Click to sign out"
        className="flex items-center gap-2.5 hover:bg-slate-50 p-1.5 pr-2.5 rounded-full border border-transparent hover:border-slate-200 transition-all cursor-pointer"
      >
        <Avatar initials="AM" color="bg-[#eef2ff] text-[#4338ca]" size="w-8 h-8" />
        <span className="text-sm font-bold text-slate-700 hidden md:block">Abhishek</span>
        <Icon name="chevron-down" className="text-[10px] text-slate-400 hidden md:block mt-0.5" />
      </button>
    </div>
  </header>
);
