// Service Worker for GetCore POS PWA
const CACHE_NAME = 'getcore-pos-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME)
          .map(cacheName => caches.delete(cacheName))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== location.origin || request.method !== 'GET') {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const cache_copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, cache_copy));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request).then(response => {
        return response || fetch(request).then(response => {
          if (response.ok) {
            const cache_copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, cache_copy));
          }
          return response;
        });
      })
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        if (response.ok) {
          const cache_copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, cache_copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
