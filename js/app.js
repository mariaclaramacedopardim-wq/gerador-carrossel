// ============================================================
// app.js — liga a interface ao desenho dos slides.
// Guarda marcas e carrosséis, responde aos campos do painel,
// desenha a pré-visualização e exporta os PNGs.
// ============================================================

import {
  PALETTES, TITLE_FONTS, BODY_FONTS, LAYOUTS, STYLES,
  findStyle, newSlide, newBrand, newCarousel, newId, createDefaultState,
} from './data.js';
import { SLIDE_W, SLIDE_H, renderSlide, loadFonts } from './render.js';
import { parseScript } from './roteiro.js';
import * as storage from './storage.js';

const THUMB_SCALE = 0.2;   // miniaturas em 216 × 270

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

// state = { brands: [...], carousels: [...], currentCarouselId }
let state;
let current = 0;           // slide aberto

const carousel = () => state.carousels.find((c) => c.id === state.currentCarouselId) || state.carousels[0];
const brandOf = (c) => state.brands.find((b) => b.id === c.brandId) || state.brands[0];
const brand = () => brandOf(carousel());
const slides = () => carousel().slides;

// ---------- Carregar e salvar ----------

function isValidState(s) {
  return s && Array.isArray(s.brands) && s.brands.length
    && Array.isArray(s.carousels) && s.carousels.length
    && s.carousels.every((c) => Array.isArray(c.slides) && c.slides.length);
}

// Corrige referências quebradas (ex.: marca excluída).
function repairState(s) {
  const ids = new Set(s.brands.map((b) => b.id));
  s.carousels.forEach((c) => { if (!ids.has(c.brandId)) c.brandId = s.brands[0].id; });
  if (!s.carousels.some((c) => c.id === s.currentCarouselId)) s.currentCarouselId = s.carousels[0].id;
  return s;
}

async function dataURLToBlob(url) {
  return (await fetch(url)).blob();
}

// Traz o projeto da versão anterior do editor (um carrossel só,
// com as fotos guardadas como texto) para o formato novo.
async function migrateOldProject(old) {
  const b = newBrand({
    name: 'Minha marca',
    styleId: 'editorial',
    paletteId: old.paletteId,
    colors: { ...old.colors },
    titleFontId: old.titleFontId,
    bodyFontId: old.bodyFontId,
    handle: old.handle || '',
    showNumbers: old.showNumbers !== false,
  });
  const migrated = [];
  for (const s of old.slides) {
    let image = null;
    if (typeof s.image === 'string' && s.image.startsWith('data:')) {
      try { image = await storage.putImage(await dataURLToBlob(s.image)); } catch { image = null; }
    }
    migrated.push(newSlide({ ...s, image }));
  }
  const c = newCarousel({ name: 'Meu carrossel', brandId: b.id, slides: migrated });
  return { version: 2, brands: [b], carousels: [c], currentCarouselId: c.id };
}

async function loadInitialState() {
  const saved = storage.loadState();
  if (isValidState(saved)) return repairState(saved);
  const old = storage.loadOldProject();
  if (old) {
    const migrated = await migrateOldProject(old);
    storage.saveState(migrated);
    return migrated;
  }
  return createDefaultState();
}

let saveTimer;
function saveSoon() {
  carousel().updatedAt = Date.now();
  delete state.pristine;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 400);
}

function saveNow() {
  setStatus(storage.saveState(state) ? 'Salvo neste aparelho' : 'Não foi possível salvar');
}

let statusTimer;
function setStatus(text) {
  $('#status').textContent = text;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => { $('#status').textContent = ''; }, 2500);
}

// Códigos de todas as imagens em uso (para limpar as que sobraram).
function usedImageIds() {
  const ids = new Set();
  state.brands.forEach((b) => b.logo && ids.add(b.logo));
  state.carousels.forEach((c) => c.slides.forEach((s) => s.image && ids.add(s.image)));
  return ids;
}

// ---------- Tema e imagens ----------

