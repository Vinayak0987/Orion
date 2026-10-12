import { LogOut, Check } from "lucide-react";
import {
  SettingsHeader,
  PrimaryButton,
  OutlineButton,
  pageShellCls,
  cardCls,
} from "./SettingsShared.jsx";

const checklist = [
  "Your work is saved automatically",
  "You'll need to sign in again to access Orion",
  "Active sessions on other devices will remain",
];

export const ViewLogout = ({ onLogout }) => (
  <div className={pageShellCls}>
    <div className="max-w-[920px]">
      <SettingsHeader title="Logout" subtitle="Sign out from workspace." />

      <div className="flex flex-col items-center text-center max-w-[520px] mx-auto pt-4">
        <span className="w-16 h-16 rounded-2xl bg-[#eef2ff] text-[#4f46e5] grid place-items-center mb-6">
          <LogOut size={28} strokeWidth={1.9} />
        </span>
        <h2 className="text-[22px] font-extrabold text-[#0b1220]">Ready to sign out?</h2>
        <p className="text-[15px] text-[#64748b] mt-2">
          You will be signed out from your account and all active sessions.
        </p>

        <div className={`${cardCls} w-full p-6 mt-8 text-left bg-[#f8fafc]`}>
          <p className="text-[14px] font-bold text-[#0b1220] mb-4">Before you go</p>
          <ul className="flex flex-col gap-3">
            {checklist.map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="w-5 h-5 rounded-full bg-[#e7f8ef] text-[#16a34a] grid place-items-center shrink-0">
                  <Check size={13} strokeWidth={3} />
                </span>
                <span className="text-[14px] text-[#64748b]">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex items-center gap-3 mt-8">
          <PrimaryButton className="px-8" onClick={onLogout}>Sign Out</PrimaryButton>
          <OutlineButton className="px-8">Cancel</OutlineButton>
        </div>
      </div>
    </div>
  </div>
);
