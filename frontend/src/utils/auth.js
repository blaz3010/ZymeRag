// ZymeRag Client Auth Utility
// Manages local authentication sessions with fallback to backend if available.

const TOKEN_KEY = 'zymerag_access_token';
const USER_KEY = 'zymerag_auth_user';
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const user = JSON.parse(raw);
    // Only sessions backed by a real backend-issued token are valid.
    if (user?.mode !== 'backend' || !localStorage.getItem(TOKEN_KEY)) {
      clearStoredSession();
      return null;
    }
    return user;
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

// Standard Login — requires a real authenticated backend session
export async function loginWithCredentials(username, password) {
  let res;
  try {
    res = await fetch(`${API_BASE}/user/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    });
  } catch {
    return { success: false, error: 'Cannot reach the server. Please try again.' };
  }

  if (res.ok) {
    const data = await res.json();
    if (!data.access_token) {
      return { success: false, error: 'Login failed: no access token returned' };
    }
    const user = {
      user_id: data.user_id,
      username: data.username || username,
      email: data.email || (username.includes('@') ? username : `${username}@zymerag.io`),
      role: 'Member',
      mode: 'backend',
    };
    setStoredSession(user, data.access_token);
    return { success: true, user, token: data.access_token };
  }

  const errData = await res.json().catch(() => ({}));
  if (res.status === 401) {
    return { success: false, error: errData.detail || 'Invalid username or password' };
  }
  return { success: false, error: errData.detail || `Login failed (${res.status})` };
}

// Standard Signup — requires a real authenticated backend session
export async function signupWithCredentials(username, email, password) {
  let res;
  try {
    res = await fetch(`${API_BASE}/user/create_user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, email: email || undefined, password }),
    });
  } catch {
    return { success: false, error: 'Cannot reach the server. Please try again.' };
  }

  if (res.ok) {
    const data = await res.json();
    if (!data.access_token) {
      return { success: false, error: 'Signup failed: no access token returned' };
    }
    const user = {
      user_id: data.user_id,
      username: data.username || username,
      email: data.email || email || `${username}@zymerag.io`,
      role: 'Member',
      mode: 'backend',
    };
    setStoredSession(user, data.access_token);
    return { success: true, user, token: data.access_token };
  }

  const errData = await res.json().catch(() => ({}));
  if (res.status === 400) {
    return { success: false, error: errData.detail || 'Username or email already in use' };
  }
  return { success: false, error: errData.detail || `Signup failed (${res.status})` };
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
