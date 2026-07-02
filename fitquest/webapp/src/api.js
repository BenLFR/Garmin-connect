// Thin API client. 409 = onboarding required (no profile yet).

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
}
