// IntroScreen — the OrionAI splash / loading screen.
//
// Composes the animated circuit background (CircuitBackground) with the
// canvas brand-dust wordmark (useBrandDust) plus a loader bar and status
// line. After the timed sequence it fades out and calls `onComplete` — it
// does NOT hardcode a redirect. The parent owns "what comes next" (today the
// app, later the auth/login route), keeping this component decoupled.
//
// Props:
//   onComplete?: () => void   invoked once, after the fade-out finishes.
//   holdMs?:     number       time before the fade-out begins (default 2950).
//   fadeMs?:     number       fade-out duration (default 700).

import { useEffect, useRef, useState } from "react";

import CircuitBackground from "./CircuitBackground";
import useBrandDust from "./useBrandDust";
import "./intro.css";

export default function IntroScreen({
  onComplete,
  holdMs = 2950,
  fadeMs = 700,
}) {
  const canvasRef = useRef(null);
  const [fading, setFading] = useState(false);

  useBrandDust(canvasRef, { text: "OrionAI", split: "Orion".length });

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFading(true), holdMs);
    const doneTimer = setTimeout(() => {
      onComplete?.();
    }, holdMs + fadeMs);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, [holdMs, fadeMs, onComplete]);

  return (
    <div className="intro-page">
      <CircuitBackground />

      <div className={`intro-splash${fading ? " intro-fade-out" : ""}`}>
        <div className="intro-orbit-glow" aria-hidden="true" />
        <div className="intro-brand">
          <canvas
            ref={canvasRef}
            className="intro-brand-canvas"
            role="img"
            aria-label="OrionAI"
          />
        </div>
        <div className="intro-loader" aria-hidden="true" />
        <div className="intro-loading-text">
          Initializing intelligent operations
        </div>
      </div>
    </div>
  );
}