// Imagens guardadas no aparelho → <img> pronta para desenhar.
// Cada código é carregado uma única vez e reaproveitado.
const imageCache = new Map();

function getImage(id) {
  if (!id) return Promise.resolve(null);
  if (!imageCache.has(id)) {
    imageCache.set(id, storage.getImageBlob(id).then((blob) => new Promise((resolve) => {
      if (!blob) return resolve(null);
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = URL.createObjectURL(blob);
    })));
  }
  return imageCache.get(id);
}

async function theme() {
  const b = brand();
  return {
    colors: b.colors,
    style: findStyle(b.styleId),
    titleFont: TITLE_FONTS.find((f) => f.id === b.titleFontId) || TITLE_FONTS[0],
    bodyFont: BODY_FONTS.find((f) => f.id === b.bodyFontId) || BODY_FONTS[0],
    handle: (b.handle || '').trim(),
    showNumbers: b.showNumbers,
    logo: await getImage(b.logo),
  };
}

// Reduz fotos muito grandes (fotos do iPad têm 12+ megapixels)
// para no máximo 2000 px — mais leve e ainda nítido em 1080 px.
// Logos ficam em PNG para manter o fundo transparente.
async function fileToBlob(file, { maxSide = 2000, type = 'image/jpeg' } = {}) {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = reject;
      i.src = url;
    });
    const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, type, 0.88));
    canvas.width = canvas.height = 0;
    if (!blob) throw new Error('imagem inválida');
    return blob;
  } finally {
    URL.revokeObjectURL(url);
  }
}

// ---------- Desenho ----------

async function drawSlide(canvas, index, scale, preview, t) {
  const slide = slides()[index];
  const image = await getImage(slide.image);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  renderSlide(ctx, { slide, index, total: slides().length, theme: t, image, preview });
}

// Junta várias mudanças seguidas (ex.: digitação) num só desenho.
let renderQueued = false;
function render() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(async () => {
    renderQueued = false;
    const t = await theme();
    await loadFonts(t);
    await drawSlide($('#preview-canvas'), current, 1, true, t);
    const thumbs = $$('#strip .thumb canvas');
    await Promise.all(thumbs.map((c, i) => drawSlide(c, i, THUMB_SCALE, true, t)));
    $('#stage-title').innerHTML = '';
    $('#stage-title').append(Object.assign(document.createElement('strong'), { textContent: carousel().name }), ` · ${brand().name}`);
    $('#preview-meta').textContent = `Slide ${current + 1} de ${slides().length} · 1080 × 1350 px`;
    $('#prev').disabled = current === 0;
    $('#next').disabled = current === slides().length - 1;
  });
}

// ---------- Faixa de miniaturas ----------

function buildStrip() {
  const strip = $('#strip');
  strip.innerHTML = '';
  slides().forEach((_, i) => {
    const btn = document.createElement('button');
    btn.className = 'thumb' + (i === current ? ' is-active' : '');
    btn.setAttribute('aria-label', `Slide ${i + 1}`);
    const c = document.createElement('canvas');
    c.width = SLIDE_W * THUMB_SCALE;
    c.height = SLIDE_H * THUMB_SCALE;
    const num = document.createElement('span');
    num.className = 'thumb-num';
    num.textContent = i + 1;
    btn.append(c, num);
    btn.addEventListener('click', () => select(i));
    strip.append(btn);
  });
  const add = document.createElement('button');
  add.className = 'thumb-add';
  add.innerHTML = '<strong>+</strong>Novo slide';
  add.addEventListener('click', addSlide);
  strip.append(add);
}

function select(i) {
  current = Math.max(0, Math.min(slides().length - 1, i));
  $$('#strip .thumb').forEach((t, n) => t.classList.toggle('is-active', n === current));
  $$('#strip .thumb')[current]?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  fillSlideForm();
  render();
}

// Mudanças na quantidade/ordem dos slides
function structureChanged(newIndex) {
  current = newIndex;
  buildStrip();
  select(newIndex);
  saveSoon();
}

