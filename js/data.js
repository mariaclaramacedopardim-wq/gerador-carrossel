// ============================================================
// data.js — estilos, paletas, fontes, layouts, marcas e o
// carrossel de exemplo.
// Para adicionar uma paleta ou fonte, basta incluir um item
// nas listas abaixo (fontes também precisam estar no <link>
// do Google Fonts em index.html).
// ============================================================

// Paletas: bg = fundo, text = texto principal,
// muted = texto secundário, accent = cor de destaque.
export const PALETTES = [
  { id: 'marfim',  name: 'Marfim',     colors: { bg: '#F4EFE6', text: '#1B1A17', muted: '#6B655B', accent: '#B4532A' } },
  { id: 'noite',   name: 'Noite',      colors: { bg: '#14161B', text: '#F2EEE6', muted: '#9A968D', accent: '#D9B26F' } },
  { id: 'oliva',   name: 'Oliva',      colors: { bg: '#E7E4D3', text: '#2D3320', muted: '#6E7259', accent: '#8A3B12' } },
  { id: 'rosa',    name: 'Rosa seco',  colors: { bg: '#F2E3DD', text: '#3A1F1D', muted: '#8C6A64', accent: '#A33B3B' } },
  { id: 'tinta',   name: 'Azul tinta', colors: { bg: '#0F2A44', text: '#F3EDE2', muted: '#A9B4C0', accent: '#E7B04B' } },
  { id: 'papel',   name: 'Papel',      colors: { bg: '#FFFFFF', text: '#111111', muted: '#6F6F6F', accent: '#2443D6' } },
  { id: 'neon',    name: 'Neon',       colors: { bg: '#121212', text: '#FFFFFF', muted: '#A3A3A3', accent: '#D7FF3A' } },
  { id: 'pessego', name: 'Pêssego',    colors: { bg: '#FFF4EC', text: '#2B2240', muted: '#7A6F86', accent: '#FF7A59' } },
  { id: 'menta',   name: 'Menta',      colors: { bg: '#E8F3EE', text: '#173B32', muted: '#5E7A71', accent: '#2E9E78' } },
];

// Fontes de título: weight é o peso usado nos títulos.
export const TITLE_FONTS = [
  { id: 'playfair',   name: 'Playfair Display',   family: 'Playfair Display',   weight: 600 },
  { id: 'fraunces',   name: 'Fraunces',           family: 'Fraunces',           weight: 500 },
  { id: 'cormorant',  name: 'Cormorant Garamond', family: 'Cormorant Garamond', weight: 600 },
  { id: 'dmserif',    name: 'DM Serif Display',   family: 'DM Serif Display',   weight: 400 },
  { id: 'instrument', name: 'Instrument Serif',   family: 'Instrument Serif',   weight: 400 },
  { id: 'inter',      name: 'Inter (sem serifa)', family: 'Inter',              weight: 800 },
  { id: 'grotesk',    name: 'Space Grotesk',      family: 'Space Grotesk',      weight: 700 },
  { id: 'anton',      name: 'Anton (condensada)', family: 'Anton',              weight: 400 },
  { id: 'bricolage',  name: 'Bricolage Grotesque', family: 'Bricolage Grotesque', weight: 700 },
  { id: 'poppins',    name: 'Poppins',            family: 'Poppins',            weight: 700 },
  { id: 'nunito',     name: 'Nunito (arredondada)', family: 'Nunito',           weight: 800 },
];

// Fontes de texto corrido.
export const BODY_FONTS = [
  { id: 'inter',   name: 'Inter',          family: 'Inter' },
  { id: 'dmsans',  name: 'DM Sans',        family: 'DM Sans' },
  { id: 'source',  name: 'Source Serif 4', family: 'Source Serif 4' },
  { id: 'lora',    name: 'Lora',           family: 'Lora' },
  { id: 'grotesk', name: 'Space Grotesk',  family: 'Space Grotesk' },
  { id: 'poppins', name: 'Poppins',        family: 'Poppins' },
  { id: 'nunito',  name: 'Nunito',         family: 'Nunito' },
];

// Estilos: o "jeito" dos slides. Cada estilo muda como os
// destaques (*palavras*) aparecem e alguns detalhes do desenho,
// e sugere uma paleta e fontes (defaults) para começar.
//   emphasis: italic    → itálico na cor de destaque
//             color     → só a cor de destaque
//             marker    → caixa colorida atrás da palavra
//             highlight → traço de marca-texto
//   upperTitles: títulos em CAIXA-ALTA
//   rules: filetes (linhas curtas) na cor de destaque
//   kicker: tracked = chamada em letras espaçadas; pill = etiqueta
export const STYLES = [
  {
    id: 'editorial', name: 'Editorial', description: 'Serifas e itálicos, cara de revista.',
    emphasis: 'italic', upperTitles: false, rules: true, kicker: 'tracked',
    defaults: { paletteId: 'marfim', titleFontId: 'playfair', bodyFontId: 'inter' },
  },
  {
    id: 'minimalista', name: 'Minimalista', description: 'Limpo, sem enfeites, muito respiro.',
    emphasis: 'color', upperTitles: false, rules: false, kicker: 'tracked',
    defaults: { paletteId: 'papel', titleFontId: 'inter', bodyFontId: 'inter' },
  },
  {
    id: 'impacto', name: 'Impacto', description: 'Caixa-alta e destaques fortes.',
    emphasis: 'marker', upperTitles: true, rules: true, kicker: 'pill',
    defaults: { paletteId: 'neon', titleFontId: 'anton', bodyFontId: 'inter' },
  },
  {
    id: 'leve', name: 'Leve', description: 'Amigável, com marca-texto.',
    emphasis: 'highlight', upperTitles: false, rules: false, kicker: 'pill',
    defaults: { paletteId: 'pessego', titleFontId: 'poppins', bodyFontId: 'nunito' },
  },
];

