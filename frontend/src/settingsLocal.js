// settingsLocal — user preferences persisted in localStorage.
//
// There is no preferences backend (single-user, free system). These are pure
// client preferences: theme, language, timezone, date/time format, and
// notification toggles. Stored under one key so they load/save together.
//
// Theme is special: it is also reflected onto <html data-theme> so the themed
// CSS applies, matching the auth screen's theme system (useAuthTheme).

const KEY = "orion.preferences";

export const DEFAULTS = {
  theme: "light", // light | dark | system
  language: "English (US)",
  timezone: "(GMT+05:30) Asia/Kolkata",
  dateFormat: "MMM D, YYYY",
  timeFormat: "12h",
  notifyEmail: true,
  notifyInApp: true,
  notifyMarketing: false,
};

export function loadPreferences() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePreferences(prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(prefs));
  } catch {
    /* ignore quota / unavailable */
  }
}

export function updatePreference(key, value) {
  const prefs = loadPreferences();
  prefs[key] = value;
  savePreferences(prefs);
  if (key === "theme") applyTheme(value);
  return prefs;
}

// Reflect the chosen theme onto <html>. "system" follows the OS preference.
export function applyTheme(theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  let effective = theme;
  if (theme === "system") {
    const prefersDark =
      window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    effective = prefersDark ? "dark" : "light";
  }
  // The platform UI is light-themed; map "dark" to the auth dark palette token.
  root.setAttribute("data-theme", effective === "dark" ? "dark-black" : "light");
}

// Options exposed to the Preferences UI.
export const LANGUAGE_OPTIONS = [
  "English (US)",
  "English (UK)",
  "Hindi",
  "Spanish",
  "French",
  "German",
];

export const TIMEZONE_OPTIONS = [
  "(GMT+05:30) Asia/Kolkata",
  "(GMT+00:00) UTC",
  "(GMT-05:00) America/New_York",
  "(GMT-08:00) America/Los_Angeles",
  "(GMT+01:00) Europe/London",
  "(GMT+08:00) Asia/Singapore",
];

export const DATE_FORMAT_OPTIONS = [
  { value: "MMM D, YYYY", label: "Sep 15, 2026" },
  { value: "DD/MM/YYYY", label: "15/09/2026" },
  { value: "MM/DD/YYYY", label: "09/15/2026" },
  { value: "YYYY-MM-DD", label: "2026-09-15" },
];

export const TIME_FORMAT_OPTIONS = [
  { value: "12h", label: "12 hour (AM/PM)" },
  { value: "24h", label: "24 hour" },
];
