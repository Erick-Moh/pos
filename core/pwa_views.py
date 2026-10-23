"""
core/pwa_views.py
Serves the PWA manifest and service worker — no tenant dependency.
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def manifest(request):
    """Serve manifest.json for the PWA."""
    return JsonResponse({
        "name": "GetCore POS",
        "short_name": "GetCore",
        "start_url": "/pos/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "theme_color": "#1f2937",
        "background_color": "#ffffff",
        "icons": [
            {
                "src": "/static/img/manifest-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/img/manifest-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            }
        ],
        "categories": ["business", "productivity"],
        "screenshots": [
            {
                "src": "/static/img/manifest-192.png",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }, content_type='application/manifest+json')


@require_http_methods(["GET"])
def service_worker(request):
    """Serve service-worker.js directly from Django view."""
    sw_code = """// Service Worker for GetCore POS PWA
const CACHE_NAME = 'getcore-pos-v1';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => Promise.all(
      cacheNames
        .filter(n => n !== CACHE_NAME)
        .map(n => caches.delete(n))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== location.origin || request.method !== 'GET') return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            caches.open(CACHE_NAME).then(c => c.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request).then(cached => cached || fetch(request).then(response => {
        if (response.ok) caches.open(CACHE_NAME).then(c => c.put(request, response.clone()));
        return response;
      }))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        if (response.ok) caches.open(CACHE_NAME).then(c => c.put(request, response.clone()));
        return response;
      })
      .catch(() => caches.match(request))
  );
});
"""
    response = HttpResponse(sw_code, content_type='application/javascript')
    response['Cache-Control'] = 'public, max-age=3600'
    return response