export function findStyle(id) {
  return STYLES.find((s) => s.id === id) || STYLES[0];
}

// Layouts disponíveis. "image" indica se o layout usa foto.
// Os nomes dos campos mudam conforme o layout (ex.: na citação,
// o "título" é a frase e o "texto" é o autor).
export const LAYOUTS = [
  { id: 'capa',     name: 'Capa',     image: true,  labels: { kicker: 'Chamada', title: 'Título', body: 'Subtítulo' } },
  { id: 'conteudo', name: 'Texto',    image: false, labels: { kicker: 'Chamada / número', title: 'Título', body: 'Texto' } },
  { id: 'citacao',  name: 'Citação',  image: false, labels: { kicker: 'Chamada', title: 'Citação', body: 'Autor' } },
  { id: 'imagem',   name: 'Imagem',   image: true,  labels: { kicker: 'Chamada', title: 'Título', body: 'Texto' } },
  { id: 'final',    name: 'Final',    image: false, labels: { kicker: 'Chamada', title: 'Título', body: 'Texto' } },
];

let nextId = 1;
export function newId(prefix) {
  return `${prefix}${Date.now().toString(36)}${nextId++}`;
}

export function newSlide(fields = {}) {
  return {
    id: newId('s'),
    layout: 'conteudo',
    kicker: '',
    title: 'Novo slide',
    body: '',
    image: null,     // código da foto guardada no aparelho (ver storage.js)
    imagePos: 50,    // enquadramento vertical da foto: 0 = topo, 100 = base
    overlay: 60,     // escurecimento sobre a foto na capa (0–100)
    ...fields,
  };
}

// Uma marca guarda a identidade visual: estilo, cores, fontes,
// @ e logo. Ao criar, usa as sugestões do estilo escolhido.
export function newBrand(fields = {}) {
  const style = findStyle(fields.styleId);
  const palette = PALETTES.find((p) => p.id === style.defaults.paletteId) || PALETTES[0];
  return {
    id: newId('m'),
    name: 'Minha marca',
    styleId: style.id,
    paletteId: palette.id,
    colors: { ...palette.colors },
    titleFontId: style.defaults.titleFontId,
    bodyFontId: style.defaults.bodyFontId,
    handle: '@seuperfil',
    logo: null,      // código do logo guardado no aparelho
    showNumbers: true,
    ...fields,
  };
}

export function newCarousel(fields = {}) {
  return {
    id: newId('c'),
    name: 'Novo carrossel',
    brandId: null,
    updatedAt: Date.now(),
    slides: [
      newSlide({ layout: 'capa', kicker: 'Chamada', title: 'Título da *capa*', body: 'Um subtítulo curto.' }),
      newSlide({ layout: 'conteudo', kicker: '01', title: 'Primeira ideia', body: 'Explique a ideia em poucas linhas.' }),
      newSlide({ layout: 'final', kicker: 'Gostou?', title: 'Salve para *consultar* depois', body: '' }),
    ],
    ...fields,
  };
}

export function exampleSlides() {
  return [
    newSlide({ layout: 'capa', kicker: 'Guia rápido', title: 'Design *editorial* para carrosséis', body: 'Cinco princípios para posts que parecem página de revista.' }),
    newSlide({ layout: 'conteudo', kicker: '01', title: 'Hierarquia é tudo', body: 'Um título forte, um apoio curto e muito espaço em branco.\nO olho precisa saber por onde começar.' }),
    newSlide({ layout: 'conteudo', kicker: '02', title: 'Poucas fontes, *bem escolhidas*', body: 'Uma serifa expressiva para os títulos e uma fonte discreta para o texto. Duas famílias bastam.' }),
    newSlide({ layout: 'citacao', kicker: '', title: 'A tipografia é o que a linguagem parece.', body: 'Ellen Lupton' }),
    newSlide({ layout: 'imagem', kicker: '03', title: 'Imagens com respiro', body: 'Deixe a foto ocupar espaço e o texto descansar logo abaixo.' }),
    newSlide({ layout: 'final', kicker: 'Gostou?', title: 'Salve para *consultar* depois', body: 'E compartilhe com quem também cria conteúdo.' }),
  ];
}

// Estado inicial: uma marca e um carrossel de exemplo.
// pristine = ainda não foi mexido (some na primeira alteração).
export function createDefaultState() {
  const brand = newBrand({ name: 'Minha marca' });
  const carousel = newCarousel({ name: 'Exemplo', brandId: brand.id, slides: exampleSlides() });
  return { version: 2, brands: [brand], carousels: [carousel], currentCarouselId: carousel.id, pristine: true };
}
