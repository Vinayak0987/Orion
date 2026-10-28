// knowledgeApi — client for the Knowledge section (Orion v2 :8081).

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

export const knowledgeApi = {
  base: V2_BASE,

  // --- documents ---
  listDocuments: ({ type = "", status = "", search = "" } = {}) => {
    const p = new URLSearchParams();
    if (type) p.set("type", type);
    if (status) p.set("status", status);
    if (search) p.set("search", search);
    return req(`/knowledge/documents?${p.toString()}`);
  },
  getDocument: (id, includeChunks = true) =>
    req(`/knowledge/documents/${id}?include_chunks=${includeChunks}`),
  deleteDocument: (id) => req(`/knowledge/documents/${id}`, { method: "DELETE" }),
  reindexDocument: (id) => req(`/knowledge/documents/${id}/reindex`, { method: "POST" }),
  indexDocument: (id) => req(`/knowledge/documents/${id}/index`, { method: "POST" }),
  ingestUrl: (url, name) => req("/knowledge/documents/url", { method: "POST", body: { url, name } }),
  uploadDocument: (file, departmentId, index = false) => {
    const form = new FormData();
    form.append("file", file);
    if (departmentId) form.append("department_id", departmentId);
    form.append("index", index ? "true" : "false");
    return fetch(`${V2_BASE}/knowledge/documents`, { method: "POST", body: form }).then(async (r) => {
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail ?? `Upload failed (HTTP ${r.status})`);
      return d;
    });
  },
  search: (query, limit = 5) => req("/knowledge/search", { method: "POST", body: { query, limit } }),

  // --- Google Drive source ---
  driveStatus: () => req("/knowledge/sources/drive/status"),
  drivePickerConfig: () => req("/knowledge/sources/drive/picker-config"),
  driveFiles: (q = "") => req(`/knowledge/sources/drive/files${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  driveImport: (file_id, name, mime_type) =>
    req("/knowledge/sources/drive/import", { method: "POST", body: { file_id, name, mime_type } }),

  // --- Microsoft OneDrive/SharePoint ---
  msStatus: () => req("/knowledge/sources/ms/status"),
  msFiles: (q = "") => req(`/knowledge/sources/ms/files${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  msImport: (file_id, name) => req("/knowledge/sources/ms/import", { method: "POST", body: { file_id, name } }),

  // --- GitHub ---
  githubStatus: () => req("/knowledge/sources/github/status"),
  githubRepos: () => req("/knowledge/sources/github/repos"),
  githubFiles: (repo, path = "") => req(`/knowledge/sources/github/files?repo=${encodeURIComponent(repo)}${path ? `&path=${encodeURIComponent(path)}` : ""}`),
  githubImport: (repo, path) => req("/knowledge/sources/github/import", { method: "POST", body: { repo, path } }),

  // --- Slack ---
  slackStatus: () => req("/knowledge/sources/slack/status"),
  slackFiles: () => req("/knowledge/sources/slack/files"),
  slackImport: (url, name) => req("/knowledge/sources/slack/import", { method: "POST", body: { url, name } }),

  // --- memory ---
  listMemory: (agentId = "") =>
    req(`/knowledge/memory${agentId ? `?agent_id=${agentId}` : ""}`),
  deleteMemory: (entryId) => req(`/knowledge/memory/${entryId}`, { method: "DELETE" }),
  clearAgentMemory: (agentId) =>
    req(`/knowledge/memory/agent/${agentId}?confirm=CLEAR`, { method: "DELETE" }),
  getMemorySettings: () => req("/knowledge/memory/settings"),
  updateMemorySettings: (settings) =>
    req("/knowledge/memory/settings", { method: "PUT", body: settings }),
};
