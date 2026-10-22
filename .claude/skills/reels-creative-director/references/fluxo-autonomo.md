# Fluxo autônomo de edição (iPad + Claude Code na nuvem)

Use este guia quando a criadora **enviar vídeos brutos e pedir um Reels editado**, ou pedir **alterações numa versão já
gerada**. Você é a editora: decide sozinha o que for razoável, pergunta só o essencial, monta, renderiza, entrega o MP4 no
chat e aplica os pedidos de alteração gerando novas versões. Tudo roda com o Estúdio de Reels (`estudio_reels/`); não use
outro editor.

## 0. Ambiente

- Na sessão na nuvem, o hook de início (`.claude/hooks/preparar_estudio.sh`) instala FFmpeg e `.venv-reels`. Confira com
  `bash estudio_reels/rodar.sh sistema` se algo falhar.
- Os vídeos anexados no chat ficam em `/root/.claude/uploads/<sessão>/` **só nesta sessão**. Não existem no Codespace nem
  em sessões futuras.
- `estudio_reels_dados/` (vídeos, análises, renders) é apagado quando a sessão acaba. O que sobrevive é a memória em
  `estudio_reels_memoria/<ID>/` (texto), **depois do commit e push** (ver o passo 4 sobre o repositório público).

## 1. Receber o material e perguntar só o essencial

Antes de perguntar, leia: o pedido, `REFERENCIAS_CRIATIVAS/04_MINHA_IDENTIDADE/IDENTIDADE_CRIATIVA.md`, o índice de
referências e, se for um projeto existente, `estudio_reels_memoria/<ID>/`.

Pergunte **de uma vez, no máximo 3 perguntas**, e só o que não puder deduzir:

| Pergunte se faltar | Não pergunte (decida e declare) |
| --- | --- |
| Tema ou mensagem do vídeo, quando nem o pedido nem as imagens deixam claro | Duração (padrões da skill: 15–25 s demonstração, 30–45 s educativo) |
| Se o som original tem fala que precisa ficar (sem transcrição você não sabe o que é dito) | Proporção (9:16), ritmo, enquadramento, cortes (seco), ordem dos trechos |
| Frases exatas na tela, quando ela disser que quer textos mas não quais | Estilo de texto (vem da identidade), tamanho, posição |

Se o pedido já for suficiente, não pergunte nada. Declare as suposições em uma linha na entrega.

## 2. Importar e analisar

```
bash estudio_reels/rodar.sh importar --nome "Nome curto" --briefing /caminho/briefing.json VIDEO1 VIDEO2...
bash estudio_reels/rodar.sh analisar ID
```

- `briefing.json`: `{"objetivo", "estilo", "historia", "duracao_alvo_s", "proporcao", "tratamento_orientacao", "ritmo",
  "narracao"}`; campos omitidos ficam com o padrão. Escreva-o no scratchpad, não no repositório.
- O prefixo aleatório dos anexos (`a2c17be9-`) é retirado do nome do clipe, para o plano valer em outra sessão.
- Depois da análise, leia `analise/contexto_para_ia.md` e **abra as folhas de contato** (Read nas imagens).

## 3. Planejar (você decide)

Siga [pre-edicao-automatica.md](pre-edicao-automatica.md) para escrever `plano/edit_plan.json`, com estas regras a mais:

- Consulte a identidade e só as fichas de referência relevantes (CLAUDE.md). Instrução explícita da criadora vence a
  identidade; conflito entre referência visual e instrução escrita: pergunte.
- Regra fixa dela: textos entram e saem em **corte seco**. O estúdio já faz assim (sem fade nos textos).
- **Estilo dos textos:** se a identidade definir fonte/cor, escreva `estudio_reels_dados/projetos/<ID>/estilo_textos.json`.
  Campos: `fonte` (arquivo em `estudio_reels/fontes/` ou caminho), `cor` (`#RRGGBB`), `caixa` (fundo escuro atrás do texto),
  `contorno`, `tamanho` (fração da largura, padrão 0.058), `entrelinha`, `maiusculas`, `centralizar_linhas`
  (cada linha centrada, FFmpeg 6.1+), `escurecer_fundo` (0 a 0.3: escurece o vídeo para ler o texto). Fonte disponível:
  `GochiHand-Regular.ttf` (manuscrita do projeto ID). Sem o arquivo, o estúdio usa branco com caixa escura.
