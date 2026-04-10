from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings

@require_http_methods(["GET"])
def manifest(request, tenant_slug):
    """
    Serve manifest.json with tenant-specific start_url.
    
    URL: /<tenant_slug>/manifest.json
    Example: /seniors-place/manifest.json
    
    Returns manifest with proper icon paths.
    """
    return JsonResponse({
        "name": "GetCore POS",
        "short_name": "GetCore",
        "start_url": f"/{tenant_slug}/pos/",
        "scope": f"/{tenant_slug}/",
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
    """
    Serve service-worker.js directly from Django view.
    
    URL: /service-worker.js
    """
    service_worker_code = """// Service Worker for GetCore POS PWA
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
"""
    
    response = HttpResponse(service_worker_code, content_type='application/javascript')
    response['Cache-Control'] = 'public, max-age=3600'
    response.status_code = 200
    return response
