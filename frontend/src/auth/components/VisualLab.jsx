// VisualLab — a collapsible design-time panel for live-tweaking the auth
// screen's circuit + nebula visuals. It writes CSS custom properties onto the
// document element (matching the variables auth.css reads), so changes apply
// instantly without a rebuild. Purely a tuning tool; it holds no auth logic.
//
// The heartbeat "pulse size" control rewrites the nebulaHeartbeat keyframes via
// an injected <style>, mirroring the original standalone page.
//
// Controlled by `theme` so its swatches re-sync whenever the theme changes.

import { useCallback, useEffect, useRef, useState } from "react";

// Resolve a colour string to #rrggbb using the browser.
function toHex(input) {
  const c = (input || "").trim();
  const m = c.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (m) {
    let h = m[1];
    if (h.length === 3) h = h.split("").map((x) => x + x).join("");
    return `#${h.toLowerCase()}`;
  }
  const probe = document.createElement("div");
  probe.style.color = c;
  document.body.appendChild(probe);
  const parts = getComputedStyle(probe).color.match(/\d+(\.\d+)?/g) || [255, 255, 255];
  document.body.removeChild(probe);
  return `#${[0, 1, 2]
    .map((i) => Math.round(+parts[i]).toString(16).padStart(2, "0"))
    .join("")}`;
}

// The theme variables are declared on the .auth-page element (see auth.css),
// so overrides must be written to that same element to win the cascade —
// writing them to <html> would be shadowed by .auth-page's own declarations.
// Fall back to documentElement if the auth page isn't mounted yet.
function labRoot() {
  return document.querySelector(".auth-page") || document.documentElement;
}

function readVar(name) {
  const el = labRoot();
  return (
    el.style.getPropertyValue(name).trim() ||
    getComputedStyle(el).getPropertyValue(name).trim()
  );
}
function setVar(name, value) {
  labRoot().style.setProperty(name, value);
}
function clearVars(names) {
  const el = labRoot();
  names.forEach((n) => el.style.removeProperty(n));
}

const TWEAK_VARS = [
  "--pulse-color",
  "--pulse-core",
  "--grad-stop-a",
  "--grad-stop-b",
  "--nebula-c1",
  "--nebula-c2",
  "--nebula-c3",
  "--line-width",
  "--nebula-size",
  "--nebula-opacity",
  "--nebula-blur",
  "--heartbeat-scale",
  "--heartbeat-speed",
];

function ColorRow({ label, value, onChange }) {
  return (
    <div className="color-lab-row">
      <label>{label}</label>
      <input type="color" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function RangeRow({ label, value, display, ...rangeProps }) {
  return (
    <div className="color-lab-row">
      <label>{label}</label>
      <div className="range-wrap">
        <input type="range" value={value} {...rangeProps} />
        <span className="range-value">{display}</span>
      </div>
    </div>
  );
}

// First-time defaults. The circuit (glow + base lines) defaults to cyan so a
// brand-new user sees a cyan circuit regardless of the active theme; the nebula
// keeps the violet accent. Once the user tweaks + we persist, their saved
// values take over; "Reset to theme" clears back to these.
const DEFAULT_STATE = {
  glow: "#00e1ff", // pulse line — cyan
  shine: "#ffffff", // bright pulse core
  base: "#00e1ff", // static circuit gradient — cyan
  lineWidth: 1,
  neb1: "#8175ff",
  neb2: "#8b7cff",
  neb3: "#7c5cff",
  nebSize: 560,
  nebOpacity: 0.55,
  nebBlur: 65,
  heartbeat: true,
  hbScale: 1.08,
  hbSpeed: 4,
};

const STORAGE_KEY = "orion.visualLab";

function loadSaved() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Merge over defaults so a partial/old payload still yields a full state.
    return { ...DEFAULT_STATE, ...parsed };
  } catch (e) {
    return null;
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    /* ignore */
  }
}

function clearSaved() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    /* ignore */
  }
}

