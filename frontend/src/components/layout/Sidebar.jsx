import { useEffect, useState } from "react";
import { Icon } from "../ui/Icon.jsx";
import {
  House,
  MessageSquareMore,
  Target,
  CircleCheck,
  Bell,
  Network,
  Users,
  Database,
  Wrench,
  Gauge,
  SlidersHorizontal,
  ChevronDown,
  ArrowUpRight,
} from "lucide-react";
import {
  NAV_ITEMS,
  WORKSPACE_ITEMS,
  AGENTS_SUBTABS,
  TOOLS_SUBTABS,
  KNOWLEDGE_SUBTABS,
  OPERATIONS_SUBTABS,
  OBSERVABILITY_SUBTABS,
  DEPARTMENTS_SUBTABS,
} from "../../data/navigation.js";

const NAV_ICONS = {
  dashboard: House,
  "command-center": MessageSquareMore,
  missions: Target,
  approvals: CircleCheck,
  notifications: Bell,
  departments: Network,
  agents: Users,
  knowledge: Database,
  tools: Wrench,
  operations: SlidersHorizontal,
  observability: Gauge,
};

const BADGE_COLORS = {
  rose: "bg-rose-100 text-rose-600",
  indigo: "bg-[#eef2ff] text-[#4f46e5]",
};

const EXPANDABLE = {
  agents: AGENTS_SUBTABS,
  tools: TOOLS_SUBTABS,
  knowledge: KNOWLEDGE_SUBTABS,
  operations: OPERATIONS_SUBTABS,
  observability: OBSERVABILITY_SUBTABS,
  departments: DEPARTMENTS_SUBTABS,
};

const isGroupActive = (itemId, activeView) => {
  if (itemId === "knowledge") return activeView === "knowledge" || activeView.startsWith("knowledge-");
  if (itemId === "operations") return activeView === "operations" || activeView.startsWith("operations-");
  if (itemId === "observability") return activeView === "observability" || activeView.startsWith("observability-");
  if (itemId === "departments") {
    return (
      activeView === "departments" ||
      activeView === "create-department" ||
      activeView === "department-marketing" ||
      activeView === "department-finance" ||
      activeView === "department-operations" ||
      activeView === "department-sales" ||
      activeView === "department-hr" ||
      activeView === "department-research" ||
      activeView.startsWith("marketing-") ||
      activeView.startsWith("finance-") ||
      activeView.startsWith("sales-") ||
      activeView.startsWith("hr-") ||
      activeView.startsWith("research-")
    );
  }
  return activeView === itemId;
};

