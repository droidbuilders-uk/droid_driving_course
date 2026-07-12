// Dummy service worker to prevent 404s
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // Claim any clients immediately
    event.waitUntil(clients.claim());
});
