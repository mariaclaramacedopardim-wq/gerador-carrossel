// Interface do Estúdio de Reels (sem frameworks, pensada para o Safari do iPad).
const TAMANHO_PEDACO = 8 * 1024 * 1024;
const $ = (id) => document.getElementById(id);
let projeto = null;
let sistema = {};
let consulta = null;
let ultimoErro = null;

const NOMES_PLANEJADOR = {
  demonstrativo: "Demonstrativo (regras simples, sem IA)",
  claude_code: "Claude Code + skill reels-creative-director",
  api_anthropic: "API da Anthropic",
  manual: "Manual",
};

function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const seg = (n) => `${Number(n).toFixed(1).replace(".", ",")} s`;

async function api(caminho, opcoes = {}) {
  const resp = await fetch(caminho, opcoes);
  let dados = {};
  try { dados = await resp.json(); } catch (_) { /* resposta sem JSON */ }
  if (!resp.ok) {
    const erro = new Error(dados.erro || (dados.erros || []).join("\n") || `Erro ${resp.status}`);
    erro.dados = dados;
    erro.status = resp.status;
    throw erro;
  }
  return dados;
}
const postJSON = (caminho, corpo) =>
  api(caminho, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo || {}) });

function mostrarStatus(texto, erro = false) {
  const el = $("status");
  if (!texto) { el.hidden = true; return; }
  el.hidden = false;
  el.textContent = texto;
  el.className = "status" + (erro ? " erro" : "");
  if (erro) setTimeout(() => { if (el.textContent === texto) el.hidden = true; }, 9000);
}

async function tentar(acao) {
  try { await acao(); } catch (e) { mostrarStatus(e.message, true); }
}

// ---------- Sistema e projetos ----------
async function carregarSistema() {
  sistema = await api("/api/sistema");
  const itens = [
    ["FFmpeg", sistema.ffmpeg && sistema.ffprobe],
    ["Textos na tela", sistema.textos_na_tela],
    ["Transcrição", sistema.transcricao],
    ["API Anthropic", sistema.api_anthropic_configurada && sistema.sdk_anthropic],
  ];
  $("sistema").innerHTML =
    itens.map(([nome, ok]) => `<span class="etiqueta ${ok ? "ok" : "alerta"}">${nome}: ${ok ? "sim" : "não"}</span>`).join("") +
    `<span class="etiqueta ${sistema.espaco_livre_mb > 2000 ? "ok" : "alerta"}">Disco livre: ${(sistema.espaco_livre_mb / 1024).toFixed(1)} GB</span>`;
  if (!sistema.ffmpeg) mostrarStatus("O FFmpeg não está instalado. Rode a tarefa 'Reels: instalar dependências' no Codespaces.", true);
}

async function carregarLista(selecionar) {
  const lista = await api("/api/projetos");
  const sel = $("lista-projetos");
  sel.innerHTML = lista.length
    ? lista.map((p) => `<option value="${esc(p.id)}">${esc(p.nome)} (${p.clipes} vídeo${p.clipes === 1 ? "" : "s"})</option>`).join("")
    : `<option value="">Nenhum projeto ainda</option>`;
  const id = selecionar || localStorage.getItem("projeto") || (lista[0] && lista[0].id);
  if (id && lista.some((p) => p.id === id)) {
    sel.value = id;
    await abrirProjeto(id);
  } else {
    projeto = null;
    $("area-projeto").hidden = true;
  }
}

async function abrirProjeto(id) {
  try { localStorage.setItem("projeto", id); } catch (_) { /* navegação privada */ }
  projeto = await api(`/api/projetos/${id}`);
  preencherBriefing();
  desenharTudo();
}

async function atualizarProjeto() {
  if (!projeto) return;
  projeto = await api(`/api/projetos/${projeto.id}`);
  desenharTudo();
}

function desenharTudo() {
  $("area-projeto").hidden = false;
  desenharClipes();
  desenharAnalise();
  desenharPlano();
  desenharResultado();
  desenharEstado();
}

