// Minimal service worker for PWA installability
// Strategy: network-first, cache fallback for offline shell
const CACHE = 'tp-v1';
const SHELL = ['/', '/static/icon.svg', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(()=>{})));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  // Don't cache API calls
  if (e.request.url.includes('/api/')) return;
  e.respondWith((async () => {
    try {
      const fresh = await fetch(e.request);
      if (fresh && fresh.ok) {
        const cache = await caches.open(CACHE);
        cache.put(e.request, fresh.clone()).catch(()=>{});
      }
      return fresh;
    } catch {
      const cached = await caches.match(e.request);
      return cached || Response.error();
    }
  })());
});
