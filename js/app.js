// ============================================================
// app.js — liga a interface ao desenho dos slides.
// Guarda o projeto, responde aos campos do painel, desenha a
// pré-visualização e exporta os PNGs.
// ============================================================

import { PALETTES, TITLE_FONTS, BODY_FONTS, LAYOUTS, newSlide, createDefaultProject } from './data.js';
import { SLIDE_W, SLIDE_H, renderSlide, loadFonts } from './render.js';

const STORAGE_KEY = 'carrossel-editorial:v1';
const THUMB_SCALE = 0.2;   // miniaturas em 216 × 270

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

let project = loadProject() || createDefaultProject();
let current = 0;

// ---------- Salvar no navegador ----------

function loadProject() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return saved && Array.isArray(saved.slides) && saved.slides.length ? saved : null;
  } catch {
    return null;
  }
}

let saveTimer;
function saveSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 400);
}

function saveNow() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(project));
    setStatus('Salvo neste aparelho');
  } catch {
    // O navegador tem pouco espaço; fotos grandes podem não caber.
    // Nesse caso salvamos ao menos os textos e o estilo.
    try {
      const light = { ...project, slides: project.slides.map((s) => ({ ...s, image: null })) };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(light));
      setStatus('Textos salvos (fotos não couberam na memória)');
    } catch {
      setStatus('Não foi possível salvar');
    }
  }
}

let statusTimer;
function setStatus(text) {
  $('#status').textContent = text;
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => { $('#status').textContent = ''; }, 2500);
}

// ---------- Tema e imagens ----------

function theme() {
  return {
    colors: project.colors,
    titleFont: TITLE_FONTS.find((f) => f.id === project.titleFontId) || TITLE_FONTS[0],
    bodyFont: BODY_FONTS.find((f) => f.id === project.bodyFontId) || BODY_FONTS[0],
    handle: project.handle.trim(),
    showNumbers: project.showNumbers,
  };
}

// Fotos são guardadas como texto (dataURL). Aqui transformamos
// esse texto em imagem uma única vez e reaproveitamos.
const imageCache = new Map();

function getImage(src) {
  if (!src) return Promise.resolve(null);
  if (!imageCache.has(src)) {
    imageCache.set(src, new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = src;
    }));
  }
  return imageCache.get(src);
}

// Reduz fotos muito grandes (fotos do iPad têm 12+ megapixels)
// para no máximo 2000 px — mais leve e ainda nítido em 1080 px.
async function fileToDataURL(file, maxSide = 2000) {
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
    return canvas.toDataURL('image/jpeg', 0.88);
  } finally {
    URL.revokeObjectURL(url);
  }
}

// ---------- Desenho ----------

async function drawSlide(canvas, index, scale, preview) {
  const slide = project.slides[index];
  const image = await getImage(slide.image);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  renderSlide(ctx, { slide, index, total: project.slides.length, theme: theme(), image, preview });
}

// Junta várias mudanças seguidas (ex.: digitação) num só desenho.
let renderQueued = false;
function render() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(async () => {
    renderQueued = false;
    await loadFonts(theme());
    await drawSlide($('#preview-canvas'), current, 1, true);
    const thumbs = $$('#strip .thumb canvas');
    await Promise.all(thumbs.map((c, i) => drawSlide(c, i, THUMB_SCALE, true)));
    $('#preview-meta').textContent = `Slide ${current + 1} de ${project.slides.length} · 1080 × 1350 px`;
    $('#prev').disabled = current === 0;
    $('#next').disabled = current === project.slides.length - 1;
  });
}

// ---------- Faixa de miniaturas ----------