- `planejador.tipo` = `"claude_code"`. Valide com `bash estudio_reels/rodar.sh validar ID` até "Plano válido."

O que o renderizador **faz**: cortes, ordem, velocidade (0,5–3x), volume/mudo por trecho, enquadramento (preencher com
foco e zoom fixo, encaixar com fundo desfocado ou barras), transições dissolver/fade para preto, textos e legendas
desenhados, conversão HDR→SDR.

O que ele **não faz** (diga isso em vez de prometer): música, efeitos sonoros, zoom animado (keyframes), textos animados,
filtros de cor (só o `escurecer_fundo` do estilo de texto). Para animações e gráficos, use a skill Remotion **num projeto à parte fora do repositório** e só quando a
criadora pedir; o resultado entra no estúdio como um clipe a mais.

## 4. Renderizar e entregar

```
bash estudio_reels/rodar.sh auto ID
```

`auto` analisa se preciso, usa o plano existente (sem plano, gera o demonstrativo), renderiza e guarda `saida/versoes/vN.mp4`
e a memória (`estudio_reels_memoria/ID/`). Depois:

1. Confira 3 a 6 quadros do vídeo final (extraia com FFmpeg e abra) antes de entregar.
2. Envie o MP4 com **SendUserFile** (`display: "render"`), legenda curta com versão e duração.
3. Responda em poucas linhas: suposições, a história em 1 frase, o que decidiu (ritmo, enquadramento, textos) e o que não
   pôde conferir. Termine com: "Peça alterações do jeito que quiser falar."
4. Para a memória sobreviver à sessão, faça commit e push só de `estudio_reels_memoria/ID/` (nunca de
   `estudio_reels_dados/`). **O repositório é público**: briefing, textos e nomes dos clipes ficam visíveis. Na primeira
   vez, pergunte se pode publicar ou sugira deixar o repositório privado; registre a resposta na identidade criativa.

## 5. Alterações em linguagem natural

Não peça o briefing de novo. Leia `estudio_reels_memoria/ID/historico.md` e o plano atual, traduza o pedido em mudanças no
plano (ou no `estilo_textos.json`), valide e rode:

```
bash estudio_reels/rodar.sh auto ID --pedido "texto do pedido, como ela escreveu"
```

| Pedido | Mudança |
| --- | --- |
| "mais rápido", "mais dinâmico" | encurtar trechos, tirar opcionais, ritmo menor por plano |
| "tira/troca/move o texto" | `textos_na_tela` (texto, tempos, posição) |
| "começa com a cena X" | `ordem` dos segmentos e o papel `gancho` |
| "aproxima", "dá zoom" | `enquadramento.zoom` (1–2) e `foco_x/foco_y` |
| "sem som", "mais baixo" | `audio.modo` = mudo / `audio.volume` |
| "fonte/cor das letras", "não dá para ler" | `estilo_textos.json` (`cor`, `tamanho`, `escurecer_fundo`) |
| "mais curto/longo" | trechos e `duracao_total_estimada_s` |

Pedido ambíguo que muda o resultado de forma importante: pergunte uma vez, objetivamente. Pedido que o renderizador não
faz (música, efeito sonoro, zoom animado): diga e ofereça o caminho possível. Preferência que ela disser que vale "sempre":
proponha registrar na identidade criativa.

## 6. Retomar em outra sessão

Os vídeos não ficam guardados. Peça para ela anexar os mesmos vídeos de novo (o nome original, como `IMG_3935.MOV`, precisa
ser o mesmo) e rode:

```
bash estudio_reels/rodar.sh restaurar ID VIDEO1 VIDEO2...
bash estudio_reels/rodar.sh auto ID --pedido "..."
```

`restaurar` recria o projeto com o briefing, a ordem dos clipes, o estilo de texto e o último plano. A numeração das versões
continua de onde parou.
