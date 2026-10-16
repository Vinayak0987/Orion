// chatApi — client for the multi-conversation Command Center (Orion v2 :8081).
//
// Conversations and messages are persisted server-side so chats survive reloads.
// Global context is a small set of durable facts injected into every mission.

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

export const chatApi = {
  base: V2_BASE,

  // --- conversations ---
  listConversations: () => req("/conversations").then((d) => d.conversations),
  createConversation: (title) => req("/conversations", { method: "POST", body: { title } }),
  getConversation: (id) => req(`/conversations/${id}`),
  renameConversation: (id, title) => req(`/conversations/${id}`, { method: "PUT", body: { title } }),
  deleteConversation: (id) => req(`/conversations/${id}`, { method: "DELETE" }),

  // --- messages ---
  addMessage: (conversationId, message) =>
    req(`/conversations/${conversationId}/messages`, { method: "POST", body: message }),
  updateMessage: (messageId, fields) =>
    req(`/messages/${messageId}`, { method: "PUT", body: fields }),

  // --- global context ---
  listContext: () => req("/context").then((d) => d.context),
  setContext: (key, value) => req("/context", { method: "PUT", body: { key, value } }),
  deleteContext: (key) => req(`/context/${encodeURIComponent(key)}`, { method: "DELETE" }),
};
