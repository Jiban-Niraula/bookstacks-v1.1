/**
 * Shared session helpers, loaded on every page (auth pages + dashboard).
 * Keeps token storage, the authenticated fetch wrapper, and small utility
 * functions in one place instead of duplicated per page.
 */

const TOKEN_KEY = 'bookstacks_token';
const USER_KEY = 'bookstacks_user';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * fetch wrapper that attaches the auth token and bounces back to the
 * login page if the session has expired or was revoked server-side.
 */
async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    clearSession();
    window.location.href = '/login.html';
  }
  return res;
}

// Wire up "Log out" wherever it appears (currently just the dashboard topbar).
document.addEventListener('DOMContentLoaded', () => {
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      clearSession();
      window.location.href = '/login.html';
    });
  }
});
