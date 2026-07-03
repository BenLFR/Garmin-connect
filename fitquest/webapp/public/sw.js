// FitQuest service worker — minimal, no build plugin.
// /api/* is NEVER cached (live game data); navigations are network-first
// with the cached shell as offline fallback; hashed assets are cache-first.
const CACHE = 'fitquest-v1'
const SHELL = ['/', '/manifest.webmanifest']

self.addEventListener('install', (e) => {
  self.skipWaiting()
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/')) return // network only, always

  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          caches.open(CACHE).then((c) => c.put('/', res.clone()))
          return res
        })
        .catch(() => caches.match('/'))
    )
    return
  }

  if (e.request.method === 'GET') {
    e.respondWith(
      caches.match(e.request).then(
        (hit) => hit || fetch(e.request).then((res) => {
          if (res.ok) caches.open(CACHE).then((c) => c.put(e.request, res.clone()))
          return res
        })
      )
    )
  }
})
