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
  TOOLS_SUBTABS,
  KNOWLEDGE_SUBTABS,
  OPERATIONS_SUBTABS,
  OBSERVABILITY_SUBTABS,
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
  rose: "text-rose-600",
  indigo: "text-[#4f46e5]",
};

const EXPANDABLE = {
  tools: TOOLS_SUBTABS,
  knowledge: KNOWLEDGE_SUBTABS,
  operations: OPERATIONS_SUBTABS,
  observability: OBSERVABILITY_SUBTABS,
};

const isGroupActive = (itemId, activeView) => {
  if (itemId === "knowledge") return activeView === "knowledge" || activeView.startsWith("knowledge-");
  if (itemId === "operations") return activeView === "operations" || activeView.startsWith("operations-");
  if (itemId === "observability") return activeView === "observability" || activeView.startsWith("observability-");
  if (itemId === "departments") {
    return (
      activeView === "departments" ||
      activeView === "create-department" ||
      activeView === "department-detail"
    );
  }
  return activeView === itemId;
};

const NavRow = ({ item, isActive, onClick, expandable = false, open = false, onToggle }) => {
  const IconCmp = NAV_ICONS[item.id] || House;
  return (
    <div className={`neu-nav ${isActive ? "neu-nav-active" : ""} flex items-center`}>
      <button
        type="button"
        onClick={onClick}
        aria-current={isActive ? "page" : undefined}
        className="flex-1 min-w-0 flex items-center gap-2.5 px-3 py-2.5 text-[14px]"
      >
        <IconCmp
          size={19}
          strokeWidth={2.1}
          fill="none"
          className={isActive ? "text-[#4f46e5]" : "text-[#8792a6]"}
        />
        <span className={`flex-1 text-left truncate ${isActive ? "text-[#4f46e5] font-semibold" : "text-[#4a5568] font-medium"}`}>
          {item.label}
        </span>
        {item.badge && (
          <span className={`neu-chip py-0.5 px-2 text-[10px] font-bold ${BADGE_COLORS[item.badge.color] || BADGE_COLORS.indigo}`}>
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
          className={`mr-2 w-6 h-6 rounded-md flex items-center justify-center shrink-0 ${
            open ? "text-[#4f46e5]" : "text-[#9aa6b8] hover:text-[#4a5568]"
          }`}
        >
          <ChevronDown
            size={15}
            strokeWidth={2.4}
            className={`transition-transform duration-200 ease-out ${open ? "rotate-0" : "-rotate-90"}`}
          />
        </button>
      )}
    </div>
  );
};

const SubNav = ({ items, activeId, onSelect }) => (
  <div className="neu-inset mt-1.5 mb-1 mx-1 p-1.5">
    <ul className="flex flex-col gap-0.5">
      {items.map((sub) => {
        const subActive = activeId === sub.id;
        return (
          <li key={sub.id}>
            <button
              type="button"
              onClick={() => onSelect(sub.id)}
              aria-current={subActive ? "page" : undefined}
              className={`w-full flex items-center gap-2.5 text-left px-2.5 py-2 rounded-[9px] text-[13px] font-medium transition-all ${
                subActive
                  ? "neu-raised text-[#4f46e5]"
                  : "text-[#64748b] hover:text-[#334155]"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${subActive ? "bg-[#4f46e5]" : "bg-[#b4bdcc]"}`} />
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
    <aside className="w-60 neu-surface flex flex-col shrink-0 z-20 border-r border-[#e2e6ee]">
      {/* Brand */}
      <div className="h-16 flex items-center px-5">
        <div className="flex items-center gap-3">
          <div className="neu-circle w-9 h-9 rounded-xl flex items-center justify-center text-[#4f46e5]">
            <Icon name="atom" className="text-lg" />
          </div>
          <span className="text-[18px] font-bold text-[#334155] tracking-tight">Orion AI</span>
        </div>
      </div>

      <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 pt-3 pb-6 scrollbar-hide">
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

        <div className="mt-6 mx-2 mb-2.5 text-[11px] font-semibold uppercase tracking-wide text-[#9aa6b8]">
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

      {/* Workspace card */}
      <div className="p-3 shrink-0">
        <button
          type="button"
          onClick={() => onNavClick("settings")}
          aria-current={settingsOpen ? "page" : undefined}
          className={`neu-card-hover w-full flex items-center gap-3 p-2.5 text-left ${settingsOpen ? "!shadow-[inset_4px_4px_9px_#d4d9e4,inset_-4px_-4px_9px_#ffffff]" : ""}`}
        >
          <span className="neu-circle w-9 h-9 rounded-xl flex items-center justify-center shrink-0">
            <span className="text-[12px] font-bold text-[#4338ca] tracking-tight">AM</span>
          </span>
          <div className="flex-1 min-w-0">
            <h4 className="text-[13px] font-semibold text-[#334155] truncate leading-tight">Personal Workspace</h4>
            <p className="text-[11.5px] text-[#8792a6] truncate mt-0.5">Free Plan</p>
          </div>
          <span className="neu-circle w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-[#64748b]">
            <ArrowUpRight size={15} strokeWidth={2.2} />
          </span>
        </button>
      </div>
    </aside>
  );
};
