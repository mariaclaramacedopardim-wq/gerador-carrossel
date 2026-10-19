// ============================================================
// data.js — opções de estilo e o carrossel de exemplo.
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
];

// Fontes de texto corrido.
export const BODY_FONTS = [
  { id: 'inter',   name: 'Inter',          family: 'Inter' },
  { id: 'dmsans',  name: 'DM Sans',        family: 'DM Sans' },
  { id: 'source',  name: 'Source Serif 4', family: 'Source Serif 4' },
  { id: 'lora',    name: 'Lora',           family: 'Lora' },
  { id: 'grotesk', name: 'Space Grotesk',  family: 'Space Grotesk' },
];

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
export function newSlide(fields = {}) {
  return {
    id: `s${Date.now().toString(36)}${nextId++}`,
    layout: 'conteudo',
    kicker: '',
    title: 'Novo slide',
    body: '',
    image: null,     // foto em formato dataURL (texto)
    imagePos: 50,    // enquadramento vertical da foto: 0 = topo, 100 = base
    overlay: 60,     // escurecimento sobre a foto na capa (0–100)
    ...fields,
  };
}

export function createDefaultProject() {
  return {
    paletteId: 'marfim',
    colors: { ...PALETTES[0].colors },
    titleFontId: 'playfair',
    bodyFontId: 'inter',
    handle: '@seuperfil',
    showNumbers: true,
    slides: [
      newSlide({ layout: 'capa', kicker: 'Guia rápido', title: 'Design *editorial* para carrosséis', body: 'Cinco princípios para posts que parecem página de revista.' }),
      newSlide({ layout: 'conteudo', kicker: '01', title: 'Hierarquia é tudo', body: 'Um título forte, um apoio curto e muito espaço em branco.\nO olho precisa saber por onde começar.' }),
      newSlide({ layout: 'conteudo', kicker: '02', title: 'Poucas fontes, *bem escolhidas*', body: 'Uma serifa expressiva para os títulos e uma fonte discreta para o texto. Duas famílias bastam.' }),
      newSlide({ layout: 'citacao', kicker: '', title: 'A tipografia é o que a linguagem parece.', body: 'Ellen Lupton' }),
      newSlide({ layout: 'imagem', kicker: '03', title: 'Imagens com respiro', body: 'Deixe a foto ocupar espaço e o texto descansar logo abaixo.' }),
      newSlide({ layout: 'final', kicker: 'Gostou?', title: 'Salve para *consultar* depois', body: 'E compartilhe com quem também cria conteúdo.' }),
    ],
  };
}
