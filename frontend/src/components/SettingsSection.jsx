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
        return <ViewBilling />;
      case "settings-api":
        return <ViewApiAccess />;
      case "settings-preferences":
        return <ViewPreferences />;
      case "settings-help":
        return <ViewHelpSupport />;
      case "settings-logout":
        return <ViewLogout onLogout={onLogout} />;
      default:
        return <ViewSettingsProfile />;
    }
  };

  return (
    <div className="flex h-full min-h-0 bg-[#f8fafc]">
      {/* Inner settings sidebar — Agents/Tools indigo chrome */}
      <aside className="w-[272px] shrink-0 border-r border-[#eef2f8] bg-white flex flex-col">
        <div className="px-5 pt-6 pb-5 border-b border-[#eef2f8]">
          <p className="text-[12px] font-semibold tracking-wide text-[#4f46e5]">
            Settings
          </p>
          <h2 className="text-[20px] font-extrabold text-[#0b1220] mt-1 leading-tight tracking-[-0.3px]">
            Settings &amp; Profile
          </h2>
          <p className="text-[13px] text-[#64748b] mt-1.5 leading-snug">
            Manage your account and workspace.
          </p>
        </div>

        <nav aria-label="Settings" className="flex-1 overflow-y-auto p-3 scrollbar-hide">
          <ul className="flex flex-col gap-1">
            {SETTINGS_SUBTABS.map((item) => {
              const IconCmp = SETTINGS_ICONS[item.id] || User;
              const active = tab === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onTabChange?.(item.id)}
                    aria-current={active ? "page" : undefined}
                    className={`w-full flex items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${
                      active
                        ? "bg-[#eef2ff] text-[#4f46e5]"
                        : "text-[#334155] hover:bg-[#f5f8fc]"
                    }`}
                  >
                    <span
                      className={`w-10 h-10 rounded-xl grid place-items-center shrink-0 ${
                        active
                          ? "bg-white text-[#4f46e5] shadow-sm"
                          : "bg-[#eef2ff] text-[#4f46e5]"
                      }`}
                    >
                      <IconCmp size={18} strokeWidth={2.1} />
                    </span>
                    <span className="min-w-0 pt-0.5">
                      <span
                        className={`block text-[13.5px] leading-tight ${
                          active ? "font-bold text-[#4f46e5]" : "font-semibold text-[#0b1220]"
                        }`}
                      >
                        {item.label}
                      </span>
                      <span className="block text-[12px] text-[#64748b] mt-0.5 leading-snug">
                        {item.desc}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      <div className="flex-1 min-w-0 overflow-auto bg-[#f8fafc]">{renderScreen()}</div>
    </div>
  );
};