function desenharEstado() {
  const e = projeto.estado;
  const ocupado = e.rodando;
  for (const id of ["analisar", "plano-demo", "plano-ia", "renderizar", "salvar-json"]) $(id).disabled = ocupado;
  if (!(sistema.api_anthropic_configurada && sistema.sdk_anthropic)) $("plano-ia").disabled = true;
  $("plano-ia").title = $("plano-ia").disabled && !ocupado ? "Configure o secret ANTHROPIC_API_KEY (veja o README)" : "";
  $("comando-claude").textContent =
    `/reels-creative-director monte o plano de edição do projeto ${projeto.id} do estúdio de Reels`;
  ultimoErro = ocupado ? null : ultimoErro;
  if (ocupado) {
    mostrarStatus(e.mensagem || "Processando...");
    clearTimeout(consulta);
    consulta = setTimeout(() => tentar(atualizarProjeto), 2000);
  } else if (e.erro) {
    if (e.erro !== ultimoErro) mostrarStatus(e.erro, true);
    ultimoErro = e.erro;
  } else {
    mostrarStatus("");
  }
}

// ---------- Briefing ----------
const CAMPOS = { nome: "b-nome", objetivo: "b-objetivo", estilo: "b-estilo", historia: "b-historia", duracao_alvo_s: "b-duracao",
  proporcao: "b-proporcao", tratamento_orientacao: "b-orientacao", ritmo: "b-ritmo", narracao: "b-narracao" };

function preencherBriefing() {
  for (const [chave, id] of Object.entries(CAMPOS)) $(id).value = chave === "nome" ? projeto.nome : projeto.briefing[chave];
}

function lerBriefing() {
  const dados = {};
  for (const [chave, id] of Object.entries(CAMPOS)) dados[chave] = $(id).value;
  return dados;
}

// ---------- Clipes ----------
function desenharClipes() {
  const analise = projeto.analise ? projeto.analise.clipes : {};
  $("clipes").innerHTML = projeto.clipes.map((c, i) => {
    const m = c.metadados;
    const a = analise[c.arquivo];
    const mini = a && a.miniatura ? `<img src="/arquivos/${projeto.id}/${a.miniatura}" alt="">` : `<div class="miniatura-vazia"></div>`;
    return `<li class="clipe" data-arquivo="${esc(c.arquivo)}">
      ${mini}
      <div>
        <div class="nome">${i + 1}. ${esc(c.arquivo)}</div>
        <div class="meta">${seg(m.duracao_s)} · ${m.largura}x${m.altura} · ${m.orientacao} · ${Math.round(m.fps)} fps · ${m.tem_audio ? "com áudio" : "sem áudio"}${m.hdr ? " · HDR" : ""}</div>
        <label class="chave"><input type="checkbox" class="indispensavel" ${c.indispensavel ? "checked" : ""}> Indispensável</label>
        <input type="text" class="descricao" placeholder="O que acontece neste clipe? (opcional)" value="${esc(c.descricao)}">
        <div class="acoes">
          <button class="discreto subir" ${i === 0 ? "disabled" : ""} aria-label="Subir">↑ Subir</button>
          <button class="discreto descer" ${i === projeto.clipes.length - 1 ? "disabled" : ""} aria-label="Descer">↓ Descer</button>
          <button class="discreto perigo remover">Remover</button>
        </div>
      </div>
    </li>`;
  }).join("");
}

function lerClipes() {
  return [...document.querySelectorAll("#clipes .clipe")].map((li) => ({
    arquivo: li.dataset.arquivo,
    indispensavel: li.querySelector(".indispensavel").checked,
    descricao: li.querySelector(".descricao").value,
  }));
}

async function salvarClipes(lista) {
  projeto = await postJSON(`/api/projetos/${projeto.id}/clipes`, { clipes: lista || lerClipes() });
  desenharTudo();
}

$("clipes").addEventListener("click", (ev) => tentar(async () => {
  const li = ev.target.closest(".clipe");
  if (!li) return;
  const lista = lerClipes();
  const i = lista.findIndex((c) => c.arquivo === li.dataset.arquivo);
  if (ev.target.classList.contains("subir") && i > 0) { [lista[i - 1], lista[i]] = [lista[i], lista[i - 1]]; await salvarClipes(lista); }
  if (ev.target.classList.contains("descer") && i < lista.length - 1) { [lista[i + 1], lista[i]] = [lista[i], lista[i + 1]]; await salvarClipes(lista); }
  if (ev.target.classList.contains("remover") && confirm(`Remover ${li.dataset.arquivo} deste projeto? (o vídeo no seu iPad não é afetado)`)) {
    projeto = await api(`/api/projetos/${projeto.id}/clipes/${encodeURIComponent(li.dataset.arquivo)}`, { method: "DELETE" });
    desenharTudo();
  }
}));
$("clipes").addEventListener("change", () => tentar(() => salvarClipes()));

