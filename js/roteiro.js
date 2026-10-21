// ============================================================
// roteiro.js — transforma um texto colado em slides.
//
// Formato:
//   # capa
//   Chamada: Guia rápido
//   Título: Seu *título* aqui
//   Texto: Um subtítulo curto
//
//   # texto
//   Chamada: 01
//   Título: Primeira dica
//   Texto: Linhas seguintes sem rótulo
//   continuam o campo anterior.
//
// Cada slide começa com "#" e o layout (capa, texto, citação,
// imagem ou final). Acentos e maiúsculas não importam.
// ============================================================

const LAYOUT_WORDS = {
  capa: 'capa',
  texto: 'conteudo', conteudo: 'conteudo',
  citacao: 'citacao', frase: 'citacao',
  imagem: 'imagem', foto: 'imagem',
  final: 'final', fim: 'final',
};

const FIELD_WORDS = {
  chamada: 'kicker', numero: 'kicker',
  titulo: 'title', citacao: 'title', frase: 'title',
  texto: 'body', subtitulo: 'body', autor: 'body', legenda: 'body',
};

// "Citação" → "citacao"
function plain(text) {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

// Devolve uma lista de slides no formato { layout, kicker, title, body }.
export function parseScript(text) {
  const slides = [];
  let slide = null;
  let field = null;

  const start = (layout) => {
    slide = { layout, kicker: '', title: '', body: '' };
    slides.push(slide);
    field = null;
  };

  for (const raw of String(text || '').split(/\r?\n/)) {
    const line = raw.trimEnd();

    // "# capa", "## Slide 2 — texto", "---"
    const heading = line.match(/^\s*#+\s*(.*)$/);
    if (heading || /^\s*---+\s*$/.test(line)) {
      const words = plain(heading ? heading[1] : '').split(/[^a-z]+/);
      start(LAYOUT_WORDS[words.find((w) => LAYOUT_WORDS[w])] || (slides.length ? 'conteudo' : 'capa'));
      continue;
    }

    // "Título: ..." (só rótulos conhecidos contam)
    const labeled = line.match(/^\s*([^:]{2,20}):\s*(.*)$/);
    const key = labeled && FIELD_WORDS[plain(labeled[1])];
    if (key) {
      if (!slide) start('capa');
      field = key;
      slide[field] = labeled[2].trim();
      continue;
    }

    // Linha sem rótulo: continua o último campo.
    if (!line.trim()) {
      if (slide && field && slide[field]) slide[field] += '\n';
      continue;
    }
    if (!slide) start('capa');
    if (!field) field = slide.title ? 'body' : 'title';
    slide[field] = slide[field] ? `${slide[field]}\n${line.trim()}` : line.trim();
  }

  // Limpa linhas em branco sobrando e descarta slides vazios.
  return slides
    .map((s) => ({
      ...s,
      kicker: s.kicker.trim(),
      title: s.title.trim(),
      body: s.body.replace(/\n{3,}/g, '\n\n').trim(),
    }))
    .filter((s) => s.kicker || s.title || s.body);
}
