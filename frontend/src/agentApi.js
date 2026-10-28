// agentApi — client for the Agents section (Orion v2 :8081).

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

export const agentApi = {
  base: V2_BASE,

  list: ({ status = "active", type = "", departmentId = "" } = {}) => {
    const p = new URLSearchParams({ status });
    if (type) p.set("type", type);
    if (departmentId) p.set("department_id", departmentId);
    return req(`/agents?${p.toString()}`);
  },
  get: (id) => req(`/agents/${id}`),
  architect: (body) => req("/agents/architect", { method: "POST", body }),
  create: (agent) => req("/agents", { method: "POST", body: agent }),
  update: (id, changes) => req(`/agents/${id}`, { method: "PUT", body: changes }),
  remove: (id) => req(`/agents/${id}`, { method: "DELETE" }),
  clone: (id, name) => req(`/agents/${id}/clone`, { method: "POST", body: { name } }),
  versions: (id) => req(`/agents/${id}/versions`),
  performance: (id) => req(`/agents/${id}/performance`),
  test: (id, message) => req(`/agents/${id}/test`, { method: "POST", body: { message } }),

  templates: () => req("/agents/templates"),
  fromTemplate: (templateId, name) =>
    req(`/agents/from-template/${templateId}`, { method: "POST", body: { name } }),
};
