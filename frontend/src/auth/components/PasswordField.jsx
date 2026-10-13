// PasswordField — labelled password input with a show/hide eye toggle.
// Controlled: value + onChange come from the parent form. `id` keeps the
// label association and eye button accessible.

import { useState } from "react";

export default function PasswordField({
  id,
  label = "Password",
  value,
  onChange,
  onBlur,
  placeholder = "Your Password",
  autoComplete = "current-password",
  error = "",
}) {
  const [visible, setVisible] = useState(false);
  const errorId = error ? `${id}-error` : undefined;

  return (
    <label className="password">
      <span>{label}</span>
      <input
        id={id}
        type={visible ? "text" : "password"}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        autoComplete={autoComplete}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={errorId}
      />
      <button
        type="button"
        className="eye"
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        onClick={() => setVisible((v) => !v)}
      >
        {visible ? (
          // password shown -> soft closed eye (single gentle downward curve)
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M4 10c2.2 3 4.9 4.5 8 4.5S17.8 13 20 10" />
          </svg>
        ) : (
          // password hidden -> soft rounded open eye (almond lids + round pupil)
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 6c-4 0-7 3.2-8.4 5.3a1.2 1.2 0 0 0 0 1.4C5 14.8 8 18 12 18s7-3.2 8.4-5.3a1.2 1.2 0 0 0 0-1.4C19 9.2 16 6 12 6z" />
            <circle cx="12" cy="12" r="2.6" />
          </svg>
        )}
      </button>
      {error && (
        <span className="field-error" id={errorId} role="alert">
          {error}
        </span>
      )}
    </label>
  );
}
