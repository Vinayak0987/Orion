// OrionLogo — the orbiting "operations hub" SVG mark next to the streamed
// "OrionAI" wordmark. The wordmark text element is exposed via `textRef` so
// the parent can drive the typing animation (and chain the tagline after).

export default function OrionLogo({ textRef }) {
  return (
    <div className="auth-logo-wrap">
      <svg
        className="auth-logo-icon"
        viewBox="0 0 36 40"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="coreGrad3d" cx="32%" cy="26%" r="80%">
            <stop id="core-grad-stop-1" offset="0%" stopOpacity="0.95" />
            <stop id="core-grad-stop-2" offset="38%" stopOpacity="1" />
            <stop id="core-grad-stop-3" offset="100%" stopOpacity="0.55" />
          </radialGradient>
          <radialGradient id="glossGrad" cx="35%" cy="25%" r="75%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>
          <filter id="logoShadow" x="-60%" y="-60%" width="220%" height="220%">
            <feDropShadow
              dx="0"
              dy="1.2"
              stdDeviation="1.4"
              floodColor="#000000"
              floodOpacity="0.28"
            />
          </filter>
        </defs>
        <g transform="translate(2,3)" filter="url(#logoShadow)">
          <g className="orbit-group">
            <ellipse
              cx="17"
              cy="18"
              rx="15"
              ry="8.5"
              transform="rotate(-18 17 18)"
              fill="none"
              stroke="var(--logo-color)"
              strokeWidth="1"
              opacity="0.3"
            />
            <line x1="17" y1="18" x2="30.7" y2="18" stroke="var(--logo-color)" strokeWidth="1.1" strokeLinecap="round" opacity="0.8" />
            <line x1="17" y1="18" x2="6" y2="26.1" stroke="var(--logo-color)" strokeWidth="1.1" strokeLinecap="round" opacity="0.8" />
            <line x1="17" y1="18" x2="14.4" y2="9.9" stroke="var(--logo-color)" strokeWidth="1.1" strokeLinecap="round" opacity="0.8" />
            <circle cx="30.7" cy="18" r="2.3" fill="url(#coreGrad3d)" />
            <circle cx="29.9" cy="17.2" r="1.5" fill="url(#glossGrad)" />
            <circle cx="6" cy="26.1" r="2.3" fill="url(#coreGrad3d)" />
            <circle cx="5.2" cy="25.3" r="1.5" fill="url(#glossGrad)" />
            <circle cx="14.4" cy="9.9" r="2.3" fill="url(#coreGrad3d)" />
            <circle cx="13.6" cy="9.1" r="1.5" fill="url(#glossGrad)" />
          </g>
          <circle cx="17" cy="18" r="4.4" fill="url(#coreGrad3d)" />
          <circle cx="15.9" cy="16.8" r="2.7" fill="url(#glossGrad)" />
        </g>
      </svg>
      <span className="auth-logo-text" ref={textRef} />
    </div>
  );
}
