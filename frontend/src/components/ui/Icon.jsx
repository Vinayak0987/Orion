// Maps legacy Font Awesome icon names used across the app to Phosphor icon names.
// Add or tweak entries here to change an icon everywhere it's referenced by that key.
export const PH_MAP = {
  // nav / workspace
  "gauge-high": "gauge", "wand-magic-sparkles": "magic-wand", "bullseye": "target",
  "clipboard-check": "clipboard-text", "bell": "bell", "sitemap": "tree-structure",
  "robot": "robot", "book-open": "book-open", "screwdriver-wrench": "wrench",
  "wave-square": "wave-sine", "house": "house",
  // dashboard metrics + misc
  "calendar-day": "calendar-dots", "chevron-right": "caret-right", "chevron-left": "caret-left",
  "chevron-down": "caret-down", "chevron-up": "caret-up", "diagram-project": "graph",
  "hourglass-half": "hourglass-medium", "heart-pulse": "heartbeat", "atom": "atom",
  "arrow-up": "arrow-up", "arrow-right": "arrow-right", "arrow-down": "arrow-down",
  // activity / status
  "check": "check", "plus": "plus", "exclamation": "warning", "flag-checkered": "flag-checkered",
  "lightbulb": "lightbulb", "chart-pie": "chart-pie", "chart-line": "chart-line-up",
  "chart-column": "chart-bar", "chart-simple": "chart-bar", "circle-check": "check-circle",
  "check-circle": "check-circle", "circle": "circle", "circle-xmark": "x-circle",
  "circle-dot": "record", "circle-plus": "plus-circle", "circle-exclamation": "warning-circle",
  "triangle-exclamation": "warning", "times-circle": "x-circle", "check-double": "checks",
  "spinner": "circle-notch", "stop": "stop", "clock": "clock",
  // files / evidence
  "file-invoice-dollar": "invoice", "file-excel": "microsoft-excel-logo",
  "file-pdf": "file-pdf", "file-lines": "file-text", "file-alt": "file-text",
  "folder-open": "folder-open", "paperclip": "paperclip",
  // approvals / people / tools
  "user-plus": "user-plus", "users": "users-three", "key": "key", "bullhorn": "megaphone",
  "pen-nib": "pen-nib", "handshake": "handshake", "indian-rupee-sign": "currency-inr",
  "align-left": "text-align-left", "arrow-trend-up": "trend-up", "arrow-trend-down": "trend-down",
  // command center / graph
  "paper-plane": "paper-plane-tilt", "up-right-and-down-left-from-center": "arrows-out",
  "location-dot": "map-pin", "map-marker-alt": "map-pin", "map-location-dot": "map-trifold",
  "tag": "tag", "coins": "coins", "globe": "globe", "search": "magnifying-glass",
  "magnifying-glass-plus": "magnifying-glass-plus", "magnifying-glass-minus": "magnifying-glass-minus",
  "crosshairs": "crosshair", "rocket": "rocket-launch", "list-check": "list-checks",
  "stream": "list-checks", "spider": "bug-beetle", "search-plus": "magnifying-glass-plus",
  "search-minus": "magnifying-glass-minus", "expand": "arrows-out", "border-all": "squares-four",
  // notifications
  "exclamation-triangle": "warning", "plus-circle": "plus-circle", "sync-alt": "arrows-clockwise",
  "arrows-rotate": "arrows-clockwise", "bug": "bug", "chart-bar": "chart-bar",
  "dot-circle": "record", "folder": "folder", "sun": "sun", "bars": "list", "expand-arrows": "arrows-out",
};

const phName = (name) => PH_MAP[name] || name;

// Filled (rounded) icon — used for accents, buttons, badges.
export const Icon = ({ name, className = "" }) => (
  <i className={`ph-fill ph-${phName(name)} ${className}`}></i>
);

// Outline (rounded) icon — used for sidebar nav and top bar.
export const OutlineIcon = ({ name, className = "" }) => (
  <i className={`ph ph-${phName(name)} ${className}`}></i>
);
