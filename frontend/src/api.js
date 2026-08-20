// Backend client. Single place that knows the API shape, so components stay
// declarative and the base URL is configured once.

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

function wsUrl(path) {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}${path}`;
}

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // non-JSON error body; keep the status text
    }
    throw new Error(detail);
  }
  return response.json();
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail ?? `HTTP ${response.status}`);
  return result;
}

function enc(value) {
  return encodeURIComponent(value);
}

export const api = {
  base: API_BASE,
  health: () => getJson("/health"),
  sectionCatalogue: () => getJson("/sections"),
  sessions: () => getJson("/sessions?limit=50"),
  session: (id) => getJson(`/sessions/${id}`),
  package: (id) => getJson(`/sessions/${id}/package`),
  section: (id, key) => getJson(`/sessions/${id}/sections/${key}`),
  reportUrl: (id) => `${API_BASE}/sessions/${id}/report`,
  pdfUrl: (id) => `${API_BASE}/sessions/${id}/report.pdf`,

  async deleteSession(id) {
    const response = await fetch(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error(`Could not delete session (HTTP ${response.status})`);
    return response.json();
  },

  async intent(prompt) {
    const response = await fetch(`${API_BASE}/intent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail ?? "Intent classification failed");
    return body;
  },

  // =========================================================================
  // Operating layer
  // =========================================================================
  operating: {
    anchors: (companyId) =>
      getJson(`/operating/anchors?company_id=${enc(companyId)}`),

    anchorHistory: (companyId, points = 30) =>
      getJson(`/operating/anchors/history?company_id=${enc(companyId)}&points=${points}`),

    findings: (companyId, limit = 50) =>
      getJson(`/operating/findings?company_id=${enc(companyId)}&limit=${limit}`),

    decisions: (companyId, state = null) => {
      let url = `/operating/decisions?company_id=${enc(companyId)}`;
      if (state) url += `&state=${enc(state)}`;
      return getJson(url);
    },

    async approve(decisionId, by) {
      return postJson(`/operating/decisions/${enc(decisionId)}/approve`, { by });
    },

    async reject(decisionId, by, reason = "") {
      return postJson(`/operating/decisions/${enc(decisionId)}/reject`, { by, reason });
    },

    async returnDecision(decisionId, by, reason) {
      return postJson(`/operating/decisions/${enc(decisionId)}/return`, { by, reason });
    },

    audit: (decisionId) =>
      getJson(`/operating/audit/${enc(decisionId)}`),

    constitution: () => getJson("/operating/constitution"),

    loops: () => getJson("/operating/loops"),

    schedule: (companyId) =>
      getJson(`/operating/schedule?company_id=${enc(companyId)}`),

    runs: (companyId, loopId = null, limit = 100) => {
      let url = `/operating/runs?company_id=${enc(companyId)}&limit=${limit}`;
      if (loopId) url += `&loop_id=${enc(loopId)}`;
      return getJson(url);
    },

    ledger: (companyId, limit = 100) =>
      getJson(`/operating/ledger?company_id=${enc(companyId)}&limit=${limit}`),

    memory: (companyId, department) =>
      getJson(`/operating/memory?company_id=${enc(companyId)}&department=${enc(department)}`),

    departments: () => getJson("/operating/departments"),

    async tick(companyId) {
      return postJson("/operating/tick", { company_id: companyId });
    },
  },
};

/**
 * F48 - stream a generation over WebSocket.
 *
 * Returns a `cancel()` function. Callbacks:
 *   onEvent(event)    every progress event
 *   onResult(summary) the completed run
 *   onError(message)  validation or generation failure, or a transport drop
 */
export function streamGeneration({ prompt, forceAllDepartments = false, onEvent, onResult, onError }) {
  const socket = new WebSocket(wsUrl("/ws/generate"));
  let settled = false;

  socket.onopen = () => {
    socket.send(JSON.stringify({ prompt, force_all_departments: forceAllDepartments }));
  };

  socket.onmessage = (message) => {
    let payload;
    try {
      payload = JSON.parse(message.data);
    } catch {
      return;
    }

    if (payload.event === "result") {
      settled = true;
      onResult?.(payload.summary);
      return;
    }
    if (payload.event === "error") {
      settled = true;
      onError?.(payload.detail, payload.kind);
      return;
    }
    onEvent?.(payload);
  };

  socket.onerror = () => {
    if (!settled) onError?.(`Cannot reach the backend at ${API_BASE}.`, "transport");
  };

  socket.onclose = (closeEvent) => {
    if (!settled && !closeEvent.wasClean) {
      onError?.("Connection to the backend was lost mid-generation.", "transport");
    }
  };

  return () => {
    settled = true;
    socket.close();
  };
}
