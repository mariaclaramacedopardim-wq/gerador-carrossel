/* Service worker do Fichário: deixa o app abrir sem internet.
   Os dados do usuário ficam no aparelho (localStorage e IndexedDB), nunca aqui. */
const VERSAO = "fichario-v4";
const BASE = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const c = await caches.open(VERSAO);
    await c.addAll(BASE);
    const imgs = await (await fetch("img/lista.json", { cache: "no-store" })).json();
    await c.addAll(imgs.map(n => "img/" + n));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k !== VERSAO) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (req.mode === "navigate") {
    // página: tenta a rede (pega atualizações) e cai no cache se estiver offline
    e.respondWith(fetch(req).then(r => { const cp = r.clone(); caches.open(VERSAO).then(c => c.put("index.html", cp)); return r; })
      .catch(() => caches.match("index.html")));
    return;
  }
  if (url.origin === location.origin) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => { const cp = r.clone(); caches.open(VERSAO).then(c => c.put(req, cp)); return r; })));
    return;
  }
  // fontes e jszip (outros domínios): usa o cache e atualiza em segundo plano
  e.respondWith(caches.open(VERSAO).then(async c => {
    const hit = await c.match(req);
    const net = fetch(req).then(r => { if (r.ok || r.type === "opaque") c.put(req, r.clone()); return r; }).catch(() => hit);
    return hit || net;
  }));
});
