// LandingCircuit — faint decorative "signal lines" with smooth angled bends
// (diagonal segments joined by gentle rounded corners), like the reference.
// Cyan glow; each line draws itself in and out on a loop.
//
// Each section gets 3–4 traces, spread apart across the empty margin zones
// (the four corners + the left/right side gutters) so they never cluster and
// never cross the centre where the content lives. Orientation/placement varies
// per variant so no two sections look identical.
//
// Drawn in a 1440x600 viewBox, stretched with preserveAspectRatio="none".
// Content column is ~ x:120..1320; traces stay near/outside that band.

import { useLayoutEffect, useRef } from "react";

const VARIANTS = {
  a: [
    "M-20 70 H120 Q160 70 186 102 L272 208",         // top-left, larger
    "M1460 100 H1330 Q1290 100 1264 132 L1196 220",  // top-right
    "M50 300 V400 Q50 440 82 462 L150 508",           // left-mid gutter
    "M1410 490 V380 Q1410 344 1382 322 L1320 278",    // right-lower gutter
  ],
  b: [
    "M1460 80 H1330 Q1290 80 1264 112 L1192 204",     // top-right
    "M-20 150 H100 Q140 150 166 182 L238 274",         // top-left
    "M70 540 V430 Q70 394 100 372 L162 328",            // bottom-left gutter
    "M1420 300 V400 Q1420 440 1388 462 L1322 506",      // right-mid gutter
  ],
  c: [
    "M-20 100 H110 Q150 100 176 132 L250 226",          // top-left
    "M1460 520 H1330 Q1290 520 1264 488 L1190 396",     // bottom-right
    "M1440 130 V240 Q1440 276 1410 298 L1346 342",      // right-upper gutter
    "M40 490 V380 Q40 344 70 322 L134 278",              // left-lower gutter
  ],
  d: [
    "M50 -20 V110 Q50 150 82 172 L152 216",              // top-left gutter
    "M1460 110 H1330 Q1290 110 1264 142 L1194 232",      // top-right
    "M-20 540 H110 Q150 540 176 508 L252 414",            // bottom-left
    "M1410 490 V380 Q1410 344 1382 322 L1320 276",        // right-lower gutter
  ],
  e: [
    "M1460 80 H1340 Q1300 80 1274 112 L1198 210",        // top-right
    "M-20 150 H90 Q130 150 156 182 L228 280",             // top-left
    "M1430 370 V480 Q1430 516 1400 538 L1338 574",        // right-lower gutter
    "M50 320 V430 Q50 466 82 488 L150 528",                // left-mid gutter
  ],
};

export default function LandingCircuit({ variant = "a" }) {
  const ref = useRef(null);
  const paths = VARIANTS[variant] || VARIANTS.a;

  useLayoutEffect(() => {
    const svg = ref.current;
    if (!svg) return;
    svg.querySelectorAll(".lp-circuit-path").forEach((p, i) => {
      try {
        const len = p.getTotalLength();
        p.style.setProperty("--len", len);
        p.style.strokeDasharray = len;
        p.style.strokeDashoffset = len;
        p.style.animationDelay = `${(i * 1.2).toFixed(2)}s`;
      } catch (e) {
        /* getTotalLength unsupported — leave the faint static line */
      }
    });
  }, []);

  return (
    <div className="lp-circuit" aria-hidden="true">
      <svg ref={ref} viewBox="0 0 1440 600" preserveAspectRatio="none" width="100%" height="100%">
        {paths.map((d, i) => (
          <path key={i} className="lp-circuit-path" d={d} />
        ))}
      </svg>
    </div>
  );
}