function addSlide() {
  const prev = slides()[current]?.layout;
  const layout = prev === 'capa' || prev === 'final' ? 'conteudo' : prev || 'conteudo';
  slides().splice(current + 1, 0, newSlide({ layout }));
  structureChanged(current + 1);
}

// Troca tudo o que aparece (ao abrir outro carrossel ou marca).
function refreshAll() {
  fillBrandPanel();
  fillCarouselPanel();
  buildStrip();
  select(Math.min(current, slides().length - 1));
}

// ---------- Aba "Slide" ----------

function buildLayoutPicker() {
  const box = $('#layout-picker');
  LAYOUTS.forEach((l) => {
    const b = document.createElement('button');
    b.textContent = l.name;
    b.dataset.layout = l.id;
    b.addEventListener('click', () => {
      slides()[current].layout = l.id;
      fillSlideForm();
      render();
      saveSoon();
    });
    box.append(b);
  });
}

function fillSlideForm() {
  const s = slides()[current];
  const layout = LAYOUTS.find((l) => l.id === s.layout) || LAYOUTS[1];
  $$('#layout-picker button').forEach((b) => b.classList.toggle('is-active', b.dataset.layout === s.layout));
  $('#label-kicker').textContent = layout.labels.kicker;
  $('#label-title').textContent = layout.labels.title;
  $('#label-body').textContent = layout.labels.body;
  $$('[data-field]').forEach((el) => { el.value = s[el.dataset.field] ?? ''; });
  $('#image-controls').hidden = !layout.image;
  $('#range-overlay').hidden = s.layout !== 'capa' || !s.image;
  $('#range-pos').hidden = !s.image;
  $('#image-remove').hidden = !s.image;
  $('#image-btn-label').textContent = s.image ? 'Trocar foto' : 'Escolher foto';
  $('#move-left').disabled = current === 0;
  $('#move-right').disabled = current === slides().length - 1;
  $('#delete').disabled = slides().length === 1;
}

function bindSlideForm() {
  $$('[data-field]').forEach((el) => {
    el.addEventListener('input', () => {
      const v = el.hasAttribute('data-number') ? Number(el.value) : el.value;
      slides()[current][el.dataset.field] = v;
      render();
      saveSoon();
    });
  });

  $('#image-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    setStatus('Carregando foto…');
    try {
      slides()[current].image = await storage.putImage(await fileToBlob(file));
      fillSlideForm();
      render();
      saveSoon();
    } catch {
      setStatus('Não foi possível abrir essa imagem');
    }
  });

  $('#image-remove').addEventListener('click', () => {
    slides()[current].image = null;
    fillSlideForm();
    render();
    saveSoon();
  });

  const move = (dir) => {
    const to = current + dir;
    if (to < 0 || to >= slides().length) return;
    const [s] = slides().splice(current, 1);
    slides().splice(to, 0, s);
    structureChanged(to);
  };
  $('#move-left').addEventListener('click', () => move(-1));
  $('#move-right').addEventListener('click', () => move(1));

  $('#duplicate').addEventListener('click', () => {
    const copy = { ...slides()[current], id: newId('s') };
    slides().splice(current + 1, 0, copy);
    structureChanged(current + 1);
  });

  $('#delete').addEventListener('click', () => {
    if (slides().length === 1) return;
    if (!confirm('Excluir este slide?')) return;
    slides().splice(current, 1);
    structureChanged(Math.min(current, slides().length - 1));
  });

  $('#prev').addEventListener('click', () => select(current - 1));
  $('#next').addEventListener('click', () => select(current + 1));
}

// ---------- Aba "Marca" ----------

function brandChanged() {
  fillBrandPanel();
  fillCarouselPanel();
  render();
  saveSoon();
}

function useBrand(b) {
  carousel().brandId = b.id;
  brandChanged();
}

