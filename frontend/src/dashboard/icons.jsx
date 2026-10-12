// Inline-SVG icon set. No icon library — keeps the locked "react/react-dom/
// react-router-dom only" dependency rule intact. Each icon is a small stroked
// glyph inheriting `currentColor`, sized by the `s` (size) prop.

const base = (s = 18) => ({
  width: s,
  height: s,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round",
  strokeLinejoin: "round",
});

export const Icon = {
  dashboard: (p) => (
    <svg {...base(p?.s)}><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>
  ),
  command: (p) => (
    <svg {...base(p?.s)}><path d="M8 9h8M8 13h5" /><rect x="3" y="4" width="18" height="16" rx="2.5" /></svg>
  ),
  missions: (p) => (
    <svg {...base(p?.s)}><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>
  ),
  approvals: (p) => (
    <svg {...base(p?.s)}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /><path d="M9 12l2 2 4-4" /></svg>
  ),
  bell: (p) => (
    <svg {...base(p?.s)}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></svg>
  ),
  departments: (p) => (
    <svg {...base(p?.s)}><rect x="3" y="3" width="8" height="8" rx="1.5" /><rect x="13" y="3" width="8" height="8" rx="1.5" /><rect x="3" y="13" width="8" height="8" rx="1.5" /><rect x="13" y="13" width="8" height="8" rx="1.5" /></svg>
  ),
  agents: (p) => (
    <svg {...base(p?.s)}><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5" /><circle cx="18" cy="9" r="2.4" /><path d="M16 20c.3-2.5 1.6-4 4-4" /></svg>
  ),
  knowledge: (p) => (
    <svg {...base(p?.s)}><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z" /><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5A2.5 2.5 0 0 1 4 20.5z" /></svg>
  ),
  tools: (p) => (
    <svg {...base(p?.s)}><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2-2z" /></svg>
  ),
  observability: (p) => (
    <svg {...base(p?.s)}><path d="M3 12h4l2 6 4-14 2 8h6" /></svg>
  ),
  search: (p) => (
    <svg {...base(p?.s)}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
  ),
  sun: (p) => (
    <svg {...base(p?.s)}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
  ),
  chevronDown: (p) => (
    <svg {...base(p?.s)}><path d="m6 9 6 6 6-6" /></svg>
  ),
  chevronRight: (p) => (
    <svg {...base(p?.s)}><path d="m9 6 6 6-6 6" /></svg>
  ),
  chevronLeft: (p) => (
    <svg {...base(p?.s)}><path d="m15 6-6 6 6 6" /></svg>
  ),
  plus: (p) => (
    <svg {...base(p?.s)}><path d="M12 5v14M5 12h14" /></svg>
  ),
  activity: (p) => (
    <svg {...base(p?.s)}><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
  ),
  trend: (p) => (
    <svg {...base(p?.s)}><path d="M23 6l-9.5 9.5-5-5L1 18" /><path d="M17 6h6v6" /></svg>
  ),
  check: (p) => (
    <svg {...base(p?.s)}><path d="M20 6 9 17l-5-5" /></svg>
  ),
  rocket: (p) => (
    <svg {...base(p?.s)}><path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2 0-2.8a2 2 0 0 0-3 0z" /><path d="M12 15l-3-3a12 12 0 0 1 6.5-8.5c3-1 4.5-.5 4.5-.5s.5 1.5-.5 4.5A12 12 0 0 1 15 12z" /><circle cx="15" cy="9" r="1.2" /></svg>
  ),
  alert: (p) => (
    <svg {...base(p?.s)}><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></svg>
  ),
  clock: (p) => (
    <svg {...base(p?.s)}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
  ),
  send: (p) => (
    <svg {...base(p?.s)}><path d="M22 2 11 13" /><path d="M22 2 15 22l-4-9-9-4z" /></svg>
  ),
  paperclip: (p) => (
    <svg {...base(p?.s)}><path d="M21 12.5 12.5 21a5 5 0 0 1-7-7l8.5-8.5a3.5 3.5 0 0 1 5 5L10.5 18a2 2 0 0 1-3-3l7.5-7.5" /></svg>
  ),
  stop: (p) => (
    <svg {...base(p?.s)}><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
  ),
  doc: (p) => (
    <svg {...base(p?.s)}><path d="M14 3v5h5" /><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /></svg>
  ),
  globe: (p) => (
    <svg {...base(p?.s)}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18z" /></svg>
  ),
  map: (p) => (
    <svg {...base(p?.s)}><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" /><path d="M9 4v14M15 6v14" /></svg>
  ),
  building: (p) => (
    <svg {...base(p?.s)}><rect x="4" y="3" width="16" height="18" rx="1.5" /><path d="M9 8h.01M15 8h.01M9 12h.01M15 12h.01M10 21v-4h4v4" /></svg>
  ),
  users: (p) => (
    <svg {...base(p?.s)}><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5" /><circle cx="18" cy="9" r="2.4" /><path d="M16 20c.3-2.5 1.6-4 4-4" /></svg>
  ),
  x: (p) => (
    <svg {...base(p?.s)}><path d="M18 6 6 18M6 6l12 12" /></svg>
  ),
  more: (p) => (
    <svg {...base(p?.s)}><circle cx="5" cy="12" r="1.4" /><circle cx="12" cy="12" r="1.4" /><circle cx="19" cy="12" r="1.4" /></svg>
  ),
};

export default Icon;
