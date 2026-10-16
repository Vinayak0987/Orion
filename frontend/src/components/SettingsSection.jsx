import {
  User,
  Settings2,
  Shield,
  CreditCard,
  KeyRound,
  SlidersHorizontal,
  CircleHelp,
  LogOut,
} from "lucide-react";
import { SETTINGS_SUBTABS } from "../data/navigation.js";
import { ViewSettingsProfile } from "./views/settings/ViewSettingsProfile.jsx";
import { ViewWorkspaceSettings } from "./views/settings/ViewWorkspaceSettings.jsx";
import { ViewSecurity } from "./views/settings/ViewSecurity.jsx";
import { ViewBilling } from "./views/settings/ViewBilling.jsx";
import { ViewApiAccess } from "./views/settings/ViewApiAccess.jsx";
import { ViewPreferences } from "./views/settings/ViewPreferences.jsx";
import { ViewHelpSupport } from "./views/settings/ViewHelpSupport.jsx";
import { ViewLogout } from "./views/settings/ViewLogout.jsx";

const SETTINGS_ICONS = {
  settings: User,
  "settings-workspace": Settings2,
  "settings-security": Shield,
  "settings-billing": CreditCard,
  "settings-api": KeyRound,
  "settings-preferences": SlidersHorizontal,
  "settings-help": CircleHelp,
  "settings-logout": LogOut,
};

export const SettingsSection = ({ tab = "settings", onTabChange, onLogout }) => {
  const renderScreen = () => {
    switch (tab) {
      case "settings":
        return <ViewSettingsProfile />;
      case "settings-workspace":
        return <ViewWorkspaceSettings />;
      case "settings-security":
        return <ViewSecurity />;
      case "settings-billing":
        return <ViewBilling onManageKeys={() => onTabChange?.("settings-api")} />;
      case "settings-api":
        return <ViewApiAccess />;
      case "settings-preferences":
        return <ViewPreferences />;
      case "settings-help":
        return <ViewHelpSupport />;
      case "settings-logout":
        return <ViewLogout onLogout={onLogout} onCancel={() => onTabChange?.("settings")} />;
      default:
        return <ViewSettingsProfile />;
    }
  };

  return (
    <div className="flex h-full min-h-0 neu-surface">
      {/* Inner settings sidebar */}
      <aside className="w-[264px] shrink-0 neu-surface flex flex-col border-r border-[#e2e6ee]">
        <div className="px-5 pt-6 pb-5">
          <div className="flex items-center gap-2.5">
            <span className="neu-circle w-9 h-9 rounded-xl grid place-items-center text-[#4f46e5]">
              <Settings2 size={17} strokeWidth={2.2} />
            </span>
            <h2 className="text-[16px] font-semibold text-[#334155] tracking-[-0.2px]">Settings</h2>
          </div>
          <p className="text-[12.5px] text-[#8792a6] mt-2 leading-snug">
            Manage your account, workspace, and preferences.
          </p>
        </div>

        <nav aria-label="Settings" className="flex-1 overflow-y-auto px-3 pb-6 scrollbar-hide">
          <ul className="flex flex-col gap-1.5">
            {SETTINGS_SUBTABS.map((item) => {
              const IconCmp = SETTINGS_ICONS[item.id] || User;
              const active = tab === item.id;
              const danger = item.id === "settings-logout";
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onTabChange?.(item.id)}
                    aria-current={active ? "page" : undefined}
                    className={`neu-nav ${active ? "neu-nav-active" : ""} w-full flex items-center gap-3 px-2.5 py-2 text-left`}
                  >
                    <span
                      className={`w-8 h-8 rounded-lg grid place-items-center shrink-0 ${
                        active
                          ? "text-[#4f46e5]"
                          : danger
                            ? "text-[#e11d48]"
                            : "text-[#7b8699]"
                      }`}
                    >
                      <IconCmp size={16} strokeWidth={2.1} />
                    </span>
                    <span
                      className={`text-[13.5px] leading-tight ${
                        active ? "text-[#4f46e5] font-semibold" : danger ? "text-[#e11d48] font-medium" : "text-[#5b6678] font-medium"
                      }`}
                    >
                      {item.label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      <div className="flex-1 min-w-0 overflow-auto neu-surface">{renderScreen()}</div>
    </div>
  );
};