function buildBrandPanel() {
  $('#brand-select').addEventListener('change', (e) => {
    useBrand(state.brands.find((b) => b.id === e.target.value));
  });

  $('#brand-new').addEventListener('click', () => {
    const name = prompt('Nome da nova marca:', '');
    if (name === null) return;
    const b = newBrand({ name: name.trim() || 'Nova marca' });
    state.brands.push(b);
    useBrand(b);
  });

  $('#brand-duplicate').addEventListener('click', () => {
    const b = { ...brand(), colors: { ...brand().colors }, id: newId('m'), name: `${brand().name} (cópia)` };
    state.brands.push(b);
    useBrand(b);
  });

  $('#brand-delete').addEventListener('click', () => {
    if (state.brands.length === 1) return;
    const b = brand();
    const users = state.carousels.filter((c) => c.brandId === b.id).length;
    const note = users > 1 ? `\n${users} carrosséis usam esta marca e vão passar para outra.` : '';
    if (!confirm(`Excluir a marca “${b.name}”?${note}`)) return;
    state.brands = state.brands.filter((x) => x !== b);
    state.carousels.forEach((c) => { if (c.brandId === b.id) c.brandId = state.brands[0].id; });
    brandChanged();
  });

  $('#brand-name').addEventListener('input', (e) => {
    brand().name = e.target.value;
    $$('#brand-select option').find((o) => o.value === brand().id).textContent = e.target.value || 'Sem nome';
    fillCarouselPanel();
    render();
    saveSoon();
  });

  // Estilos: aplicam também a paleta e as fontes sugeridas.
  const styles = $('#styles');
  STYLES.forEach((s) => {
    const b = document.createElement('button');
    b.className = 'style-option';
    b.dataset.style = s.id;
    b.innerHTML = `<strong>${s.name}</strong><span>${s.description}</span>`;
    b.addEventListener('click', () => {
      const palette = PALETTES.find((p) => p.id === s.defaults.paletteId) || PALETTES[0];
      Object.assign(brand(), {
        styleId: s.id,
        paletteId: palette.id,
        colors: { ...palette.colors },
        titleFontId: s.defaults.titleFontId,
        bodyFontId: s.defaults.bodyFontId,
      });
      brandChanged();
    });
    styles.append(b);
  });

  const box = $('#palettes');
  PALETTES.forEach((p) => {
    const b = document.createElement('button');
    b.className = 'palette';
    b.dataset.palette = p.id;
    const chips = ['bg', 'text', 'accent', 'muted'].map((k) => `<span style="background:${p.colors[k]}"></span>`).join('');
    b.innerHTML = `<span class="palette-chips">${chips}</span>${p.name}`;
    b.addEventListener('click', () => {
      brand().paletteId = p.id;
      brand().colors = { ...p.colors };
      brandChanged();
    });
    box.append(b);
  });

  $$('[data-color]').forEach((el) => {
    el.addEventListener('input', () => {
      brand().colors[el.dataset.color] = el.value;
      brand().paletteId = 'custom';
      $$('.palette').forEach((b) => b.classList.remove('is-active'));
      render();
      saveSoon();
    });
  });

  const fillSelect = (sel, list) => list.forEach((f) => sel.append(new Option(f.name, f.id)));
  fillSelect($('#title-font'), TITLE_FONTS);
  fillSelect($('#body-font'), BODY_FONTS);
  $('#title-font').addEventListener('change', (e) => { brand().titleFontId = e.target.value; render(); saveSoon(); });
  $('#body-font').addEventListener('change', (e) => { brand().bodyFontId = e.target.value; render(); saveSoon(); });

  $('#handle').addEventListener('input', (e) => { brand().handle = e.target.value; render(); saveSoon(); });
  $('#show-numbers').addEventListener('change', (e) => { brand().showNumbers = e.target.checked; render(); saveSoon(); });

  $('#logo-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    try {
      brand().logo = await storage.putImage(await fileToBlob(file, { maxSide: 800, type: 'image/png' }));
      brandChanged();
    } catch {
      setStatus('Não foi possível abrir esse logo');
    }
  });

  $('#logo-remove').addEventListener('click', () => {
    brand().logo = null;
    brandChanged();
  });
}

