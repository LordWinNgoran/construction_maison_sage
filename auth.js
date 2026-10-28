(function () {
  'use strict';

  const STORAGE_KEY = 'maquette_3d_access';
  const SESSION_DURATION_MS = 12 * 60 * 60 * 1000;
  const ACCESS_CODE_HASH = '267f9beef1de2f7e3ba6f4387a41554b4289bd0481ade921c4e7640c96ea2ef2';

  function readSession() {
    try {
      const session = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!session || session.expiresAt <= Date.now()) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
      return session;
    } catch (_) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
  }

  async function sha256(value) {
    const bytes = new TextEncoder().encode(value);
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  async function authorize(code) {
    const candidate = await sha256(String(code).trim());
    if (candidate !== ACCESS_CODE_HASH) return false;

    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      expiresAt: Date.now() + SESSION_DURATION_MS
    }));
    return true;
  }

  function isAuthorized() {
    return Boolean(readSession());
  }

  function requireAuth(loginPath) {
    if (isAuthorized()) return true;
    window.location.replace(new URL(loginPath || '../index.html', window.location.href));
    return false;
  }

  function logout(loginPath) {
    localStorage.removeItem(STORAGE_KEY);
    window.location.replace(new URL(loginPath || '../index.html', window.location.href));
  }

  window.MaquetteAuth = { authorize, isAuthorized, requireAuth, logout };
}());
