/*
 * Service Worker: hält alle Dateien des Programms auf dem Gerät vor, damit die
 * installierte App ohne Internet startet.
 *
 * Mit Netz kommt jede Datei frisch vom Server (der Browser-Zwischenspeicher
 * wird dabei übergangen) und der Vorrat wird aufgefrischt. So passen Seite,
 * Gestaltung und Skripte nach einem Update immer zusammen – eine Mischung aus
 * altem und neuem Stand zerlegt die Oberfläche. Nur ohne Netz, oder wenn der
 * Server nach drei Sekunden nicht geantwortet hat, springt der Vorrat ein.
 *
 * Kommt eine Datei dazu, hier eintragen und CACHE hochzählen.
 */
const CACHE = 'kurs-planer-v2';
const TIMEOUT = 3000;                    // Millisekunden bis zum Rückgriff auf den Vorrat
const FILES = [
  './',
  'index.html',
  'manifest.webmanifest',
  'css/style.css',
  'js/config.js',
  'js/elements.js',
  'js/editor.js',
  'js/export.js',
  'js/file.js',
  'js/app.js',
  'vendor/konva.min.js',
  'vendor/jspdf.umd.min.js',
  'icons/icon.svg',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-512.png',
  'icons/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(FILES.map((url) => new Request(url, { cache: 'reload' }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((name) => name !== CACHE).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(request, { ignoreSearch: true });
      const fresh = fetch(request.url, { cache: 'no-cache' }).then((response) => {
        if (response.ok) cache.put(request, response.clone());
        return response;
      });
      if (!cached) return fresh;
      event.waitUntil(fresh.catch(() => {}));       // Vorrat auch nach dem Rückgriff auffrischen
      const fallback = new Promise((resolve) => setTimeout(() => resolve(cached), TIMEOUT));
      return Promise.race([fresh.catch(() => cached), fallback]);
    })
  );
});
