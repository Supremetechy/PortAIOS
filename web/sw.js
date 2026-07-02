// AIOS service worker — no-op, clears any stale registration from previous sessions
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => {
  event.waitUntil(
    self.registration.unregister()
      .then(() => self.clients.claim())
  );
});
