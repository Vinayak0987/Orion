// authApi — the client for the backend /auth/* endpoints.
//
// Token model (mirrors the backend):
//   • access token — kept in memory only (this module), sent as
//     `Authorization: Bearer`. Not persisted, so it's not exposed to XSS via
//     localStorage; a page reload re-derives it from the refresh cookie.
//   • refresh token — an httpOnly cookie the browser stores and sends
//     automatically; JS never sees it. All auth requests use
//     `credentials: "include"` so the cookie flows.
//
// authFetch() attaches the bearer token and, on a 401, transparently tries a
// single refresh-then-retry before giving up.

const API_BASE =
  import.meta.env.VITE_V2_API_BASE_URL ??
  import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8081";

let accessToken = null;

export function getAccessToken() {
  return accessToken;
}
export function setAccessToken(token) {
  accessToken = token ?? null;
}
export function clearAccessToken() {
  accessToken = null;
}

async function parse(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    /* empty / non-JSON body */
  }
  if (!response.ok) {
    const message = body?.detail ?? `HTTP ${response.status}`;
    const error = new Error(typeof message === "string" ? message : "Request failed");
    error.status = response.status;
    throw error;
  }
  return body;
}

async function rawPost(path, json) {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: json ? JSON.stringify(json) : undefined,
  });
}

export const authApi = {
  base: API_BASE,

  async signup({ fullName, email, password }) {
    const body = await parse(
      await rawPost("/auth/signup", { full_name: fullName, email, password })
    );
    setAccessToken(body.access_token);
    return body;
  },

  async login({ email, password }) {
    const body = await parse(await rawPost("/auth/login", { email, password }));
    setAccessToken(body.access_token);
    return body;
  },

  // Exchange the refresh cookie for a new access token. Used on app start and
  // by authFetch on a 401. Returns the token payload or throws.
  async refresh() {
    const body = await parse(await rawPost("/auth/refresh", null));
    setAccessToken(body.access_token);
    return body;
  },

  async logout() {
    try {
      await rawPost("/auth/logout", null);
    } finally {
      clearAccessToken();
    }
  },

  async me() {
    return authFetch("/auth/me");
  },

  async updateMe({ fullName, email, jobTitle, bio }) {
    const body = {};
    if (fullName !== undefined) body.full_name = fullName;
    if (email !== undefined) body.email = email;
    if (jobTitle !== undefined) body.job_title = jobTitle;
    if (bio !== undefined) body.bio = bio;
    return authFetch("/auth/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  },

  async uploadFile(file) {
    const form = new FormData();
    form.append("file", file);
    return authFetch("/uploads", { method: "POST", body: form });
  },

  async changePassword({ currentPassword, newPassword }) {
    return authFetch("/auth/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  async uploadAvatar(file) {
    const form = new FormData();
    form.append("file", file);
    // Note: do NOT set Content-Type — the browser sets the multipart boundary.
    return authFetch("/auth/avatar", { method: "POST", body: form });
  },

  // --- Workspace ---------------------------------------------------------
  getWorkspace() {
    return authFetch("/workspace");
  },
  updateWorkspace(fields) {
    return authFetch("/workspace", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    });
  },
  getMembers() {
    return authFetch("/workspace/members");
  },
  addMember({ name, email, role }) {
    return authFetch("/workspace/members", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, role }),
    });
  },
  updateMember(id, fields) {
    return authFetch(`/workspace/members/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    });
  },
  removeMember(id) {
    return authFetch(`/workspace/members/${id}`, { method: "DELETE" });
  },
};

// Authenticated fetch for any protected endpoint: attaches the bearer token and
// retries once after a refresh if the access token was rejected.
export async function authFetch(path, options = {}) {
  const doFetch = () =>
    fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let response = await doFetch();
  if (response.status === 401 && accessToken !== null) {
    // Access token likely expired — try one refresh, then retry the request.
    try {
      await authApi.refresh();
      response = await doFetch();
    } catch {
      clearAccessToken();
    }
  }
  return parse(response);
}
