// Mission Engine API client (Orion v2 backend).
//
// Separate from the legacy api.js so the two backends never get confused.
// The v2 backend serves the dynamic mission engine (planner → agents → tools).

const V2_BASE = import.meta.env.VITE_V2_API_BASE_URL ?? "http://localhost:8081";

function v2Ws(path) {
  return `${V2_BASE.replace(/^http/, "ws")}${path}`;
}

async function getJson(path) {
  const res = await fetch(`${V2_BASE}${path}`);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep status */
    }
    throw new Error(detail);
  }
  return res.json();
}

async function postJson(path, body) {
  const res = await fetch(`${V2_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const result = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(result.detail ?? `HTTP ${res.status}`);
  return result;
}

export const missionApi = {
  base: V2_BASE,
  health: () => getJson("/health"),
  createMission: (prompt, { departmentId = null, conversationId = null, clarified = false, mode = "action" } = {}) =>
    postJson("/missions", {
      prompt,
      department_id: departmentId,
      conversation_id: conversationId,
      clarified,
      mode,
    }),
  missions: (limit = 50) => getJson(`/missions?limit=${limit}`),
  missionsQuery: ({ limit = 50, offset = 0, status = "", search = "", type = "" } = {}) => {
    const p = new URLSearchParams({ limit, offset });
    if (status) p.set("status", status);
    if (search) p.set("search", search);
    if (type) p.set("type", type);
    return getJson(`/missions?${p.toString()}`);
  },
  mission: (id) => getJson(`/missions/${id}`),
  listApprovals: () => getJson("/approvals"),
  resolveApproval: (approvalId, approved, always = false) =>
    postJson(`/approvals/${approvalId}`, { approved, always }),
  missionTools: (id) => getJson(`/missions/${id}/tools`),
  missionEvidence: (id) => getJson(`/missions/${id}/evidence`),
  missionTrace: (id) => getJson(`/missions/${id}/trace`),
  exportMissionJson: (id) => getJson(`/missions/${id}/export.json`),
  deleteMission: async (id) => {
    const res = await fetch(`${V2_BASE}/missions/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`Could not delete (HTTP ${res.status})`);
    return res.json();
  },
  stopMission: (id) =>
    fetch(`${V2_BASE}/missions/${id}/stop`, { method: "POST" }).then((r) => r.json().catch(() => ({}))),
  approveDecision: (decisionId) => postJson(`/decisions/${decisionId}/approve`, {}),
  rejectDecision: (decisionId) => postJson(`/decisions/${decisionId}/reject`, {}),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${V2_BASE}/knowledge/documents`, { method: "POST", body: form }).then((r) => {
      if (!r.ok) throw new Error(`Upload failed (HTTP ${r.status})`);
      return r.json();
    });
  },
  apiKeys: () => getJson("/settings/api-keys"),
  saveApiKeys: (keys) =>
    fetch(`${V2_BASE}/settings/api-keys`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(keys),
    }).then((r) => r.json()),
  deleteApiKey: (provider) =>
    fetch(`${V2_BASE}/settings/api-keys/${provider}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(`Could not delete key (HTTP ${r.status})`);
      return r.json();
    }),
  customKeys: () => getJson("/settings/api-keys/custom"),
  addCustomKey: (name, value) => postJson("/settings/api-keys/custom", { name, value }),
  deleteCustomKey: (slug) =>
    fetch(`${V2_BASE}/settings/api-keys/custom/${slug}`, { method: "DELETE" }).then((r) => {
      if (!r.ok) throw new Error(`Could not delete key (HTTP ${r.status})`);
      return r.json();
    }),
};

/**
 * Stream a running mission over WebSocket.
 *
 * Connect AFTER createMission() returns, using the returned mission_id. The
 * backend buffers events, so any emitted before the socket opens are replayed.
 *
 * Returns a cancel() function. Callbacks receive each typed event.
 */
export function streamMission(missionId, { onEvent, onDone, onError } = {}) {
  const socket = new WebSocket(v2Ws(`/ws/missions/${missionId}`));
  let closed = false;

  socket.onmessage = (msg) => {
    let payload;
    try {
      payload = JSON.parse(msg.data);
    } catch {
      return;
    }
    onEvent?.(payload);
    if (payload.event === "mission_completed" || payload.event === "mission_failed") {
      onDone?.(payload);
    }
  };

  socket.onerror = () => {
    if (!closed) onError?.(`Cannot reach the mission backend at ${V2_BASE}.`);
  };

  socket.onclose = () => {
    if (!closed) onDone?.(null);
  };

  return () => {
    closed = true;
    socket.close();
  };
}
