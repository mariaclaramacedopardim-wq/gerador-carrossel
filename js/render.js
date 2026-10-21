// ============================================================
// render.js — desenha um slide num <canvas> de 1080 × 1350.
// A mesma função é usada na pré-visualização e na exportação,
// então o PNG sai exatamente igual ao que aparece na tela.
// ============================================================

export const SLIDE_W = 1080;
export const SLIDE_H = 1350;

const M = 96;                         // margem externa
const FOOTER_SIZE = 24;               // tamanho do texto do rodapé
const FOOTER_Y = SLIDE_H - M - FOOTER_SIZE;
const BOTTOM = FOOTER_Y - 64;         // limite inferior do conteúdo
const CONTENT_W = SLIDE_W - 2 * M;

const LIGHT = '#F7F3EC';              // texto claro sobre fotos

// Garante que as fontes escolhidas terminaram de carregar
// antes de desenhar (senão o canvas usa a fonte padrão).
export function loadFonts(theme) {
  const t = theme.titleFont;
  const b = theme.bodyFont.family;
  const specs = [
    `normal ${t.weight} 100px "${t.family}"`,
    `italic ${t.weight} 100px "${t.family}"`,
    `normal 400 40px "${b}"`,
    `normal 600 40px "${b}"`,
  ];
  return Promise.all(specs.map((s) => document.fonts.load(s).catch(() => [])));
}

// ---------- Cores ----------

