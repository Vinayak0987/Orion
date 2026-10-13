// FadeIn — fades its children in on mount. Pure CSS (no animation library),
// used to give route changes a smooth transition instead of a hard cut.
//
// It sets an initial "hidden" state, then flips to "shown" on the next frame so
// the CSS transition runs. `duration` and `delay` are in ms.

import { useEffect, useState } from "react";

export default function FadeIn({
  children,
  duration = 320,
  delay = 0,
  className = "",
}) {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    // rAF ensures the initial (hidden) styles are committed before we flip to
    // shown, so the browser animates the change.
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <div
      className={`fade-in${shown ? " fade-in-shown" : ""} ${className}`.trim()}
      style={{ transitionDuration: `${duration}ms`, transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}
