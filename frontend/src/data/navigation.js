// Sidebar navigation config — edit labels / ids / svg icons here.
// `svg` holds the inner markup of a 0 0 24 24 viewBox icon. Icons are FILLED
// (solid glyphs, use currentColor via `.nav-svg { fill: currentColor }`).
export const NAV_ITEMS = [
  {
    id: "dashboard",
    label: "Dashboard",
    // Solid house
    svg: '<path d="M11.3 2.7a1 1 0 0 1 1.4 0l8.5 8a1 1 0 0 1-.7 1.7H20V20a1.5 1.5 0 0 1-1.5 1.5H14.5v-5.25a1.25 1.25 0 0 0-1.25-1.25h-2.5a1.25 1.25 0 0 0-1.25 1.25V21.5H5.5A1.5 1.5 0 0 1 4 20v-7.6H2.5a1 1 0 0 1-.7-1.7z"/>',
  },
  {
    id: "command-center",
    label: "Command Center",
    // Solid speech bubble with three dots
    svg: '<path d="M4 3.5h16A1.5 1.5 0 0 1 21.5 5v10A1.5 1.5 0 0 1 20 16.5H9.8L6 20.3a.9.9 0 0 1-1.5-.64V16.5H4A1.5 1.5 0 0 1 2.5 15V5A1.5 1.5 0 0 1 4 3.5zM8 9a1.3 1.3 0 1 0 0 2.6A1.3 1.3 0 0 0 8 9zm4 0a1.3 1.3 0 1 0 0 2.6A1.3 1.3 0 0 0 12 9zm4 0a1.3 1.3 0 1 0 0 2.6A1.3 1.3 0 0 0 16 9z"/>',
  },
  {
    id: "missions",
    label: "Missions",
    // Target with center dot + arrow feel
    svg: '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 4.2A5.8 5.8 0 1 1 6.2 12 5.8 5.8 0 0 1 12 6.2zm0 3.3A2.5 2.5 0 1 0 14.5 12 2.5 2.5 0 0 0 12 9.5z"/>',
  },
  {
    id: "approvals",
    label: "Approvals",
    badge: { text: "5", color: "rose" },
    // Solid clipboard with check
    svg: '<path d="M9 2.5h6a1 1 0 0 1 1 1V4h1.5A1.5 1.5 0 0 1 19 5.5v14A1.5 1.5 0 0 1 17.5 21h-11A1.5 1.5 0 0 1 5 19.5v-14A1.5 1.5 0 0 1 6.5 4H8v-.5a1 1 0 0 1 1-1zm.5 2V6h5V4.5zm6.7 6.1a1 1 0 0 0-1.4-1.4l-3.5 3.5-1.3-1.3a1 1 0 1 0-1.4 1.4l2 2a1 1 0 0 0 1.4 0z"/>',
  },
  {
    id: "notifications",
    label: "Notifications",
    badge: { text: "12", color: "indigo" },
    // Solid bell
    svg: '<path d="M12 2.5a5.5 5.5 0 0 1 5.5 5.5c0 3.4.8 5.3 1.6 6.4a1.2 1.2 0 0 1-1 1.9H5.9a1.2 1.2 0 0 1-1-1.9C5.7 13.3 6.5 11.4 6.5 8A5.5 5.5 0 0 1 12 2.5zM9.8 18.5h4.4a2.2 2.2 0 0 1-4.4 0z"/>',
  },
];

