// Loader — a full-screen loading indicator in the Orion neumorphic aesthetic
// (soft #eef1f6 surface, indigo ring).
//
// "Delayed" by default: it stays invisible for `delay` ms, so fast loads don't
// flash a spinner (a spinner that appears and vanishes in 80ms looks worse than
// nothing). Only genuinely slow waits reveal it.
//
// Usage:
//   {loading && <Loader label="Loading your workspace" />}

import { useEffect, useState } from "react";

import "./Loader.css";

export default function Loader({ label = "Loading", delay = 250, fullscreen = true }) {
  const [visible, setVisible] = useState(delay === 0);

  useEffect(() => {
    if (delay === 0) return undefined;
    const id = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(id);
  }, [delay]);

  if (!visible) return null;

  return (
    <div
      className={`orion-loader${fullscreen ? " orion-loader-fullscreen" : ""}`}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <div className="orion-loader-mark">
        <span className="orion-loader-ring" />
        <span className="orion-loader-core" />
      </div>
      <div className="orion-loader-label">{label}</div>
    </div>
  );
}
