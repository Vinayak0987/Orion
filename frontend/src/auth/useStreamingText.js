// useStreamingText — types `text` into a ref'd element one unit at a time
// (character or word), like a live AI response, then removes the blinking
// cursor and resolves. Honours prefers-reduced-motion by rendering instantly.
//
// Returns nothing; drive it by passing a ref and enabling it. When `enabled`
// flips true the animation (re)starts. `onDone` fires once per completed run.
//
// This mirrors the original page's streamInto() behaviour but as a declarative
// hook so the AuthScreen can chain wordmark -> tagline.

import { useEffect } from "react";

export default function useStreamingText(
  ref,
  text,
  { enabled = true, mode = "char", speed = 70, jitter, onDone } = {}
) {
  useEffect(() => {
    const el = ref.current;
    if (!el || !enabled) return undefined;

    const effectiveJitter = jitter != null ? jitter : speed * 0.6;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    el.textContent = "";

    if (reduce) {
      el.textContent = text;
      onDone?.();
      return undefined;
    }

    const cursor = document.createElement("span");
    cursor.className = "auth-cursor";
    el.appendChild(cursor);

    const units = mode === "word" ? text.split(/(\s+)/) : text.split("");
    let i = 0;
    let timer = 0;
    let doneTimer = 0;

    function step() {
      if (i < units.length) {
        cursor.insertAdjacentText("beforebegin", units[i]);
        i += 1;
        timer = setTimeout(step, speed + Math.random() * effectiveJitter);
      } else {
        doneTimer = setTimeout(() => {
          cursor.remove();
          onDone?.();
        }, 650);
      }
    }
    step();

    return () => {
      clearTimeout(timer);
      clearTimeout(doneTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref, text, enabled, mode, speed, jitter]);
}
