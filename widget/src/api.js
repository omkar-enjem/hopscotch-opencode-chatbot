// Thin API client for the Guddi backend.
// In dev, Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.js).
// In production set VITE_API_BASE to your backend origin.

const API_BASE = import.meta.env.VITE_API_BASE || ''

const SESSION_KEY = 'guddi_session_id'

export function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

export function resetSession() {
  const id = (crypto.randomUUID && crypto.randomUUID()) || `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`
  localStorage.setItem(SESSION_KEY, id)
  return id
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error(`health ${res.status}`)
  return res.json()
}

export async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function getHistory(sessionId) {
  const res = await fetch(`${API_BASE}/api/session/${encodeURIComponent(sessionId)}/history`)
  if (!res.ok) throw new Error(`history ${res.status}`)
  return res.json()
}