const NavRow = ({ item, isActive, onClick, expandable = false, open = false, onToggle }) => {
  const IconCmp = NAV_ICONS[item.id] || House;
  return (
    <div
      className={`group flex items-center gap-1 rounded-2xl transition-colors ${
        isActive ? "bg-[#ecebfb] text-[#1e1b4b]" : "text-[#1e1b3a] hover:bg-[#f1f4fb]"
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        aria-current={isActive ? "page" : undefined}
        className="nav-row flex-1 min-w-0 flex items-center gap-3 pl-2 pr-1 py-1.5 rounded-2xl text-[15px] font-semibold"
      >
        <span
          className={`flex items-center justify-center w-10 h-10 rounded-xl shrink-0 transition-colors ${
            isActive ? "bg-[#dcd9fb] text-[#5b52f0]" : "bg-[#eef1f8] text-[#1e2340] group-hover:bg-[#e6ebf6]"
          }`}
        >
          <IconCmp size={22} strokeWidth={2.2} fill="none" />
        </span>
        <span className="flex-1 text-left truncate">{item.label}</span>
        {item.badge && (
          <span
            className={`py-0.5 px-2 rounded-full text-[10px] font-semibold ${
              BADGE_COLORS[item.badge.color] || BADGE_COLORS.indigo
            }`}
          >
            {item.badge.text}
          </span>
        )}
      </button>

      {expandable && (
        <button
          type="button"
          aria-label={open ? `Collapse ${item.label}` : `Expand ${item.label}`}
          aria-expanded={open}
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          className={`mr-1.5 w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-all ${
            open
              ? "bg-[#dcd9fb] text-[#5b52f0]"
              : "bg-transparent text-[#94a3b8] hover:bg-[#e8ecf6] hover:text-[#475569]"
          }`}
        >
          <ChevronDown
            size={16}
            strokeWidth={2.4}
            className={`transition-transform duration-200 ease-out ${open ? "rotate-0" : "-rotate-90"}`}
          />
        </button>
      )}
    </div>
  );
};

const SubNav = ({ items, activeId, onSelect }) => (
  <div className="mt-1 mb-1 mx-1 overflow-hidden rounded-xl bg-[#f1f4fb]/80 ring-1 ring-[#e6ebf2]">
    <ul className="flex flex-col p-1 gap-0.5">
      {items.map((sub) => {
        const subActive = activeId === sub.id;
        return (
          <li key={sub.id}>
            <button
              type="button"
              onClick={() => onSelect(sub.id)}
              aria-current={subActive ? "page" : undefined}
              className={`w-full flex items-center gap-2.5 text-left px-2.5 py-2 rounded-[10px] text-[13px] font-medium transition-colors ${
                subActive
                  ? "bg-white text-[#4f46e5] shadow-[0_1px_3px_rgba(36,45,64,0.08)]"
                  : "text-[#64748b] hover:bg-white/70 hover:text-[#0b1220]"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  subActive ? "bg-[#4f46e5]" : "bg-[#cbd5e1]"
                }`}
              />
              <span className="truncate">{sub.label}</span>
            </button>
          </li>
        );
      })}
    </ul>
  </div>
);

export const Sidebar = ({
  activeView,
  viewingDetails,
  onNavClick,
  agentsTab,
  onAgentsTabClick,
  toolsTab,
  onToolsTabClick,
  settingsOpen = false,
}) => {
  const [openIds, setOpenIds] = useState(() => {
    const initial = new Set();
    for (const id of Object.keys(EXPANDABLE)) {
      if (isGroupActive(id, activeView) && !settingsOpen) initial.add(id);
    }
    return initial;
  });

  // Auto-open the section that becomes active; leave user-collapsed others alone.
  useEffect(() => {
    if (settingsOpen || viewingDetails) return;
    for (const id of Object.keys(EXPANDABLE)) {
      if (isGroupActive(id, activeView)) {
        setOpenIds((prev) => {
          if (prev.has(id)) return prev;
          const next = new Set(prev);
          next.add(id);
          return next;
        });
      }
    }
  }, [activeView, settingsOpen, viewingDetails]);

  const toggleOpen = (id) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const openExpandable = (id) => {
    setOpenIds((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    if (id === "agents") onAgentsTabClick?.("overview");
    else if (id === "tools") onToolsTabClick?.("overview");
    else if (id === "knowledge") onNavClick("knowledge");
    else if (id === "operations") onNavClick("operations");
    else if (id === "observability") onNavClick("observability");
    else if (id === "departments") onNavClick("departments");
  };

  return (
    <aside className="w-60 bg-[#fbfdfe] border-r border-[#eef2f8] flex flex-col shrink-0 z-20">
      <div className="h-16 flex items-center px-5 border-b border-[#eef2f8]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#4f46e5] rounded-lg flex items-center justify-center text-white shadow-[0_4px_12px_rgba(79,70,229,0.28)]">
            <Icon name="atom" className="text-xl" />
          </div>
          <span className="text-xl font-black text-slate-900 tracking-tight">Orion AI</span>
        </div>
      </div>

      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 pt-4 pb-6 scrollbar-hide">
        <ul className="flex flex-col gap-1.5">
          {NAV_ITEMS.map((item) => {
            const isActive = activeView === item.id && !viewingDetails && !settingsOpen;
            return (
              <li key={item.id}>
                <NavRow item={item} isActive={isActive} onClick={() => onNavClick(item.id)} />
              </li>
            );
          })}
        </ul>

        <div className="mt-7 mx-3 mb-2.5 pt-5 border-t border-[#eef2f8] text-xs font-medium text-[#7b81a0]">
          Workspace
        </div>

        <ul className="flex flex-col gap-1.5">
          {WORKSPACE_ITEMS.map((item) => {
            const groupActive = isGroupActive(item.id, activeView) && !viewingDetails && !settingsOpen;
            const subItems = EXPANDABLE[item.id];
            const isOpen = Boolean(subItems && openIds.has(item.id));

            return (
              <li key={item.id}>
                <NavRow
                  item={item}
                  isActive={groupActive}
                  expandable={Boolean(subItems)}
                  open={isOpen}
                  onToggle={() => toggleOpen(item.id)}
                  onClick={() => {
                    if (!subItems) {
                      onNavClick(item.id);
                      return;
                    }
                    // Second click on an open section collapses it
                    if (isOpen) toggleOpen(item.id);
                    else openExpandable(item.id);
                  }}
                />

                {subItems && isOpen && (
                  <SubNav
                    items={subItems}
                    activeId={
                      item.id === "agents"
                        ? agentsTab
                        : item.id === "tools"
                          ? toolsTab
                          : activeView
                    }
                    onSelect={(id) => {
                      if (item.id === "agents") onAgentsTabClick?.(id);
                      else if (item.id === "tools") onToolsTabClick?.(id);
                      else onNavClick(id);
                    }}
                  />
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-3 border-t border-[#eef2f8] bg-[#fbfdfe] shrink-0">
        <button
          type="button"
          onClick={() => onNavClick("settings")}
          aria-current={settingsOpen ? "page" : undefined}
          className={`w-full flex items-center gap-3 p-2.5 rounded-2xl cursor-pointer transition-colors text-left border ${
            settingsOpen
              ? "bg-[#ecebfb] border-[#dcd9fb]"
              : "bg-[#f3f4f6] border-transparent hover:bg-[#ebecef]"
          }`}
        >
          <div className="w-9 h-9 rounded-xl bg-[#e8e7fc] flex items-center justify-center shrink-0">
            <span className="text-[13px] font-bold text-[#4338ca] tracking-tight">AM</span>
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-[13px] font-bold text-[#0b1220] truncate leading-tight">
              Personal Workspace
            </h4>
            <p className="text-[12px] text-[#6b7280] truncate mt-0.5">Free Plan</p>
          </div>
          <span className="w-8 h-8 rounded-xl bg-[#e5e7eb] flex items-center justify-center shrink-0 text-[#374151]">
            <ArrowUpRight size={16} strokeWidth={2.2} />
          </span>
        </button>
      </div>
    </aside>
  );
};
