// useAuthTheme — owns the auth UI theme. The themes are driven by CSS custom
// properties scoped under `html[data-theme="…"]` (see auth.css), so this hook
// simply reflects the chosen theme onto the document element and persists it.
//
// Themes: "light" | "dark-purple" | "dark-black" | "dark-gray".
//
// Persistence key matches the original page ("orion-theme") so a user's choice
// carries across the whole product.

import { useCallback, useEffect, useState } from "react";

export const THEMES = ["light", "dark-purple", "dark-black", "dark-gray"];
const STORAGE_KEY = "orion-theme";

function initialTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && THEMES.includes(saved)) return saved;
  } catch (e) {
    /* localStorage unavailable */
  }
  // Fall back to whatever the pre-paint script in index.html already applied to
  // <html> (keeps the hook in sync with the first-paint theme, no flash).
  if (typeof document !== "undefined") {
    const applied = document.documentElement.getAttribute("data-theme");
    if (applied && THEMES.includes(applied)) return applied;
  }
  // Default is dark.
  return "dark-black";
}

export default function useAuthTheme() {
  const [theme, setThemeState] = useState(initialTheme);

  // Reflect the theme onto <html> so the scoped CSS variables apply.
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.getAttribute("data-theme");
    root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore */
    }
    // Restore whatever was there before when the auth screen unmounts, so the
    // main app's own styling is not left with an auth theme attribute.
    return () => {
      if (previous === null) root.removeAttribute("data-theme");
      else root.setAttribute("data-theme", previous);
    };
  }, [theme]);

  const setTheme = useCallback((name) => {
    if (THEMES.includes(name)) setThemeState(name);
  }, []);

  return { theme, setTheme };
}
