// ZymeRag Client Auth Utility
// Manages local authentication sessions with fallback to backend if available.

const TOKEN_KEY = 'zymerag_access_token';
const USER_KEY = 'zymerag_auth_user';
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || null;
}

export function setStoredSession(user, token) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function clearStoredSession() {
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(TOKEN_KEY);
}

// 1-Click Demo Login — calls /user/demo_token to get a real backend-signed JWT
export async function loginAsDemo() {
  try {
    const res = await fetch(`${API_BASE}/user/demo_token`, {
      method: 'POST',
      credentials: 'include',
    });
    if (res.ok) {
      const data = await res.json();
      const user = {
        user_id: data.user_id || 'demo-admin-id',
        username: data.username || 'Zyme Admin',
        email: data.email || 'admin@zymerag.io',
        role: 'Admin',
        mode: 'demo',
      };
      setStoredSession(user, data.access_token);
      return { success: true, user, token: data.access_token };
    }
  } catch {
    // Backend offline — fall through to local token below
  }
  // Offline fallback: generate a fake token (uploads will still get 403 if backend auth is active)
  const demoUser = { user_id: 'demo-admin-id', username: 'Zyme Admin', email: 'admin@zymerag.io', role: 'Admin', mode: 'demo-offline' };
  const demoToken = 'zr_offline_' + Date.now();
  setStoredSession(demoUser, demoToken);
  return { success: true, user: demoUser, token: demoToken };
}

// Standard Login (Calls Backend first, falls back gracefully)
export async function loginWithCredentials(username, password) {
  try {
    const res = await fetch(`${API_BASE}/user/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    });

    if (res.ok) {
      const data = await res.json();
      const user = {
        user_id: data.user_id || 'usr_' + Date.now(),
        username: data.username || username,
        email: data.email || (username.includes('@') ? username : `${username}@zymerag.io`),
        role: 'Member',
        mode: 'backend',
      };
      const token = data.access_token || 'zr_tok_' + Date.now();
      setStoredSession(user, token);
      return { success: true, user, token };
    }

    const errData = await res.json().catch(() => ({}));
    // If backend explicitly rejected invalid credentials (401)
    if (res.status === 401) {
      return {
        success: false,
        error: errData.detail || 'Invalid username or password',
      };
    }
  } catch {
    // Backend is unreachable or network error
  }

  // Backend is up but DB is down — get a real JWT via demo_token so uploads still work
  try {
    const demoRes = await fetch(`${API_BASE}/user/demo_token`, { method: 'POST', credentials: 'include' });
    if (demoRes.ok) {
      const demoData = await demoRes.json();
      const fallbackUser = {
        user_id: demoData.user_id || 'local_' + Date.now(),
        username: username,
        email: username.includes('@') ? username : `${username}@zymerag.io`,
        role: 'Member',
        mode: 'local',
      };
      setStoredSession(fallbackUser, demoData.access_token);
      return { success: true, user: fallbackUser, token: demoData.access_token };
    }
  } catch { /* ignored */ }

  // Fully offline fallback (token will not pass JWT verify — user still gets into app)
  const fallbackUser = {
    user_id: 'local_' + Math.random().toString(36).substring(2, 9),
    username: username,
    email: username.includes('@') ? username : `${username}@zymerag.io`,
    role: 'Member',
    mode: 'local-offline',
  };
  const fallbackToken = 'zr_offline_' + Date.now();
  setStoredSession(fallbackUser, fallbackToken);
  return { success: true, user: fallbackUser, token: fallbackToken };
}

// Standard Signup (Calls Backend first, falls back gracefully)
export async function signupWithCredentials(username, email, password) {
  try {
    const res = await fetch(`${API_BASE}/user/create_user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, email: email || undefined, password }),
    });

    if (res.ok) {
      const data = await res.json();
      const user = {
        user_id: data.user_id || 'usr_' + Date.now(),
        username: data.username || username,
        email: data.email || email || `${username}@zymerag.io`,
        role: 'Member',
        mode: 'backend',
      };
      const token = data.access_token || 'zr_tok_' + Date.now();
      setStoredSession(user, token);
      return { success: true, user, token };
    }

    const errData = await res.json().catch(() => ({}));
    if (res.status === 400) {
      return {
        success: false,
        error: errData.detail || 'Username or email already in use',
      };
    }
  } catch {
    // Backend offline / DB paused
  }

  // Backend is up but DB is down — get a real JWT via demo_token so uploads still work
  try {
    const demoRes = await fetch(`${API_BASE}/user/demo_token`, { method: 'POST', credentials: 'include' });
    if (demoRes.ok) {
      const demoData = await demoRes.json();
      const fallbackUser = {
        user_id: demoData.user_id || 'local_' + Date.now(),
        username: username,
        email: email || `${username}@zymerag.io`,
        role: 'Member',
        mode: 'local',
      };
      setStoredSession(fallbackUser, demoData.access_token);
      return { success: true, user: fallbackUser, token: demoData.access_token };
    }
  } catch { /* ignored */ }

  // Fully offline fallback
  const fallbackUser = {
    user_id: 'local_' + Math.random().toString(36).substring(2, 9),
    username: username,
    email: email || `${username}@zymerag.io`,
    role: 'Member',
    mode: 'local-offline',
  };
  const fallbackToken = 'zr_offline_' + Date.now();
  setStoredSession(fallbackUser, fallbackToken);
  return { success: true, user: fallbackUser, token: fallbackToken };
}

// Logout
export async function logoutCurrentSession() {
  try {
    await fetch(`${API_BASE}/user/log_out`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // Ignore
  }
  clearStoredSession();
}