function fillBrandPanel() {
  const b = brand();
  const select = $('#brand-select');
  select.innerHTML = '';
  state.brands.forEach((x) => select.append(new Option(x.name || 'Sem nome', x.id)));
  select.value = b.id;
  $('#brand-delete').disabled = state.brands.length === 1;
  $('#brand-name').value = b.name;
  $$('.style-option').forEach((el) => el.classList.toggle('is-active', el.dataset.style === b.styleId));
  $$('.palette').forEach((el) => el.classList.toggle('is-active', el.dataset.palette === b.paletteId));
  $$('[data-color]').forEach((el) => { el.value = b.colors[el.dataset.color]; });
  $('#title-font').value = b.titleFontId;
  $('#body-font').value = b.bodyFontId;
  $('#handle').value = b.handle;
  $('#show-numbers').checked = b.showNumbers;
  $('#logo-remove').hidden = !b.logo;
  $('#logo-btn-label').textContent = b.logo ? 'Trocar logo' : 'Escolher logo';
}

// Marcas prontas guardadas no repositório (marcas/catalogo.json).
// Se o arquivo não existir ou estiver vazio, a seção fica escondida.
async function loadCatalog() {
  let list;
  try {
    const res = await fetch('marcas/catalogo.json', { cache: 'no-store' });
    list = res.ok ? await res.json() : [];
  } catch {
    list = [];
  }
  if (!Array.isArray(list) || !list.length) return;
  const box = $('#catalog-list');
  list.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'catalog-item';
    const chips = ['bg', 'text', 'accent', 'muted'].map((k) => `<span style="background:${item.colors?.[k] || '#ccc'}"></span>`).join('');
    row.innerHTML = `<span class="palette-chips">${chips}</span>`;
    const name = document.createElement('span');
    name.textContent = item.name || 'Marca';
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = 'Adicionar';
    btn.addEventListener('click', () => {
      const { logo, id, ...fields } = item;   // o logo é escolhido no aparelho
      const b = newBrand(fields);
      b.colors = { ...newBrand({ styleId: b.styleId }).colors, ...item.colors };
      if (!item.paletteId) b.paletteId = 'custom';
      state.brands.push(b);
      useBrand(b);
      setStatus(`Marca “${b.name}” adicionada`);
    });
    row.append(name, btn);
    box.append(row);
  });
  $('#catalog').hidden = false;
}

// ---------- Aba "Carrosséis" ----------

function openCarousel(c) {
  state.currentCarouselId = c.id;
  current = 0;
  refreshAll();
  saveSoon();
}

function fillCarouselPanel() {
  $('#carousel-name').value = carousel().name;
  const list = $('#carousel-list');
  list.innerHTML = '';
  [...state.carousels]
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))
    .forEach((c) => {
      const btn = document.createElement('button');
      btn.className = 'carousel-item' + (c.id === carousel().id ? ' is-active' : '');
      const name = document.createElement('strong');
      name.textContent = c.name || 'Sem nome';
      const info = document.createElement('span');
      info.textContent = `${brandOf(c).name} · ${c.slides.length} slides`;
      btn.append(name, info);
      btn.addEventListener('click', () => openCarousel(c));
      list.append(btn);
    });
}