export const WORKSPACE_ITEMS = [
  {
    id: "departments",
    label: "Departments",
    // Solid org chart (three nodes)
    svg: '<path d="M9.5 3h5A1.5 1.5 0 0 1 16 4.5v2A1.5 1.5 0 0 1 14.5 8h-1.4v2.5H19A1.5 1.5 0 0 1 20.5 12v1H22v.5H2.5V13H4v-1a1.5 1.5 0 0 1 1.5-1.5h5.6V8H9.5A1.5 1.5 0 0 1 8 6.5v-2A1.5 1.5 0 0 1 9.5 3zM3 15.5h5A1 1 0 0 1 9 16.5v4A1 1 0 0 1 8 21.5H3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1zm13 0h5a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1z"/>',
  },
  {
    id: "agents",
    label: "Agents",
    // Solid users (two people)
    svg: '<path d="M9 3.5A3.5 3.5 0 1 1 5.5 7 3.5 3.5 0 0 1 9 3.5zm7 1a3 3 0 0 1 0 6 3.4 3.4 0 0 0 0-6zM9 12.5c3.6 0 6.5 2.2 6.5 5.5v1.5A1 1 0 0 1 14.5 20.5h-11A1 1 0 0 1 2.5 19.5V18c0-3.3 2.9-5.5 6.5-5.5zm7.5.2c2.6.4 4.5 2.3 4.5 4.8v1.5a1 1 0 0 1-1 1H17.3a2.6 2.6 0 0 0 .2-1v-1.7a6.4 6.4 0 0 0-1-3.3z"/>',
  },
  {
    id: "knowledge",
    label: "Knowledge",
    // Solid database
    svg: '<path d="M12 2c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zm8 6.2V11c0 1.7-3.6 3-8 3s-8-1.3-8-3V8.2c1.7 1.2 4.7 1.8 8 1.8s6.3-.6 8-1.8zm0 5V16c0 1.7-3.6 3-8 3s-8-1.3-8-3v-2.8c1.7 1.2 4.7 1.8 8 1.8s6.3-.6 8-1.8z"/>',
  },
  {
    id: "tools",
    label: "Tools",
    // Solid link / wrench-cross
    svg: '<path d="M14.8 3.5a5 5 0 0 1 5.7 8l-2.3 2.3a1 1 0 0 1-1.4-1.4l2.3-2.3a3 3 0 0 0-4.2-4.2l-2.3 2.3a1 1 0 0 1-1.4-1.4l2.3-2.3a5 5 0 0 1 1.6-1zM9.2 20.5a5 5 0 0 1-5.7-8l2.3-2.3a1 1 0 0 1 1.4 1.4l-2.3 2.3a3 3 0 0 0 4.2 4.2l2.3-2.3a1 1 0 0 1 1.4 1.4l-2.3 2.3a5 5 0 0 1-1.6 1zm-.9-6.8a1 1 0 0 1 0-1.4l4-4a1 1 0 0 1 1.4 1.4l-4 4a1 1 0 0 1-1.4 0z"/>',
  },
  {
    id: "operations",
    label: "Operations",
    // Solid sliders / filters
    svg: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="8" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="10" cy="18" r="2"/>',
  },
  {
    id: "observability",
    label: "Observability",
    // Solid gauge / activity circle
    svg: '<path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm-2 5.5a1 1 0 0 1 1 1v6.1l3-2.4a1 1 0 0 1 1.3 1.6l-4.7 3.7A1 1 0 0 1 9 16.7V8.5a1 1 0 0 1 1-1z"/>',
  },
];


// Sub-tabs for the Agents section (Section 5). Shared by the Sidebar (nested
// items under "Agents") and the in-page tab bar so they stay in sync.
export const AGENTS_SUBTABS = [
  { id: "overview", label: "Overview" },
  { id: "create", label: "Create" },
  { id: "builder", label: "Builder" },
  { id: "templates", label: "Templates" },
  { id: "testing", label: "Testing" },
  { id: "performance", label: "Performance" },
  { id: "settings", label: "Settings" },
];

// Sub-tabs for the Tools section. Shared by the Sidebar (nested items under
// "Tools") and the in-page tab bar so they stay in sync — same pattern as Agents.
export const TOOLS_SUBTABS = [
  { id: "overview", label: "All Tools" },
  { id: "mcp", label: "MCP Servers" },
  { id: "integrations", label: "Integrations" },
  { id: "custom", label: "Custom Tools" },
  { id: "api-keys", label: "API Keys" },
];

// Knowledge & Memory sub-views (view ids match App routes).
export const KNOWLEDGE_SUBTABS = [
  { id: "knowledge", label: "Knowledge Base" },
  { id: "knowledge-upload", label: "Upload Sources" },
  { id: "knowledge-memory-overview", label: "Memory Overview" },
  { id: "knowledge-memory-details", label: "Memory Details" },
  { id: "knowledge-memory-settings", label: "Memory Settings" },
];

