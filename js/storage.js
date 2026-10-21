// ============================================================
// storage.js — onde as coisas ficam guardadas no aparelho.
// Textos, marcas e carrosséis vão para o localStorage (pequeno,
// mas simples). Fotos e logos vão para o IndexedDB, que tem
// muito mais espaço. Cada imagem ganha um código (ex.: img-…)
// e os slides guardam só esse código.
// ============================================================

const STATE_KEY = 'carrossel-estudio:v2';
const OLD_KEY = 'carrossel-editorial:v1';   // versão anterior do editor
const DB_NAME = 'carrossel-estudio';
const STORE = 'imagens';

// ---------- Estado (textos, marcas, carrosséis) ----------

export function loadState() {
  try {
    return JSON.parse(localStorage.getItem(STATE_KEY));
  } catch {
    return null;
  }
}

export function saveState(state) {
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function loadOldProject() {
  try {
    const old = JSON.parse(localStorage.getItem(OLD_KEY));
    return old && Array.isArray(old.slides) && old.slides.length ? old : null;
  } catch {
    return null;
  }
}

// Pede ao navegador para não apagar os dados sozinho.
// (Nem todo navegador atende; por isso existe a cópia de segurança.)
export function requestPersistence() {
  navigator.storage?.persist?.().catch(() => {});
}

// ---------- Imagens ----------

// Reserva na memória, caso o IndexedDB não esteja disponível
// (ex.: navegação privada). Nesse caso as fotos somem ao fechar.
const memory = new Map();

let dbPromise;
function openDB() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve) => {
      try {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(STORE);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }
  return dbPromise;
}

function run(db, mode, action) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const req = action(tx.objectStore(STORE));
    tx.oncomplete = () => resolve(req.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

export function newImageId() {
  return `img-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

// Guarda uma imagem (Blob) e devolve o código dela.
export async function putImage(blob, id = newImageId()) {
  const db = await openDB();
  if (db) {
    try {
      await run(db, 'readwrite', (s) => s.put(blob, id));
      return id;
    } catch {
      // cai para a memória
    }
  }
  memory.set(id, blob);
  return id;
}

export async function getImageBlob(id) {
  if (!id) return null;
  if (memory.has(id)) return memory.get(id);
  const db = await openDB();
  if (!db) return null;
  try {
    return (await run(db, 'readonly', (s) => s.get(id))) || null;
  } catch {
    return null;
  }
}

// Apaga as imagens que nenhum slide ou marca usa mais.
export async function removeUnusedImages(usedIds) {
  const db = await openDB();
  if (!db) return;
  try {
    const keys = await run(db, 'readonly', (s) => s.getAllKeys());
    const unused = keys.filter((k) => !usedIds.has(k));
    if (unused.length) await run(db, 'readwrite', (s) => { unused.forEach((k) => s.delete(k)); return s.count(); });
  } catch {
    // sem problema: tenta de novo na próxima vez
  }
}

export function isPersistentStorage() {
  return openDB().then(Boolean);
}
