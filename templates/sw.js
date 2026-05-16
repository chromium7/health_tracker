/* HealthTracker service worker.
 *
 * Provides an installable PWA shell. For now the strategy is
 * network-first with a small offline shell cached at install time;
 * full offline support is a future enhancement.
 */

const CACHE_NAME = 'healthtracker-shell-v1';
const SHELL_URLS = [
  '/',
  '/login/',
  '{% static "css/main.css" %}',
  '/manifest.webmanifest'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS)).catch(() => undefined)
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          if (response.ok && new URL(request.url).origin === self.location.origin) {
            cache.put(request, copy);
          }
        }).catch(() => undefined);
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('/')))
  );
});