// ---------- Envio em pedaços ----------
async function enviarArquivo(arquivo, li) {
  const barra = li.querySelector("progress");
  const texto = li.querySelector("span");
  const { arquivo: nome } = await postJSON(`/api/projetos/${projeto.id}/envio`, { nome: arquivo.name, tamanho: arquivo.size });
  let posicao = 0;
  let falhas = 0;
  while (true) {
    const fim = Math.min(posicao + TAMANHO_PEDACO, arquivo.size);
    const ultimo = fim >= arquivo.size;
    try {
      const r = await api(`/api/projetos/${projeto.id}/envio/${encodeURIComponent(nome)}?posicao=${posicao}${ultimo ? "&fim=1" : ""}`,
        { method: "PUT", body: arquivo.slice(posicao, fim) });
      falhas = 0;
      if (r.concluido) return r.clipe;
      posicao = r.recebido;
    } catch (e) {
      if (e.status === 409 && e.dados && typeof e.dados.recebido === "number") { posicao = e.dados.recebido; continue; }
      if (e.status && e.status !== 0 && e.status < 500) throw e;
      if (++falhas > 3) throw new Error(`O envio de ${arquivo.name} falhou várias vezes. Confira a conexão e tente de novo.`);
      await new Promise((ok) => setTimeout(ok, 2000 * falhas));
    }
    barra.value = posicao / arquivo.size;
    texto.textContent = `${arquivo.name}: ${Math.round((100 * posicao) / arquivo.size)}%`;
  }
}

