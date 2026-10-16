import { useEffect, useState } from "react";
import { Mail, Smartphone, Megaphone, Sun, Moon, Monitor } from "lucide-react";

import {
  loadPreferences,
  updatePreference,
  applyTheme,
  LANGUAGE_OPTIONS,
  TIMEZONE_OPTIONS,
  DATE_FORMAT_OPTIONS,
  TIME_FORMAT_OPTIONS,
} from "../../../settingsLocal.js";
import { useToast } from "../../ui/Toast.jsx";
import {
  neuShellCls,
  SettingsHeader,
  NeuSectionTitle,
  NeuSegmented,
  NeuToggle,
  NeuRow,
  neuSelect,
} from "./SettingsShared.jsx";

const THEME_OPTS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

const PrefRow = ({ label, control, last }) => (
  <div className={`flex items-center justify-between gap-6 py-4 ${!last ? "border-b border-[#e2e6ee]" : ""}`}>
    <span className="text-[13.5px] font-medium text-[#5b6678]">{label}</span>
    <div className="shrink-0">{control}</div>
  </div>
);

function NeuSelect({ value, onChange, options }) {
  return (
    <div className="relative w-64">
      <select value={value} onChange={(e) => onChange(e.target.value)} className={neuSelect}>
        {options.map((o) =>
          typeof o === "string" ? <option key={o} value={o}>{o}</option> : <option key={o.value} value={o.value}>{o.label}</option>
        )}
      </select>
      <svg className="w-4 h-4 text-[#8792a6] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6" /></svg>
    </div>
  );
}

export const ViewPreferences = () => {
  const toast = useToast();
  const [prefs, setPrefs] = useState(loadPreferences);
  useEffect(() => { applyTheme(prefs.theme); /* eslint-disable-next-line */ }, []);

  function set(key, value) {
    const next = updatePreference(key, value);
    setPrefs({ ...next });
    toast.success("Preferences saved.");
  }

  return (
    <div className={neuShellCls}>
      <div className="max-w-[820px] flex flex-col gap-7">
        <SettingsHeader title="Preferences" subtitle="Customize your Orion experience. Changes save automatically." />

        <div className="neu-card p-7">
          <NeuSectionTitle className="mb-3">Appearance</NeuSectionTitle>
          <PrefRow label="Theme" control={<NeuSegmented value={prefs.theme} onChange={(v) => set("theme", v)} options={THEME_OPTS} />} />
          <PrefRow label="Primary Language" control={<NeuSelect value={prefs.language} onChange={(v) => set("language", v)} options={LANGUAGE_OPTIONS} />} />
          <PrefRow label="Timezone" control={<NeuSelect value={prefs.timezone} onChange={(v) => set("timezone", v)} options={TIMEZONE_OPTIONS} />} />
          <PrefRow label="Date Format" control={<NeuSelect value={prefs.dateFormat} onChange={(v) => set("dateFormat", v)} options={DATE_FORMAT_OPTIONS} />} />
          <PrefRow label="Time Format" control={<NeuSelect value={prefs.timeFormat} onChange={(v) => set("timeFormat", v)} options={TIME_FORMAT_OPTIONS} />} last />
        </div>

        <div className="neu-card p-7">
          <NeuSectionTitle className="mb-2">Notifications</NeuSectionTitle>
          <NeuRow icon={Mail} title="Email Notifications" sub="Receive updates via email" action={<NeuToggle on={prefs.notifyEmail} onChange={(v) => set("notifyEmail", v)} />} />
          <NeuRow icon={Smartphone} title="In-App Notifications" sub="Show notifications inside Orion" action={<NeuToggle on={prefs.notifyInApp} onChange={(v) => set("notifyInApp", v)} />} />
          <NeuRow icon={Megaphone} title="Marketing Updates" sub="Product news and newsletters" action={<NeuToggle on={prefs.notifyMarketing} onChange={(v) => set("notifyMarketing", v)} />} last />
        </div>
      </div>
    </div>
  );
};
