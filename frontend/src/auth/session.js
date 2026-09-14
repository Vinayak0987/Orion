// session — auth session helpers backed by the real backend.
//
// The source of truth for "logged in" is holding a valid access token in
// memory (authApi). A refresh cookie (httpOnly) lets us re-establish that token
// on a fresh page load via restoreSession(). The introSeen flag stays in
// sessionStorage (pure UI concern).

import { authApi, clearAccessToken, getAccessToken } from "./authApi";

const INTRO_KEY = "orion.introSeen";

// Try to re-establish a session from the refresh cookie. Returns the user on
// success, or null if there is no valid session. Safe to call on app start.
export async function restoreSession() {
  try {
    const body = await authApi.refresh();
    return body.user ?? null;
  } catch {
    clearAccessToken();
    return null;
  }
}

export function isAuthenticated() {
  return getAccessToken() !== null;
}

export async function logout() {
  await authApi.logout();
}

export function hasSeenIntro() {
  try {
    return sessionStorage.getItem(INTRO_KEY) === "1";
  } catch (e) {
    return false;
  }
}

export function markIntroSeen() {
  try {
    sessionStorage.setItem(INTRO_KEY, "1");
  } catch (e) {
    /* ignore */
  }
}