$("arquivos").addEventListener("change", (ev) => tentar(async () => {
  const arquivos = [...ev.target.files];
  ev.target.value = "";
  const lista = $("envios");
  for (const arquivo of arquivos) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${esc(arquivo.name)}: aguardando</span><progress max="1" value="0"></progress>`;
    lista.appendChild(li);
  }
  const itens = [...lista.children].slice(-arquivos.length);
  for (const [i, arquivo] of arquivos.entries()) {
    try {
      const clipe = await enviarArquivo(arquivo, itens[i]);
      itens[i].querySelector("span").textContent = `${arquivo.name}: recebido (${seg(clipe.metadados.duracao_s)})`;
      itens[i].querySelector("progress").value = 1;
    } catch (e) {
      itens[i].querySelector("span").textContent = `${arquivo.name}: ${e.message}`;
      itens[i].querySelector("progress").remove();
    }
    await atualizarProjeto();
  }
}));

// ---------- Análise ----------
function desenharAnalise() {
  const el = $("analise");
  if (!projeto.analise) {
    el.innerHTML = `<p class="dica">Gera miniaturas, folhas de contato, cortes de cena e trechos com som de cada clipe.</p>`;
    return;
  }
  const a = projeto.analise;
  let html = projeto.analise_desatualizada
    ? `<div class="aviso">Os vídeos mudaram depois da última análise. Analise de novo antes de gerar o plano.</div>` : "";
  html += a.transcricao_disponivel ? "" : `<p class="dica">Transcrição desligada: o estúdio não sabe o que é dito nos clipes (veja o README para ativar).</p>`;
  for (const c of projeto.clipes) {
    const x = a.clipes[c.arquivo];
    if (!x) continue;
    html += `<details><summary>${esc(c.arquivo)} · ${x.candidatos} trecho(s) candidato(s)${x.avisos.length ? ` · ${x.avisos.length} aviso(s)` : ""}</summary>
      <p class="dica">Cortes de cena: ${x.cortes_de_cena_s.length ? x.cortes_de_cena_s.map(seg).join(", ") : "nenhum"}<br>
      Trechos com som: ${x.trechos_com_som_s.length ? x.trechos_com_som_s.map(([i, f]) => `${seg(i)}–${seg(f)}`).join(", ") : "nenhum"}</p>
      ${x.avisos.map((t) => `<div class="aviso">${esc(t)}</div>`).join("")}
      ${x.folha_contato ? `<a href="/arquivos/${projeto.id}/${x.folha_contato}" target="_blank"><img class="folha" src="/arquivos/${projeto.id}/${x.folha_contato}" alt="Folha de contato"></a>` : ""}
    </details>`;
  }
  html += `<details><summary>Limitações da análise</summary><ul>${a.limitacoes.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></details>`;
  el.innerHTML = html;
}

// ---------- Plano ----------
function desenharPlano() {
  const el = $("plano");
  const p = projeto.plano;
  let html = "";
  if (projeto.erros_plano.length) {
    html += `<div class="aviso erro"><b>O plano tem problemas:</b><ul>${projeto.erros_plano.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>`;
  }
  if (!p) {
    el.innerHTML = html || `<p class="dica">Ainda não há plano. Gere um plano demonstrativo para testar ou peça ao Claude Code.</p>`;
    return;
  }
  const tipo = p.planejador.tipo;
  html += `<p><span class="etiqueta ${tipo === "demonstrativo" ? "alerta" : "ok"}">${esc(NOMES_PLANEJADOR[tipo])}${p.planejador.modelo ? " · " + esc(p.planejador.modelo) : ""}</span>
    · ${p.segmentos.length} trechos · ${seg(p.duracao_total_estimada_s)} (pedido: ${seg(p.briefing.duracao_alvo_s)})</p>`;
  if (tipo === "demonstrativo") html += `<div class="aviso">Este plano não foi decidido por IA: segue regras fixas. Use para testar e como primeiro corte.</div>`;
  if (projeto.ultimo_custo_ia_usd != null && tipo === "api_anthropic") html += `<p class="dica">Custo estimado da última chamada: US$ ${projeto.ultimo_custo_ia_usd.toFixed(2)}</p>`;
  html += `<div class="tabela"><table><thead><tr><th>#</th><th>Arquivo</th><th>Trecho</th><th>Papel</th><th>Objetivo</th><th>Enquadr.</th><th>Áudio</th></tr></thead><tbody>`;
  for (const s of [...p.segmentos].sort((a, b) => a.ordem - b.ordem)) {
    html += `<tr><td>${s.ordem}</td><td>${esc(s.arquivo_origem)}</td><td>${seg(s.inicio_s)}–${seg(s.fim_s)}</td>
      <td>${esc(s.papel)}${s.obrigatorio ? "" : " (opcional)"}</td><td>${esc(s.objetivo_narrativo)}</td>
      <td>${esc(s.enquadramento.modo)}</td><td>${s.audio.modo === "mudo" ? "mudo" : Math.round(s.audio.volume * 100) + "%"}</td></tr>`;
  }
  html += `</tbody></table></div>`;
  if (p.textos_na_tela.length) html += `<p><b>Textos na tela:</b></p><ul>${p.textos_na_tela.map((t) => `<li>${seg(t.inicio_s)}–${seg(t.fim_s)} (${t.posicao}): “${esc(t.texto)}”</li>`).join("")}</ul>`;
  if (p.avisos.length) html += p.avisos.map((a) => `<div class="aviso">[${esc(a.tipo)}${a.segmento_id ? " · " + esc(a.segmento_id) : ""}] ${esc(a.mensagem)}</div>`).join("");
  el.innerHTML = html;
  if (!$("editor-json").open) $("json-plano").value = JSON.stringify(p, null, 2);
}

// ---------- Resultado ----------
function desenharResultado() {
  const el = $("resultado");
  const r = projeto.resultados;
  if (!r) { el.innerHTML = `<p class="dica">Gera o MP4 vertical, os trechos separados e o pacote para o CapCut.</p>`; return; }
  const base = `/arquivos/${projeto.id}/`;
  const nomes = {
    "reels_preview.mp4": "Montagem com textos (MP4)", "reels_base_sem_textos.mp4": "Montagem sem textos (MP4)",
    "shot_report.md": "Relatório (shot_report.md)", "edit_plan.json": "Plano (edit_plan.json)", "captions.srt": "Legendas (captions.srt)",
    "README.md": "Instruções do CapCut (README.md)", "textos_na_tela.txt": "Textos na tela (.txt)",
  };
  const principais = r.arquivos.filter((a) => nomes[a.split("/").pop()]);
  const v = Date.now();
  el.innerHTML = `<video controls playsinline preload="metadata" src="${base}saida/pacote_capcut/reels_preview.mp4?v=${v}"></video>
    <div class="downloads">
      <a class="botao" href="${base}${r.zip}?baixar=1">Baixar pacote completo (.zip)</a>
      ${principais.map((a) => `<a class="botao secundario" href="${base}${a}?baixar=1">${esc(nomes[a.split("/").pop()])}</a>`).join("")}
    </div>
    <details><summary>Trechos separados (pasta clips)</summary><ul>${r.arquivos.filter((a) => a.includes("/clips/"))
      .map((a) => `<li><a href="${base}${a}?baixar=1">${esc(a.split("/").pop())}</a></li>`).join("")}</ul></details>
    <p class="dica">No iPad, o download vai para o app Arquivos. Para levar um vídeo ao app Fotos: abra no Arquivos > Compartilhar > Salvar Vídeo.</p>`;
}

// ---------- Botões ----------
$("lista-projetos").addEventListener("change", (ev) => ev.target.value && tentar(() => abrirProjeto(ev.target.value)));
$("novo-projeto").addEventListener("click", () => tentar(async () => {
  const p = await postJSON("/api/projetos", {});
  await carregarLista(p.id);
}));
$("projeto-exemplo").addEventListener("click", () => tentar(async () => {
  mostrarStatus("Criando vídeos sintéticos de teste...");
  const p = await postJSON("/api/projetos/exemplo");
  await carregarLista(p.id);
}));
$("apagar-projeto").addEventListener("click", () => tentar(async () => {
  if (!projeto || !confirm(`Apagar o projeto "${projeto.nome}" e todos os arquivos dele neste Codespace?`)) return;
  await api(`/api/projetos/${projeto.id}`, { method: "DELETE" });
  try { localStorage.removeItem("projeto"); } catch (_) { /* ignore */ }
  await carregarLista();
  await carregarSistema();
}));
$("salvar-briefing").addEventListener("click", () => tentar(async () => {
  projeto = await postJSON(`/api/projetos/${projeto.id}/briefing`, lerBriefing());
  const atual = $("lista-projetos").value;
  await carregarLista(atual);
  mostrarStatus("Briefing salvo.");
  setTimeout(() => mostrarStatus(""), 2000);
}));
$("analisar").addEventListener("click", () => tentar(async () => {
  projeto = await postJSON(`/api/projetos/${projeto.id}/analisar`);
  desenharTudo();
}));
$("plano-demo").addEventListener("click", () => tentar(async () => {
  if (projeto.plano && !confirm("Substituir o plano atual? (a versão anterior fica salva como edit_plan.anterior.json)")) return;
  projeto = await postJSON(`/api/projetos/${projeto.id}/planejar`, { modo: "demonstrativo" });
  desenharTudo();
}));
$("plano-ia").addEventListener("click", () => tentar(async () => {
  if (!confirm(`Isto usa a API da Anthropic (${sistema.modelo_ia}) e é cobrado na sua conta da API (estimativa: menos de US$ 1 por plano). Continuar?`)) return;
  projeto = await postJSON(`/api/projetos/${projeto.id}/planejar`, { modo: "api" });
  desenharTudo();
}));
$("plano-recarregar").addEventListener("click", () => tentar(async () => {
  $("editor-json").open = false;
  await atualizarProjeto();
  mostrarStatus(projeto.plano ? "Plano recarregado." : "Nenhum plano encontrado.");
  setTimeout(() => mostrarStatus(""), 2500);
}));
$("salvar-json").addEventListener("click", () => tentar(async () => {
  $("erros-json").innerHTML = "";
  try {
    projeto = await api(`/api/projetos/${projeto.id}/plano`, { method: "POST", body: $("json-plano").value, headers: { "Content-Type": "application/json" } });
    $("erros-json").innerHTML = `<div class="aviso ok">Plano válido e salvo.</div>`;
    desenharTudo();
  } catch (e) {
    const erros = (e.dados && e.dados.erros) || [e.message];
    $("erros-json").innerHTML = `<div class="aviso erro"><ul>${erros.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
  }
}));
$("renderizar").addEventListener("click", () => tentar(async () => {
  projeto = await postJSON(`/api/projetos/${projeto.id}/renderizar`);
  desenharTudo();
}));

tentar(async () => { await carregarSistema(); await carregarLista(); });