let listTimer;
function bindCarouselPanel() {
  $('#carousel-name').addEventListener('input', (e) => {
    carousel().name = e.target.value;
    render();
    saveSoon();
    clearTimeout(listTimer);
    listTimer = setTimeout(fillCarouselPanel, 600);   // atualiza a lista depois de digitar
  });

  $('#carousel-new').addEventListener('click', () => {
    const c = newCarousel({ brandId: brand().id });
    state.carousels.push(c);
    openCarousel(c);
  });

  $('#carousel-duplicate').addEventListener('click', () => {
    const src = carousel();
    const c = newCarousel({
      name: `${src.name} (cópia)`,
      brandId: src.brandId,
      slides: src.slides.map((s) => ({ ...s, id: newId('s') })),
    });
    state.carousels.push(c);
    openCarousel(c);
  });

  $('#carousel-delete').addEventListener('click', () => {
    if (!confirm(`Excluir o carrossel “${carousel().name}”?`)) return;
    state.carousels = state.carousels.filter((c) => c !== carousel());
    if (!state.carousels.length) state.carousels.push(newCarousel({ brandId: state.brands[0].id }));
    openCarousel(state.carousels[0]);
  });

  $('#script-create').addEventListener('click', () => {
    const parsed = parseScript($('#script-input').value);
    if (!parsed.length) {
      alert('Não encontrei slides no roteiro. Comece cada slide com # e o layout, por exemplo:\n\n# capa\nTítulo: Meu título');
      return;
    }
    const firstTitle = parsed[0].title.replace(/\*/g, '').split('\n')[0].trim();
    const c = newCarousel({
      name: firstTitle.slice(0, 60) || 'Carrossel do roteiro',
      brandId: brand().id,
      slides: parsed.map((s) => newSlide(s)),
    });
    state.carousels.push(c);
    $('#script-input').value = '';
    openCarousel(c);
    setStatus(`Carrossel criado com ${c.slides.length} slides`);
  });

  $('#backup-export').addEventListener('click', exportBackup);
  $('#backup-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (file) await importBackup(file);
  });
}

// ---------- Cópia de segurança ----------

function blobToDataURL(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

function downloadFile(file) {
  const url = URL.createObjectURL(file);
  const a = document.createElement('a');
  a.href = url;
  a.download = file.name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

async function exportBackup() {
  setStatus('Preparando cópia…');
  const images = {};
  for (const id of usedImageIds()) {
    const blob = await storage.getImageBlob(id);
    if (blob) images[id] = await blobToDataURL(blob);
  }
  const data = {
    app: 'estudio-de-carrosseis',
    version: 2,
    savedAt: new Date().toISOString(),
    brands: state.brands,
    carousels: state.carousels,
    images,
  };
  const day = new Date().toISOString().slice(0, 10);
  downloadFile(new File([JSON.stringify(data)], `carrosseis-copia-${day}.json`, { type: 'application/json' }));
  setStatus('Cópia salva');
}

// Junta a cópia com o que já existe: itens com o mesmo código
// são substituídos pela versão da cópia; os outros são somados.
// Num aparelho que ainda não foi usado, a cópia toma o lugar
// do exemplo.
async function importBackup(file) {
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch {
    alert('Esse arquivo não é uma cópia de segurança válida.');
    return;
  }
  if (!Array.isArray(data.brands) || !Array.isArray(data.carousels)) {
    alert('Esse arquivo não é uma cópia de segurança do Estúdio de Carrosséis.');
    return;
  }
  if (!confirm(`Restaurar ${data.brands.length} marca(s) e ${data.carousels.length} carrossel(éis)?\nItens iguais aos atuais serão substituídos.`)) return;
  setStatus('Restaurando…');
  for (const [id, url] of Object.entries(data.images || {})) {
    try { await storage.putImage(await dataURLToBlob(url), id); } catch { /* imagem ignorada */ }
  }
  const merge = (mine, theirs) => {
    const byId = new Map(state.pristine ? [] : mine.map((x) => [x.id, x]));
    theirs.forEach((x) => byId.set(x.id, x));
    return [...byId.values()];
  };
  const next = repairState({
    ...state,
    brands: merge(state.brands, data.brands),
    carousels: merge(state.carousels, data.carousels.filter((c) => Array.isArray(c.slides) && c.slides.length)),
  });
  if (!isValidState(next)) {
    alert('Não foi possível restaurar essa cópia.');
    return;
  }
  state = next;
  delete state.pristine;
  imageCache.clear();
  current = 0;
  refreshAll();
  saveNow();
  setStatus('Cópia restaurada');
}

// ---------- Abas ----------

function bindTabs() {
  $$('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      $$('.tab').forEach((t) => {
        const active = t === tab;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', active);
        $(`#tab-${t.dataset.tab}`).hidden = !active;
      });
    });
  });
}

