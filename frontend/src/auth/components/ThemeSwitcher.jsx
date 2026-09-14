// ThemeSwitcher — the fixed top-right theme control: a light (sun) button plus
// three colour swatches for the dark variants. Driven by the theme value +
// setter from useAuthTheme; reflects the active theme via aria-pressed.

const SWATCHES = [
  { id: "dark-purple", sw: "#7c6bff", label: "Dark, purple" },
  { id: "dark-black", sw: "#141416", label: "Dark, matte black" },
  { id: "dark-gray", sw: "#2b2c33", label: "Dark, matte gray" },
];

export default function ThemeSwitcher({ theme, onChange }) {
  return (
    <div className="theme-switcher" role="group" aria-label="Theme">
      <button
        type="button"
        className="ts-btn ts-light"
        aria-label="Light mode"
        aria-pressed={theme === "light"}
        onClick={() => onChange("light")}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        >
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2.5v2.2M12 19.3v2.2M4.2 4.2l1.5 1.5M18.3 18.3l1.5 1.5M2.5 12h2.2M19.3 12h2.2M4.2 19.8l1.5-1.5M18.3 5.7l1.5-1.5" />
        </svg>
      </button>

      {SWATCHES.map((s) => (
        <button
          key={s.id}
          type="button"
          className="ts-btn ts-swatch"
          style={{ "--sw": s.sw }}
          aria-label={s.label}
          aria-pressed={theme === s.id}
          onClick={() => onChange(s.id)}
        />
      ))}
    </div>
  );
}
