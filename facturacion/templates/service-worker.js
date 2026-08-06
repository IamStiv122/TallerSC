// CarServ — Service Worker PWA
const CACHE_NAME = 'carserv-v2';

// Recursos principales a cachear al instalar el SW
const STATIC_ASSETS = [
  '/',
  '/login/',
  '/static/css/bootstrap.min.css',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/img/favicon.ico',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
];

// Instalación: cachear recursos estáticos principales
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activación: limpiar cachés anteriores
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: estrategia Network First (intenta red, si falla usa caché)
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Solo manejar peticiones GET
  if (event.request.method !== 'GET') return;

  // No interceptar recursos de dominios externos (CDNs)
  // Solo manejar recursos del mismo origen
  if (url.origin !== self.location.origin) return;

  // No interceptar llamadas al admin de Django
  if (url.pathname.startsWith('/admin/')) return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Solo cachear respuestas válidas del mismo origen
        if (response && response.status === 200 && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Sin red: servir desde caché
        return caches.match(event.request).then(cached => {
          if (cached) return cached;
          // Página offline genérica si no hay caché
          if (event.request.destination === 'document') {
            return caches.match('/');
          }
        });
      })
  );
});