// ---------- Exportação ----------

let exported = []; // { file, url }

function canvasToBlob(canvas) {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}

// "Meu Carrossel: 5 dicas!" → "meu-carrossel-5-dicas"
function slug(text) {
  return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'carrossel';
}

async function exportSlides(indices) {
  const buttons = [$('#export-one'), $('#export-all')];
  buttons.forEach((b) => { b.disabled = true; });
  setStatus('Gerando imagens…');
  try {
    const t = await theme();
    await loadFonts(t);
    clearExported();
    const base = slug(carousel().name);
    for (const i of indices) {
      const canvas = document.createElement('canvas');
      canvas.width = SLIDE_W;
      canvas.height = SLIDE_H;
      await drawSlide(canvas, i, 1, false, t);
      const blob = await canvasToBlob(canvas);
      const name = `${base}-${String(i + 1).padStart(2, '0')}.png`;
      const file = new File([blob], name, { type: 'image/png' });
      exported.push({ file, url: URL.createObjectURL(blob) });
      canvas.width = canvas.height = 0; // libera memória (importante no iPad)
    }
    openExportDialog();
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
}

function clearExported() {
  exported.forEach((e) => URL.revokeObjectURL(e.url));
  exported = [];
}

function canShareFiles() {
  const files = exported.map((e) => e.file);
  return !!(navigator.canShare && navigator.canShare({ files }));
}

function openExportDialog() {
  const n = exported.length;
  const grid = $('#export-grid');
  grid.innerHTML = '';
  exported.forEach(({ file, url }) => {
    const a = document.createElement('a');
    a.className = 'export-item';
    a.href = url;
    a.download = file.name;
    a.innerHTML = `<img src="${url}" alt=""><span>${file.name}</span>`;
    grid.append(a);
  });
  const share = canShareFiles();
  $('#share-files').hidden = !share;
  $('#dialog-note').textContent = share
    ? `${n} ${n === 1 ? 'imagem' : 'imagens'} em 1080 × 1350 px. Toque em “Salvar no iPad” e escolha “Salvar ${n === 1 ? 'Imagem' : `${n} Imagens`}” para enviar ao app Fotos. Para retocar no Canva, envie as imagens pelo app do Canva (Uploads).`
    : `${n} ${n === 1 ? 'imagem' : 'imagens'} em 1080 × 1350 px. Toque numa imagem para baixá-la.`;
  $('#export-dialog').showModal();
}

function bindExport() {
  $('#export-one').addEventListener('click', () => exportSlides([current]));
  $('#export-all').addEventListener('click', () => exportSlides(slides().map((_, i) => i)));

  // O compartilhamento precisa partir de um toque, por isso ele
  // acontece neste botão (com as imagens já prontas).
  $('#share-files').addEventListener('click', async () => {
    try {
      await navigator.share({ files: exported.map((e) => e.file) });
    } catch (err) {
      if (err.name !== 'AbortError') setStatus('Compartilhamento indisponível — use “Baixar arquivos”');
    }
  });

  $('#download-all').addEventListener('click', async () => {
    for (const { file, url } of exported) {
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.append(a);
      a.click();
      a.remove();
      await new Promise((r) => setTimeout(r, 400)); // pausa entre downloads
    }
  });

  $('#dialog-close').addEventListener('click', () => $('#export-dialog').close());
  $('#export-dialog').addEventListener('close', clearExported);
}

// ---------- Início ----------

async function start() {
  state = await loadInitialState();
  storage.requestPersistence();
  storage.removeUnusedImages(usedImageIds());

  buildLayoutPicker();
  buildBrandPanel();
  bindSlideForm();
  bindCarouselPanel();
  bindTabs();
  bindExport();
  refreshAll();
  select(0);
  loadCatalog();

  // Redesenha quando as fontes do Google terminarem de chegar.
  document.fonts.ready.then(render);
}

start();