// Push a state object's values into the CSS variables the auth screen reads,
// so a restored/edited configuration looks exactly as it did last time.
function applyStateVars(state) {
  setVar("--pulse-color", state.glow);
  setVar("--pulse-core", state.shine);
  setVar("--grad-stop-a", state.base);
  setVar("--grad-stop-b", state.base);
  setVar("--line-width", String(state.lineWidth));
  setVar("--nebula-c1", state.neb1);
  setVar("--nebula-c2", state.neb2);
  setVar("--nebula-c3", state.neb3);
  setVar("--nebula-size", `${state.nebSize}px`);
  setVar("--nebula-opacity", String(state.nebOpacity));
  setVar("--nebula-blur", `${state.nebBlur}px`);
  setVar("--heartbeat-speed", `${state.hbSpeed}s`);
  setVar("--heartbeat-scale", String(state.hbScale));
}

export default function VisualLab({ theme }) {
  const [collapsed, setCollapsed] = useState(true);
  const styleTagRef = useRef(null);

  // If the user saved a Visual Lab configuration before, start from that;
  // otherwise start from defaults (and let the theme sync fill the pickers).
  const savedRef = useRef(loadSaved());
  const [state, setState] = useState(() => savedRef.current || DEFAULT_STATE);

  // Mirror the active theme's NEBULA colours into the pickers. The circuit
  // (glow/shine/base) is intentionally not synced from the theme — its default
  // is cyan (DEFAULT_STATE) until the user changes it. Only used when the user
  // has NOT saved their own configuration.
  const sync = useCallback(() => {
    setState((s) => ({
      ...s,
      neb1: toHex(readVar("--nebula-c1") || readVar("--accent-purple")),
      neb2: toHex(readVar("--nebula-c2") || readVar("--grad-stop-b")),
      neb3: toHex(readVar("--nebula-c3") || readVar("--pulse-color")),
    }));
  }, []);

  useEffect(() => {
    // A saved configuration wins over the theme: keep the user's look. When
    // there is nothing saved, mirror the active theme's colours into the
    // pickers as before.
    if (!savedRef.current) sync();
  }, [theme, sync]);

  // On first mount, restore the saved configuration if there is one; otherwise
  // apply the cyan circuit defaults so a first-time user sees a cyan circuit
  // (the nebula still follows the theme via sync()).
  useEffect(() => {
    if (savedRef.current) {
      applyStateVars(savedRef.current);
      document
        .querySelector(".auth-page .nebula")
        ?.classList.toggle("heartbeat-off", !savedRef.current.heartbeat);
    } else {
      setVar("--pulse-color", DEFAULT_STATE.glow);
      setVar("--pulse-core", DEFAULT_STATE.shine);
      setVar("--grad-stop-a", DEFAULT_STATE.base);
      setVar("--grad-stop-b", DEFAULT_STATE.base);
      setVar("--line-width", String(DEFAULT_STATE.lineWidth));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist every change so the configuration is identical next time.
  useEffect(() => {
    saveState(state);
    savedRef.current = state;
  }, [state]);

  // Keep the nebula heartbeat keyframes in step with the pulse-size control.
  const applyHeartbeatKeyframes = useCallback((scale) => {
    let tag = styleTagRef.current;
    if (!tag) {
      tag = document.createElement("style");
      document.head.appendChild(tag);
      styleTagRef.current = tag;
    }
    const mid = (1 + (scale - 1) * 0.45).toFixed(3);
    tag.textContent = `@keyframes nebulaHeartbeat{0%,100%{transform:translate(0,0) scale(1)}12%{transform:translate(2px,-1px) scale(${mid})}22%{transform:translate(0,0) scale(1)}42%{transform:translate(1px,-1px) scale(${scale.toFixed(
      3
    )})}55%{transform:translate(0,0) scale(1)}}`;
  }, []);

  useEffect(() => {
    applyHeartbeatKeyframes(state.hbScale);
    return () => {
      const tag = styleTagRef.current;
      if (tag && tag.parentNode) tag.parentNode.removeChild(tag);
      styleTagRef.current = null;
    };
    // Only manage lifecycle here; scale updates handled in the setter below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = (patch) => setState((s) => ({ ...s, ...patch }));

  function reset() {
    clearVars(TWEAK_VARS);
    clearSaved();
    savedRef.current = null;
    // Return to the first-open state: cyan circuit defaults + nebula from theme.
    setState(DEFAULT_STATE);
    setVar("--pulse-color", DEFAULT_STATE.glow);
    setVar("--pulse-core", DEFAULT_STATE.shine);
    setVar("--grad-stop-a", DEFAULT_STATE.base);
    setVar("--grad-stop-b", DEFAULT_STATE.base);
    setVar("--line-width", String(DEFAULT_STATE.lineWidth));
    document
      .querySelector(".auth-page .nebula")
      ?.classList.remove("heartbeat-off");
    applyHeartbeatKeyframes(1.08);
    sync();
  }

  return (
    <div className={`color-lab${collapsed ? " collapsed" : ""}`}>
      <div className="color-lab-head" onClick={() => setCollapsed((c) => !c)}>
        <span>Visual Lab</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </div>

      <div className="color-lab-body">
        <div className="lab-section">
          <div className="lab-section-title">Circuit lines</div>
          <ColorRow
            label="Glow"
            value={state.glow}
            onChange={(v) => { update({ glow: v }); setVar("--pulse-color", v); }}
          />
          <ColorRow
            label="Shine"
            value={state.shine}
            onChange={(v) => { update({ shine: v }); setVar("--pulse-core", v); }}
          />
          <ColorRow
            label="Base circuit"
            value={state.base}
            onChange={(v) => {
              update({ base: v });
              setVar("--grad-stop-a", v);
              setVar("--grad-stop-b", v);
            }}
          />
          <RangeRow
            label="Line width"
            min="0.5"
            max="4"
            step="0.1"
            value={state.lineWidth}
            display={(+state.lineWidth).toFixed(1)}
            onChange={(e) => { update({ lineWidth: e.target.value }); setVar("--line-width", e.target.value); }}
          />
        </div>

        <div className="lab-section">
          <div className="lab-section-title">Nebula</div>
          <ColorRow
            label="Color 1"
            value={state.neb1}
            onChange={(v) => { update({ neb1: v }); setVar("--nebula-c1", v); }}
          />
          <ColorRow
            label="Color 2"
            value={state.neb2}
            onChange={(v) => { update({ neb2: v }); setVar("--nebula-c2", v); }}
          />
          <ColorRow
            label="Color 3"
            value={state.neb3}
            onChange={(v) => { update({ neb3: v }); setVar("--nebula-c3", v); }}
          />
          <RangeRow
            label="Size"
            min="300"
            max="900"
            step="10"
            value={state.nebSize}
            display={Math.round(+state.nebSize)}
            onChange={(e) => { update({ nebSize: e.target.value }); setVar("--nebula-size", `${e.target.value}px`); }}
          />
          <RangeRow
            label="Intensity"
            min="0"
            max="1"
            step="0.01"
            value={state.nebOpacity}
            display={`${Math.round(+state.nebOpacity * 100)}%`}
            onChange={(e) => { update({ nebOpacity: e.target.value }); setVar("--nebula-opacity", e.target.value); }}
          />
          <RangeRow
            label="Blur"
            min="15"
            max="120"
            value={state.nebBlur}
            display={Math.round(+state.nebBlur)}
            onChange={(e) => { update({ nebBlur: e.target.value }); setVar("--nebula-blur", `${e.target.value}px`); }}
          />
          <div className="lab-toggle">
            <span>Heartbeat pulse</span>
            <input
              type="checkbox"
              checked={state.heartbeat}
              onChange={(e) => {
                update({ heartbeat: e.target.checked });
                document
                  .querySelector(".auth-page .nebula")
                  ?.classList.toggle("heartbeat-off", !e.target.checked);
              }}
            />
          </div>
          <RangeRow
            label="Pulse size"
            min="1"
            max="1.35"
            step="0.01"
            value={state.hbScale}
            display={`${(+state.hbScale).toFixed(2)}×`}
            onChange={(e) => {
              const v = +e.target.value;
              update({ hbScale: v });
              setVar("--heartbeat-scale", String(v));
              applyHeartbeatKeyframes(v);
            }}
          />
          <RangeRow
            label="Pulse speed"
            min="2"
            max="12"
            step="0.5"
            value={state.hbSpeed}
            display={`${+state.hbSpeed}s`}
            onChange={(e) => { update({ hbSpeed: e.target.value }); setVar("--heartbeat-speed", `${e.target.value}s`); }}
          />
        </div>

        <button type="button" className="color-lab-reset" onClick={reset}>
          Reset to theme
        </button>
      </div>
    </div>
  );
}