function buildStrip() {
  const strip = $('#strip');
  strip.innerHTML = '';
  project.slides.forEach((_, i) => {
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
  current = Math.max(0, Math.min(project.slides.length - 1, i));
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
  const layout = project.slides[current]?.layout === 'capa' ? 'conteudo' : project.slides[current]?.layout || 'conteudo';
  project.slides.splice(current + 1, 0, newSlide({ layout }));
  structureChanged(current + 1);
}

// ---------- Aba "Slide" ----------

function buildLayoutPicker() {
  const box = $('#layout-picker');
  LAYOUTS.forEach((l) => {
    const b = document.createElement('button');
    b.textContent = l.name;
    b.dataset.layout = l.id;
    b.addEventListener('click', () => {
      project.slides[current].layout = l.id;
      fillSlideForm();
      render();
      saveSoon();
    });
    box.append(b);
  });
}

function fillSlideForm() {
  const s = project.slides[current];
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
  $('#move-right').disabled = current === project.slides.length - 1;
  $('#delete').disabled = project.slides.length === 1;
}

function bindSlideForm() {
  $$('[data-field]').forEach((el) => {
    el.addEventListener('input', () => {
      const v = el.hasAttribute('data-number') ? Number(el.value) : el.value;
      project.slides[current][el.dataset.field] = v;
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
      project.slides[current].image = await fileToDataURL(file);
      fillSlideForm();
      render();
      saveSoon();
    } catch {
      setStatus('Não foi possível abrir essa imagem');
    }
  });

  $('#image-remove').addEventListener('click', () => {
    project.slides[current].image = null;
    fillSlideForm();
    render();
    saveSoon();
  });

  const move = (dir) => {
    const to = current + dir;
    if (to < 0 || to >= project.slides.length) return;
    const [s] = project.slides.splice(current, 1);
    project.slides.splice(to, 0, s);
    structureChanged(to);
  };
  $('#move-left').addEventListener('click', () => move(-1));
  $('#move-right').addEventListener('click', () => move(1));

  $('#duplicate').addEventListener('click', () => {
    const copy = { ...project.slides[current], id: newSlide().id };
    project.slides.splice(current + 1, 0, copy);
    structureChanged(current + 1);
  });

  $('#delete').addEventListener('click', () => {
    if (project.slides.length === 1) return;
    if (!confirm('Excluir este slide?')) return;
    project.slides.splice(current, 1);
    structureChanged(Math.min(current, project.slides.length - 1));
  });

  $('#prev').addEventListener('click', () => select(current - 1));
  $('#next').addEventListener('click', () => select(current + 1));
}

// ---------- Aba "Estilo" ----------

function buildStylePanel() {
  const box = $('#palettes');
  PALETTES.forEach((p) => {
    const b = document.createElement('button');
    b.className = 'palette';
    b.dataset.palette = p.id;
    const chips = ['bg', 'text', 'accent', 'muted'].map((k) => `<span style="background:${p.colors[k]}"></span>`).join('');
    b.innerHTML = `<span class="palette-chips">${chips}</span>${p.name}`;
    b.addEventListener('click', () => {
      project.paletteId = p.id;
      project.colors = { ...p.colors };
      fillStylePanel();
      render();
      saveSoon();
    });
    box.append(b);
  });

  $$('[data-color]').forEach((el) => {
    el.addEventListener('input', () => {
      project.colors[el.dataset.color] = el.value;
      project.paletteId = 'custom';
      $$('.palette').forEach((b) => b.classList.remove('is-active'));
      render();
      saveSoon();
    });
  });

  const fillSelect = (sel, list) => list.forEach((f) => sel.append(new Option(f.name, f.id)));
  fillSelect($('#title-font'), TITLE_FONTS);
  fillSelect($('#body-font'), BODY_FONTS);
  $('#title-font').addEventListener('change', (e) => { project.titleFontId = e.target.value; render(); saveSoon(); });
  $('#body-font').addEventListener('change', (e) => { project.bodyFontId = e.target.value; render(); saveSoon(); });

  $('#handle').addEventListener('input', (e) => { project.handle = e.target.value; render(); saveSoon(); });
  $('#show-numbers').addEventListener('change', (e) => { project.showNumbers = e.target.checked; render(); saveSoon(); });

  $('#reset').addEventListener('click', () => {
    if (!confirm('Apagar o carrossel atual e voltar ao exemplo?')) return;
    project = createDefaultProject();
    fillStylePanel();
    structureChanged(0);
  });
}

function fillStylePanel() {
  $$('.palette').forEach((b) => b.classList.toggle('is-active', b.dataset.palette === project.paletteId));
  $$('[data-color]').forEach((el) => { el.value = project.colors[el.dataset.color]; });
  $('#title-font').value = project.titleFontId;
  $('#body-font').value = project.bodyFontId;
  $('#handle').value = project.handle;
  $('#show-numbers').checked = project.showNumbers;
}

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

async function exportSlides(indices) {
  const buttons = [$('#export-one'), $('#export-all')];
  buttons.forEach((b) => { b.disabled = true; });
  setStatus('Gerando imagens…');
  try {
    await loadFonts(theme());
    clearExported();
    for (const i of indices) {
      const canvas = document.createElement('canvas');
      canvas.width = SLIDE_W;
      canvas.height = SLIDE_H;
      await drawSlide(canvas, i, 1, false);
      const blob = await canvasToBlob(canvas);
      const name = `carrossel-${String(i + 1).padStart(2, '0')}.png`;
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
    ? `${n} ${n === 1 ? 'imagem' : 'imagens'} em 1080 × 1350 px. Toque em “Salvar no iPad” e escolha “Salvar ${n === 1 ? 'Imagem' : `${n} Imagens`}” para enviar ao app Fotos.`
    : `${n} ${n === 1 ? 'imagem' : 'imagens'} em 1080 × 1350 px. Toque numa imagem para baixá-la.`;
  $('#export-dialog').showModal();
}

function bindExport() {
  $('#export-one').addEventListener('click', () => exportSlides([current]));
  $('#export-all').addEventListener('click', () => exportSlides(project.slides.map((_, i) => i)));

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

buildLayoutPicker();
buildStylePanel();
bindSlideForm();
bindTabs();
bindExport();
fillStylePanel();
buildStrip();
select(0);

// Redesenha quando as fontes do Google terminarem de chegar.
document.fonts.ready.then(render);
