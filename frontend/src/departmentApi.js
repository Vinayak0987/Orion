// departmentApi — client for the Departments section + schedules (Orion v2 :8081).

const V2_BASE = import.meta.env.VITE_V2_API_BASE_URL ?? "http://localhost:8081";

async function req(path, { method = "GET", body } = {}) {
  const res = await fetch(`${V2_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data && data.detail;
    const msg = typeof d === "string" ? d
      : Array.isArray(d) ? d.map((e) => e.msg).join("; ")
      : `Request failed (HTTP ${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export const departmentApi = {
  base: V2_BASE,

  list: ({ status = "", search = "" } = {}) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    if (search) p.set("search", search);
    return req(`/departments?${p.toString()}`);
  },
  get: (id) => req(`/departments/${id}`),
  create: (dept) => req("/departments", { method: "POST", body: dept }),
  update: (id, changes) => req(`/departments/${id}`, { method: "PUT", body: changes }),
  archive: (id) => req(`/departments/${id}`, { method: "DELETE" }),
  architect: (description) => req("/departments/architect", { method: "POST", body: { description } }),

  members: (id) => req(`/departments/${id}/members`),
  missions: (id) => req(`/departments/${id}/missions`),
  activity: (id) => req(`/departments/${id}/activity`),

  // Schedules (cron-ish)
  schedules: (id) => req(`/departments/${id}/schedules`),
  createSchedule: (id, body) => req(`/departments/${id}/schedules`, { method: "POST", body }),
  deleteSchedule: (sid) => req(`/schedules/${sid}`, { method: "DELETE" }),
  toggleSchedule: (sid, enabled) => req(`/schedules/${sid}/toggle?enabled=${enabled}`, { method: "POST" }),
};
