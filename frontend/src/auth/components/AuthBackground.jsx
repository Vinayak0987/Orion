// AuthBackground — the themed circuit-trace SVG plus the nebula glow that sits
// behind the auth cards. Colours come entirely from the active theme's CSS
// variables (see auth.css), so it restyles instantly when the theme changes.
//
// Each pulse path's exact length is measured once via getTotalLength() and
// written to the --len custom property the CSS keyframes read, giving the
// "line forms, holds, recedes" effect.

import { useLayoutEffect, useRef } from "react";

const PATHS = [
  "M0 208 H325 L575 455 H810 Q850 455 850 415 V105 Q850 75 820 75 H720",
  "M215 285 L580 645 Q595 660 620 660 H805",
  "M220 765 H350 Q370 765 385 780 L430 825 H690 L790 725 Q805 710 830 710 H1100",
  "M810 0 L915 105 V225 Q915 255 945 255 H1728",
  "M1728 280 H1620 Q1590 280 1570 300 L1480 390 V535 Q1480 565 1450 565 H1380",
  "M1728 645 H1680 Q1655 645 1635 665 L1550 750 Q1530 770 1500 770 H1380 L1300 690",
];

const STATIC_OPACITY = [0.55, 0.7, 0.55, 0.55, 0.5, 0.7];

export default function AuthBackground() {
  const svgRef = useRef(null);

  useLayoutEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    svg.querySelectorAll(".pulse-path").forEach((p) => {
      try {
        const len = p.getTotalLength();
        p.style.setProperty("--len", len);
        p.style.strokeDasharray = `${len} ${len}`;
      } catch (e) {
        /* getTotalLength unsupported */
      }
    });
  }, []);

  return (
    <div className="auth-bg" aria-hidden="true">
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 1728 860"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="1">
            <stop id="grad-stop-1" offset="0%" />
            <stop id="grad-stop-2" offset="50%" />
            <stop id="grad-stop-3" offset="100%" />
          </linearGradient>

          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="pulseGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="1.6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="coreGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="0.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {PATHS.map((d, i) => (
          <path
            key={`base-${i}`}
            d={d}
            fill="none"
            stroke="url(#lineGradient)"
            strokeWidth="1"
            opacity={STATIC_OPACITY[i]}
          />
        ))}

        <path
          className="accent-line"
          d="M580 645 H805"
          fill="none"
          strokeWidth="1.5"
          opacity="0.8"
          filter="url(#glow)"
        />
        <path
          className="accent-line"
          d="M1480 390 V535"
          fill="none"
          strokeWidth="1.5"
          opacity="0.7"
          filter="url(#glow)"
        />

        {PATHS.map((d, i) => (
          <g key={`pulse-${i}`}>
            <path className="pulse-path" d={d} />
            <path className="pulse-path pulse-core" d={d} />
          </g>
        ))}
      </svg>
    </div>
  );
}
