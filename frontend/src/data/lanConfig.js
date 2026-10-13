// ================= Live Agent Network config — EDIT HERE =================
export const LAN_TITLE = "Live Agent Network";
export const LAN_CENTER = { name: "Orion", subtitle: "AI Orchestrator" };

// ADD / REMOVE / REORDER agents. First one sits at the top, the rest go clockwise.
// color: key of LAN_COLORS | icon: key of LAN_ICONS or a full "<svg ...>...</svg>" string
// onClick (optional): runs when the tile is clicked
export const LAN_AGENTS = [
  { name: "Research", color: "blue", icon: "research" },
  { name: "Finance", color: "sky", icon: "finance" },
  { name: "Operations", color: "blue", icon: "operations" },
  { name: "Product", color: "purple", icon: "product" },
  { name: "HR", color: "blue", icon: "people" },
  { name: "HR", color: "green", icon: "cap" },
  { name: "Legal", color: "blue", icon: "legal" },
  { name: "Marketing", color: "purple", icon: "marketing" },
];

export const LAN_COLORS = {
  blue: { c: "#1d63f0", n1: "#f3f6ff", n2: "#e7eeff", nb: "#d5e0fb", ns: "rgba(70,110,230,.20)" },
  sky: { c: "#1a8cf5", n1: "#f1f7ff", n2: "#e4f0ff", nb: "#cfe2fb", ns: "rgba(40,140,240,.20)" },
  purple: { c: "#5b3df5", n1: "#f7f3ff", n2: "#eee7ff", nb: "#ded3fa", ns: "rgba(130,90,240,.20)" },
  green: { c: "#16a05a", n1: "#f0fdf6", n2: "#e0f9ec", nb: "#bdeed3", ns: "rgba(30,180,110,.22)" },
  orange: { c: "#f0790f", n1: "#fff8f0", n2: "#ffefdc", nb: "#fbd9b4", ns: "rgba(240,130,30,.22)" },
  pink: { c: "#e11d74", n1: "#fff3f8", n2: "#ffe4ef", nb: "#f9c6db", ns: "rgba(225,40,120,.20)" },
};

export const LAN_ICONS = {
  research: '<path d="M5 2h8l5 5v4.3a6 6 0 0 0-7.6 8.7H5a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1zm7 1.5V8h4.5zM7 10h4v1.6H7zm0 3h3v1.6H7zm10 .5a4 4 0 1 1-2.3 7.3l-2.6 2.5-1.1-1.1 2.5-2.6A4 4 0 0 1 17 13.5zm0 1.8a2.2 2.2 0 1 0 0 4.4 2.2 2.2 0 0 0 0-4.4z"/>',
  finance: '<path d="M12 2a4.5 4.5 0 0 1 2.5 8.2A8 8 0 0 1 20 18v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a8 8 0 0 1 5.5-7.8A4.5 4.5 0 0 1 12 2zm0 2.2a2.3 2.3 0 1 0 0 4.6 2.3 2.3 0 0 0 0-4.6zM12 12.5c-3 0-5.6 2.2-5.8 5.5h11.6c-.2-3.3-2.8-5.5-5.8-5.5z"/>',
  operations: '<path d="M12 1a6 6 0 0 1 3.5 10.9L12 21 8.5 11.9A6 6 0 0 1 12 1zm0 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM3.5 14a1.5 1.5 0 0 1 3 0c0 2 2.5 3.5 5.5 4.5 3-1 5.5-2.5 5.5-4.5a1.5 1.5 0 0 1 3 0c0 4-4 6.5-8.5 8C7.5 20.5 3.5 18 3.5 14z"/>',
  product: '<path d="M9 2h6v2h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h3zm1.5 1.5v2h3v-2zM8 10h8v1.8H8zm0 3.5h8v1.8H8zm0 3.5h5v1.8H8z"/>',
  people: '<path d="M9 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zm7.5 1a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM9 13c3.3 0 6 1.8 6 4.5V20H3v-2.5C3 14.8 5.7 13 9 13zm7.5.5c2.5 0 4.5 1.6 4.5 3.8V20h-4v-2.5c0-1.6-.6-3-1.7-4z"/>',
  cap: '<path d="M12 2L1.5 7.5 12 13l8.5-4.5V15h2V7.5zM5 12.5V17c0 2 3.1 4 7 4s7-2 7-4v-4.5L12 16.2z"/>',
  legal: '<path d="M6 2h12a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm2.5 5v2h7V7zm0 4v2h7v-2zm0 4v2H13v-2z"/>',
  marketing: '<path d="M5 2h9a2 2 0 0 1 2 2v3h3a2 2 0 0 1 2 2v13h-6V4H7v18H3V4a2 2 0 0 1 2-2zm5 10v4h2v-4zm-3 2.5V16h1.5v-1.5zm6-3.5v5H15v-5z"/>',
};

// Ellipse the tiles sit on (coordinate space 1510 x 940)
export const LAN_LAYOUT = { W: 1510, H: 940, cx: 755, cy: 470, rx: 386, ry: 328, startAngle: -90, node: 168, coreR: 158 };
