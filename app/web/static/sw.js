// TradingPro Service Worker - bumped version on every release
// CACHE_NAME מועדכן בכל deploy כדי לכפות רענון static assets

const CACHE_NAME = 'tp-v3-2026-05-13';
const STATIC_ASSETS = ['/static/icon.svg', '/static/manifest.json'];

self.addEventListener('install', e => {
  // התקנה מיידית, ללא המתנה ל-tab ישן להיסגר
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(c => c.addAll(STATIC_ASSETS).catch(() => {}))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    // נקה את כל caches ישנים
    const keys = await caches.keys();
    await Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = e.request.url;

  // API: לא נוגעים - תמיד טרי מהרשת
  if (url.includes('/api/')) return;

  // HTML / דפים דינמיים: network-first ללא fallback ל-cache
  // מבטיח שמשתמשים תמיד מקבלים את הגרסה הטרייה
  const isHTML =
    e.request.destination === 'document' ||
    url.endsWith('/') ||
    url.endsWith('.html');
  if (isHTML) {
    e.respondWith(
      fetch(e.request, { cache: 'no-store' })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // static assets: stale-while-revalidate
  e.respondWith((async () => {
    const cached = await caches.match(e.request);
    const fetchPromise = fetch(e.request)
      .then(fresh => {
        if (fresh && fresh.ok) {
          caches.open(CACHE_NAME)
            .then(c => c.put(e.request, fresh.clone()).catch(() => {}));
        }
        return fresh;
      })
      .catch(() => cached);
    return cached || fetchPromise;
  })());
});
