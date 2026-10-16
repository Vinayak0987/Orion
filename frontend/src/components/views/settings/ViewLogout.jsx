import { LogOut, Check } from "lucide-react";
import {
  neuShellCls,
  SettingsHeader,
  NeuGhostButton,
} from "./SettingsShared.jsx";

const checklist = [
  "Your work is saved automatically",
  "You'll need to sign in again to access Orion",
  "Active sessions on other devices remain signed in",
];

export const ViewLogout = ({ onLogout, onCancel }) => (
  <div className={neuShellCls}>
    <div className="max-w-[520px] mx-auto">
      <SettingsHeader title="Sign Out" subtitle="End your current session." />

      <div className="neu-card p-8">
        <div className="flex flex-col items-center text-center">
          <span className="neu-circle w-16 h-16 rounded-2xl grid place-items-center text-[#e11d48] mb-5">
            <LogOut size={26} strokeWidth={1.9} />
          </span>
          <h2 className="text-[17px] font-semibold text-[#334155]">Ready to sign out?</h2>
          <p className="text-[13.5px] text-[#8792a6] mt-1.5 max-w-[340px]">
            You will be signed out of this device. Your data stays safe.
          </p>

          <div className="neu-inset w-full p-5 mt-6 text-left">
            <ul className="flex flex-col gap-3">
              {checklist.map((item) => (
                <li key={item} className="flex items-center gap-3">
                  <span className="neu-circle w-6 h-6 rounded-full grid place-items-center text-[#16a34a] shrink-0">
                    <Check size={12} strokeWidth={3} />
                  </span>
                  <span className="text-[13px] text-[#5b6678]">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="flex items-center gap-3 mt-7">
            <NeuGhostButton className="h-10 px-6" onClick={onCancel}>Cancel</NeuGhostButton>
            <button
              onClick={onLogout}
              className="neu-btn-danger-solid inline-flex items-center justify-center gap-2 h-10 px-6 text-[14px] font-semibold"
            >
              <LogOut size={16} /> Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
);
