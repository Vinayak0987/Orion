// toolApi — client for the Tools section (Orion v2 :8081).
//
// Core tool registry + custom tools + MCP + integrations use the open v2 base
// (default-user, like missionApi). OAuth endpoints are user-scoped, so they go
// through authFetch (bearer token + refresh-retry) from authApi.

import { authFetch } from "./auth/authApi";

const V2_BASE = import.meta.env.VITE_V2_API_BASE_URL ?? "http://localhost:8081";

async function req(path, { method = "GET", body } = {}) {
  const res = await fetch(`${V2_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data;
}

export const toolApi = {
  base: V2_BASE,

  // --- registry ---
  list: ({ type = "", category = "", enabled = null, search = "" } = {}) => {
    const p = new URLSearchParams();
    if (type) p.set("type", type);
    if (category) p.set("category", category);
    if (enabled !== null) p.set("enabled", enabled);
    if (search) p.set("search", search);
    return req(`/tools?${p.toString()}`);
  },
  get: (name) => req(`/tools/${encodeURIComponent(name)}`),
  setEnabled: (name, enabled) => req(`/tools/${encodeURIComponent(name)}`, { method: "PUT", body: { enabled } }),
  update: (name, fields) => req(`/tools/${encodeURIComponent(name)}`, { method: "PUT", body: fields }),
  remove: (name) => req(`/tools/${encodeURIComponent(name)}`, { method: "DELETE" }),
  execute: (name, input) => req("/tools/execute", { method: "POST", body: { name, input } }),

  // --- custom tools ---
  createCustom: (tool) => req("/tools/custom", { method: "POST", body: tool }),
  updateCustom: (name, tool) => req(`/tools/custom/${encodeURIComponent(name)}`, { method: "PUT", body: tool }),

  // --- MCP ---
  listMcp: () => req("/tools/mcp"),
  connectMcp: (server) => req("/tools/mcp", { method: "POST", body: server }),
  disconnectMcp: (serverId) => req(`/tools/mcp/${serverId}`, { method: "DELETE" }),
  reconnectMcp: (serverId) => req(`/tools/mcp/${serverId}/connect`, { method: "POST" }),
  removeMcp: (serverId) => req(`/tools/mcp/${serverId}/remove`, { method: "DELETE" }),

  // --- token-based integrations (existing) ---
  listIntegrations: () => req("/tools/integrations"),
  connectIntegration: (id, credential) =>
    req(`/tools/integrations/${id}/connect`, { method: "POST", body: { credential } }),
  disconnectIntegration: (id) => req(`/tools/integrations/${id}/disconnect`, { method: "POST" }),

  // --- OAuth integrations (user-scoped, authenticated) ---
  oauthProviders: () => authFetch("/oauth/providers"),
  oauthConnections: () => authFetch("/oauth/connections"),
  oauthAuthorize: (provider) => authFetch(`/oauth/${provider}/authorize`),
  oauthRefresh: (provider) => authFetch(`/oauth/${provider}/refresh`, { method: "POST" }),
  oauthReconnect: (provider) => authFetch(`/oauth/${provider}/reconnect`, { method: "POST" }),
  oauthDisconnect: (provider) => authFetch(`/oauth/${provider}`, { method: "DELETE" }),
};