function luminance(hex) {
  const n = parseInt(String(hex).replace('#', ''), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
}

function contrast(a, b) {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
}

// Escolhe, entre as opções, a cor que mais aparece sobre o fundo.
// Se nenhuma for legível, usa preto ou branco.
function readableOn(bg, ...options) {
  const best = (list) => list.reduce((a, b) => (contrast(bg, b) > contrast(bg, a) ? b : a));
  const pick = best(options);
  return contrast(bg, pick) >= 3 ? pick : best(['#111111', '#FFFFFF']);
}

// ---------- Texto ----------
// Um "spec" descreve como o texto é desenhado. Trechos entre
// *asteriscos* viram destaque (em = emphasis). O jeito do
// destaque vem do estilo da marca (ver STYLES em data.js).

function titleSpec(theme, color, overrides = {}) {
  const f = theme.titleFont;
  const c = theme.colors;
  const e = theme.style.emphasis;
  return {
    family: f.family, weight: f.weight, style: 'normal', color,
    upper: theme.style.upperTitles,
    emWeight: f.weight,
    emStyle: e === 'italic' ? 'italic' : 'normal',
    emColor: e === 'marker' ? readableOn(c.accent, c.bg, c.text) : e === 'highlight' ? color : c.accent,
    emBg: e === 'marker' ? c.accent : null,          // caixa atrás da palavra
    emMark: e === 'highlight' ? c.accent : null,     // traço de marca-texto
    ...overrides,
  };
}

function bodySpec(theme, color) {
  return {
    family: theme.bodyFont.family, weight: 400, style: 'normal', color,
    emWeight: 600, emStyle: 'normal', emColor: color,
  };
}

function fontString(spec, em, size) {
  const style = em ? spec.emStyle : spec.style;
  const weight = em ? spec.emWeight : spec.weight;
  return `${style} ${weight} ${size}px "${spec.family}", Georgia, serif`;
}

// Transforma o texto em parágrafos → palavras → pedaços.
// Ex.: "Design *editorial*" → [[ [Design], [editorial(em)] ]]
function parse(text) {
  return String(text || '').split('\n').map((paragraph) => {
    const words = [];
    let word = [];
    let buf = '';
    let em = false;
    const flushBuf = () => { if (buf) { word.push({ text: buf, em }); buf = ''; } };
    const flushWord = () => { flushBuf(); if (word.length) { words.push(word); word = []; } };
    for (const ch of paragraph) {
      if (ch === '*') { flushBuf(); em = !em; }
      else if (ch === ' ') flushWord();
      else buf += ch;
    }
    flushWord();
    return words;
  });
}

// Quebra o texto em linhas que cabem em maxWidth.
function layoutText(ctx, text, spec, size, maxWidth, lh) {
  if (spec.upper) text = String(text || '').toUpperCase();
  ctx.font = fontString(spec, false, size);
  const space = ctx.measureText(' ').width;
  const lines = [];
  for (const words of parse(text)) {
    if (!words.length) { lines.push({ gap: true }); continue; }
    let line = { words: [], width: 0 };
    for (const pieces of words) {
      let w = 0;
      for (const p of pieces) {
        ctx.font = fontString(spec, p.em, size);
        p.width = ctx.measureText(p.text).width;
        w += p.width;
      }
      const extra = line.words.length ? space + w : w;
      if (line.words.length && line.width + extra > maxWidth) {
        lines.push(line);
        line = { words: [], width: 0 };
      }
      line.width += line.words.length ? space + w : w;
      line.words.push({ pieces, width: w });
    }
    lines.push(line);
  }
  const height = lines.reduce((h, l) => h + size * lh * (l.gap ? 0.5 : 1), 0);
  return { lines, size, lh, space, height, spec };
}

// Escolhe o maior tamanho de fonte (entre max e min) em que o
// texto cabe na área. É isso que deixa os títulos "auto-ajustáveis".
function fitText(ctx, text, spec, { max, min, maxWidth, maxHeight, lh }) {
  let block;
  for (let size = max; size >= min; size -= 2) {
    block = layoutText(ctx, text, spec, size, maxWidth, lh);
    if (block.height <= maxHeight) return block;
  }
  return block;
}

function drawText(ctx, block, x, y, maxWidth, align = 'left') {
  const { lines, size, lh, space, spec } = block;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  const pad = (size * lh - size) / 2;
  for (const line of lines) {
    if (line.gap) { y += size * lh * 0.5; continue; }
    let cx = align === 'center' ? x + (maxWidth - line.width) / 2 : x;
    line.words.forEach((word, w) => {
      word.pieces.forEach((p, i) => {
        // Fundo do destaque. Se a palavra seguinte também é
        // destaque, o fundo cobre o espaço entre as duas.
        if (p.em && (spec.emBg || spec.emMark)) {
          const next = line.words[w + 1];
          const joins = i === word.pieces.length - 1 && next && next.pieces[0].em;
          const extra = joins ? space : 0;
          const top = y + pad;
          // Mede as letras da fonte: a altura de "H" dá o topo e a
          // base das maiúsculas; acentos (É, Ã) aumentam a caixa.
          ctx.font = fontString(spec, true, size);
          const cap = ctx.measureText('H');
          const capTop = top - cap.actualBoundingBoxAscent;
          const base = top + cap.actualBoundingBoxDescent;
          if (spec.emBg) {
            const glyphTop = top - ctx.measureText(p.text).actualBoundingBoxAscent;
            const boxTop = Math.min(capTop - size * 0.1, glyphTop - size * 0.04);
            const px = size * 0.1;
            ctx.fillStyle = spec.emBg;
            ctx.fillRect(cx - px, boxTop, p.width + extra + 2 * px, base + size * 0.1 - boxTop);
          } else {
            ctx.save();
            ctx.globalAlpha = 0.45;
            ctx.fillStyle = spec.emMark;
            ctx.fillRect(cx - size * 0.04, base - size * 0.28, p.width + extra + size * 0.08, size * 0.36);
            ctx.restore();
          }
        }
        ctx.font = fontString(spec, p.em, size);
        ctx.fillStyle = p.em ? spec.emColor : spec.color;
        ctx.fillText(p.text, cx, y + pad);
        cx += p.width;
      });
      cx += space;
    });
    y += size * lh;
  }
  return y;
}

// Texto com espaçamento entre letras (para chamadas em caixa-alta).
function measureTracked(ctx, text, tracking) {
  const chars = [...text];
  return chars.reduce((w, c) => w + ctx.measureText(c).width, 0) + tracking * (chars.length - 1);
}

function drawTracked(ctx, text, x, y, tracking, align = 'left') {
  const chars = [...text];
  const total = measureTracked(ctx, text, tracking);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  chars.forEach((c) => { ctx.fillText(c, cx, y); cx += ctx.measureText(c).width + tracking; });
  return total;
}

// Chamada: letras espaçadas ou, no estilo "pill", uma etiqueta
// colorida. plain = true força as letras espaçadas (ex.: autor).
function drawKicker(ctx, theme, text, x, y, color, align = 'left', plain = false) {
  if (!text) return;
  const label = text.toUpperCase();
  ctx.font = `600 26px "${theme.bodyFont.family}", sans-serif`;
  if (theme.style.kicker === 'pill' && !plain) {
    const padX = 22;
    const w = measureTracked(ctx, label, 4) + padX * 2;
    const left = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
    roundRectPath(ctx, left, y - 12, w, 50, 25);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.fillStyle = readableOn(color, theme.colors.bg, theme.colors.text);
    drawTracked(ctx, label, left + padX, y, 4);
    return;
  }
  ctx.fillStyle = color;
  drawTracked(ctx, label, x, y, 4, align);
}

// ---------- Imagem ----------

// Preenche a área inteira com a foto, cortando o excesso
// (como "object-fit: cover"). posY escolhe o enquadramento.
function drawCover(ctx, img, x, y, w, h, posY = 0.5) {
  const iw = img.naturalWidth || img.width;
  const ih = img.naturalHeight || img.height;
  const scale = Math.max(w / iw, h / ih);
  const sw = w / scale;
  const sh = h / scale;
  ctx.drawImage(img, (iw - sw) / 2, (ih - sh) * posY, sw, sh, x, y, w, h);
}

function roundRectPath(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// ---------- Rodapé ----------

function drawFooter(ctx, theme, index, total, color) {
  ctx.font = `600 ${FOOTER_SIZE}px "${theme.bodyFont.family}", sans-serif`;
  ctx.fillStyle = color;
  ctx.textBaseline = 'top';
  let left = M;
  if (theme.logo) {
    // logo com até 56 px de altura e 220 px de largura
    const iw = theme.logo.naturalWidth || theme.logo.width;
    const ih = theme.logo.naturalHeight || theme.logo.height;
    const scale = Math.min(56 / ih, 220 / iw);
    const w = iw * scale;
    const h = ih * scale;
    ctx.drawImage(theme.logo, M, FOOTER_Y + FOOTER_SIZE / 2 - h / 2, w, h);
    left += w + 20;
  }
  if (theme.handle) {
    ctx.textAlign = 'left';
    ctx.fillText(theme.handle, left, FOOTER_Y);
  }
  let right = SLIDE_W - M;
  const isLast = index === total - 1;
  if (!isLast) {
    // seta desenhada com linhas (não depende da fonte ter o glifo)
    const cy = FOOTER_Y + FOOTER_SIZE / 2;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(right - 44, cy); ctx.lineTo(right, cy);
    ctx.moveTo(right - 12, cy - 10); ctx.lineTo(right, cy); ctx.lineTo(right - 12, cy + 10);
    ctx.stroke();
    right -= 68;
  }
  if (theme.showNumbers) {
    const pad = (n) => String(n).padStart(2, '0');
    ctx.textAlign = 'right';
    ctx.fillText(`${pad(index + 1)} / ${pad(total)}`, right, FOOTER_Y);
  }
}

// ---------- Layouts ----------
// Cada layout desenha o conteúdo e devolve a cor do rodapé.

const layouts = {
  capa(ctx, s, theme, img) {
    const c = theme.colors;
    let fg = c.text, sub = c.muted, acc = c.accent;
    if (img) {
      drawCover(ctx, img, 0, 0, SLIDE_W, SLIDE_H, s.imagePos / 100);
      const a = s.overlay / 100;
      const g = ctx.createLinearGradient(0, 0, 0, SLIDE_H);
      g.addColorStop(0, `rgba(0,0,0,${a * 0.45})`);
      g.addColorStop(0.35, `rgba(0,0,0,${a * 0.1})`);
      g.addColorStop(1, `rgba(0,0,0,${a})`);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, SLIDE_W, SLIDE_H);
      fg = LIGHT; sub = 'rgba(247,243,236,0.85)'; acc = LIGHT;
    }

    if (theme.style.rules) {
      ctx.fillStyle = acc;
      ctx.fillRect(M, M, 72, 4);
    }
    drawKicker(ctx, theme, s.kicker, M, theme.style.rules ? M + 32 : M + 12, acc);

    const body = s.body
      ? fitText(ctx, s.body, bodySpec(theme, sub), { max: 36, min: 26, maxWidth: CONTENT_W - 80, maxHeight: 200, lh: 1.4 })
      : null;
    const bodyH = body ? body.height + 40 : 0;
    // Sobre a foto, destaques só de cor ficariam ilegíveis: usam o texto claro.
    const plainEm = ['italic', 'color'].includes(theme.style.emphasis);
    const titleSp = titleSpec(theme, fg, img && plainEm ? { emColor: fg } : {});
    const title = fitText(ctx, s.title, titleSp, {
      max: 140, min: 52, maxWidth: CONTENT_W, maxHeight: Math.min(760, BOTTOM - (M + 140) - bodyH), lh: 1.02,
    });
    let y = BOTTOM - title.height - bodyH;
    y = drawText(ctx, title, M, y, CONTENT_W);
    if (body) drawText(ctx, body, M, y + 40, CONTENT_W);
    return img ? LIGHT : c.muted;
  },

  conteudo(ctx, s, theme) {
    const c = theme.colors;
    let y = M;
    if (s.kicker) {
      drawKicker(ctx, theme, s.kicker, M, y, c.accent);
      y += 90;
    }
    const title = fitText(ctx, s.title, titleSpec(theme, c.text), { max: 92, min: 48, maxWidth: CONTENT_W, maxHeight: 420, lh: 1.06 });
    y = drawText(ctx, title, M, y, CONTENT_W) + 44;
    if (theme.style.rules) {
      ctx.fillStyle = c.accent;
      ctx.fillRect(M, y, 64, 3);
      y += 3 + 48;
    }
    if (s.body) {
      const body = fitText(ctx, s.body, bodySpec(theme, c.text), { max: 40, min: 24, maxWidth: CONTENT_W, maxHeight: BOTTOM - y, lh: 1.5 });
      drawText(ctx, body, M, y, CONTENT_W);
    }
    return c.muted;
  },

  citacao(ctx, s, theme) {
    const c = theme.colors;
    const t = theme.titleFont;
    if (s.kicker) drawKicker(ctx, theme, s.kicker, M, M, c.accent);
    ctx.font = `${t.weight} 300px "${t.family}", Georgia, serif`;
    ctx.fillStyle = c.accent;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('“', M - 10, M + 40);

    const top = M + 280;
    const authorH = s.body ? 26 + 56 : 0;
    // No estilo editorial a citação vai em itálico (e o destaque, reto).
    const spec = titleSpec(theme, c.text, theme.style.emphasis === 'italic' ? { style: 'italic', emStyle: 'normal' } : {});
    const quote = fitText(ctx, s.title, spec, { max: 88, min: 40, maxWidth: CONTENT_W, maxHeight: BOTTOM - top - authorH, lh: 1.15 });
    let y = Math.max(top, top + (BOTTOM - top - authorH - quote.height) / 2);
    y = drawText(ctx, quote, M, y, CONTENT_W);
    if (s.body) {
      y += 48;
      ctx.fillStyle = c.accent;
      ctx.fillRect(M, y + 12, 40, 2);
      drawKicker(ctx, theme, s.body, M + 60, y, c.muted, 'left', true);
    }
    return c.muted;
  },

  imagem(ctx, s, theme, img, preview) {
    const c = theme.colors;
    const ih = 760;
    if (img) {
      drawCover(ctx, img, 0, 0, SLIDE_W, ih, s.imagePos / 100);
    } else {
      ctx.save();
      ctx.globalAlpha = 0.14;
      ctx.fillStyle = c.accent;
      ctx.fillRect(0, 0, SLIDE_W, ih);
      ctx.restore();
      if (preview) {
        ctx.font = `500 30px "${theme.bodyFont.family}", sans-serif`;
        ctx.fillStyle = c.muted;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Adicione uma imagem no painel do slide', SLIDE_W / 2, ih / 2);
      }
    }
    let y = ih + 64;
    if (s.kicker) {
      drawKicker(ctx, theme, s.kicker, M, y, c.accent);
      y += 58;
    }
    const title = fitText(ctx, s.title, titleSpec(theme, c.text), { max: 72, min: 40, maxWidth: CONTENT_W, maxHeight: 220, lh: 1.08 });
    y = drawText(ctx, title, M, y, CONTENT_W) + 24;
    if (s.body && BOTTOM - y > 30) {
      const body = fitText(ctx, s.body, bodySpec(theme, c.muted), { max: 34, min: 22, maxWidth: CONTENT_W, maxHeight: BOTTOM - y, lh: 1.45 });
      drawText(ctx, body, M, y, CONTENT_W);
    }
    return c.muted;
  },

  final(ctx, s, theme) {
    const c = theme.colors;
    const title = fitText(ctx, s.title, titleSpec(theme, c.text), { max: 120, min: 52, maxWidth: CONTENT_W, maxHeight: 560, lh: 1.04 });
    const body = s.body
      ? fitText(ctx, s.body, bodySpec(theme, c.muted), { max: 36, min: 24, maxWidth: CONTENT_W - 120, maxHeight: 200, lh: 1.4 })
      : null;
    const pillH = theme.handle ? 80 : 0;
    const kickerH = s.kicker ? 26 + 48 : 0;
    const total = kickerH + title.height + (body ? 40 + body.height : 0) + (pillH ? 64 + pillH : 0);
    let y = M + (BOTTOM - M - total) / 2;

    if (s.kicker) {
      drawKicker(ctx, theme, s.kicker, SLIDE_W / 2, y, c.accent, 'center');
      y += kickerH;
    }
    y = drawText(ctx, title, M, y, CONTENT_W, 'center');
    if (body) y = drawText(ctx, body, M + 60, y + 40, CONTENT_W - 120, 'center');
    if (pillH) {
      y += 64;
      const label = `Siga ${theme.handle}`;
      ctx.font = `600 28px "${theme.bodyFont.family}", sans-serif`;
      const w = ctx.measureText(label).width + 96;
      roundRectPath(ctx, (SLIDE_W - w) / 2, y, w, pillH, pillH / 2);
      ctx.strokeStyle = c.accent;
      ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.fillStyle = c.accent;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, SLIDE_W / 2, y + pillH / 2 + 1);
    }
    return c.muted;
  },
};

// Função principal: desenha o slide inteiro.
// image = foto já carregada (ou null). preview = true mostra
// avisos que não devem aparecer no PNG final.
export function renderSlide(ctx, { slide, index, total, theme, image, preview = false }) {
  ctx.save();
  ctx.fillStyle = theme.colors.bg;
  ctx.fillRect(0, 0, SLIDE_W, SLIDE_H);
  const draw = layouts[slide.layout] || layouts.conteudo;
  const footerColor = draw(ctx, slide, theme, image, preview);
  drawFooter(ctx, theme, index, total, footerColor);
  ctx.restore();
}
