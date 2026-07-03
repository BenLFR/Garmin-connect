// Thin API client. On game routes, 409 = onboarding required (no profile
// yet); on the garmin auth routes 409 is a real error (no pending login).

async function reqStrict(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || res.statusText)
  return res.json()
}

async function req(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 409) return { onboardingRequired: true }
  if (!res.ok) throw new Error((await res.json().catch(() => ({})))?.detail || res.statusText)
  return res.json()
}

export const api = {
  getState: () => req('/api/state'),
  analyze: (mode) => req('/api/onboarding/analyze', { method: 'POST', body: JSON.stringify({ mode }) }),
  choose: (mode, playerClass, playerName) =>
    req('/api/onboarding/choose', { method: 'POST', body: JSON.stringify({ mode, playerClass, playerName }) }),
  sync: () => req('/api/sync', { method: 'POST' }),
  activities: () => req('/api/activities'),
  reset: () => req('/api/reset', { method: 'POST' }),
  garminStatus: () => reqStrict('/api/garmin/status'),
  garminLogin: (email, password) =>
    reqStrict('/api/garmin/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  garminMfa: (code) => reqStrict('/api/garmin/mfa', { method: 'POST', body: JSON.stringify({ code }) }),
  equip: (slot, itemId) =>
    reqStrict('/api/cosmetics/equip', { method: 'POST', body: JSON.stringify({ slot, itemId }) }),
}