// Operations sub-views (view ids match App routes).
export const OPERATIONS_SUBTABS = [
  { id: "operations", label: "Overview" },
  { id: "operations-finance", label: "Finance" },
  { id: "operations-sales", label: "Sales" },
  { id: "operations-inventory", label: "Inventory" },
  { id: "operations-marketing", label: "Marketing" },
  { id: "operations-crm", label: "Customers / CRM" },
  { id: "operations-hr", label: "Employees / HR" },
  { id: "operations-research", label: "Research" },
  { id: "operations-suppliers", label: "Suppliers" },
  { id: "operations-website", label: "Website" },
];

// Departments sub-views (view ids match App routes).
export const DEPARTMENTS_SUBTABS = [
  { id: "departments", label: "All Departments" },
  { id: "department-marketing", label: "Marketing" },
  { id: "department-finance", label: "Finance" },
  { id: "department-operations", label: "Operations" },
  { id: "department-sales", label: "Sales" },
  { id: "department-hr", label: "HR" },
  { id: "department-research", label: "Research" },
];

// Marketing department sub-views (view ids match App routes).
export const MARKETING_SUBTABS = [
  { id: "department-marketing", label: "Overview" },
  { id: "marketing-activity", label: "Activity" },
  { id: "marketing-members", label: "Members" },
  { id: "marketing-settings", label: "Settings" },
];

// Finance department sub-views (view ids match App routes).
export const FINANCE_SUBTABS = [
  { id: "department-finance", label: "Overview" },
  { id: "finance-activity", label: "Activity" },
  { id: "finance-members", label: "Members" },
  { id: "finance-settings", label: "Settings" },
];

// Operations department sub-views (view ids match App routes).
export const OPERATIONS_DEPT_SUBTABS = [
  { id: "department-operations", label: "Overview" },
  { id: "operations-activity", label: "Activity" },
  { id: "operations-members", label: "Members" },
  { id: "operations-settings", label: "Settings" },
];

// Sales department sub-views (view ids match App routes).
export const SALES_SUBTABS = [
  { id: "department-sales", label: "Overview" },
  { id: "sales-activity", label: "Activity" },
  { id: "sales-members", label: "Members" },
  { id: "sales-settings", label: "Settings" },
];

// HR department sub-views (view ids match App routes).
export const HR_SUBTABS = [
  { id: "department-hr", label: "Overview" },
  { id: "hr-activity", label: "Activity" },
  { id: "hr-members", label: "Members" },
  { id: "hr-settings", label: "Settings" },
];

// Research department sub-views (view ids match App routes).
export const RESEARCH_SUBTABS = [
  { id: "department-research", label: "Overview" },
  { id: "research-activity", label: "Activity" },
  { id: "research-members", label: "Members" },
  { id: "research-settings", label: "Settings" },
];

// Observability sub-views (view ids match App routes).
export const OBSERVABILITY_SUBTABS = [
  { id: "observability", label: "Dashboard" },
  { id: "observability-runs", label: "Runs / Sessions" },
  { id: "observability-trace", label: "Trace Details" },
  { id: "observability-tools", label: "Tool Usage" },
  { id: "observability-llm", label: "LLM Usage & Costs" },
  { id: "observability-errors", label: "Errors & Failures" },
  { id: "observability-evaluations", label: "Evaluations" },
  { id: "observability-audit", label: "Audit Logs" },
  { id: "observability-website", label: "Website" },
];

// Settings & Profile — opened from Orion Workspace (not main sidebar).
// Descriptions match Section 10 menu cards.
export const SETTINGS_SUBTABS = [
  { id: "settings", label: "Profile", desc: "Personal information and preferences." },
  { id: "settings-workspace", label: "Workspace Settings", desc: "Workspace details, members, roles." },
  { id: "settings-security", label: "Security", desc: "Authentication, 2FA, access control." },
  { id: "settings-billing", label: "Billing & Subscription", desc: "Plan, usage, invoices." },
  { id: "settings-api", label: "API Access", desc: "API keys and developer settings." },
  { id: "settings-preferences", label: "Preferences", desc: "UI, notifications, language, timezone." },
  { id: "settings-help", label: "Help & Support", desc: "Documentation and support." },
  { id: "settings-logout", label: "Logout", desc: "Sign out from workspace." },
];
