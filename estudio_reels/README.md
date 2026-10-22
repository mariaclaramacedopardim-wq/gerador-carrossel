# Estúdio de Reels (pré-edição automática)

Você envia os clipes brutos e um briefing curto. O estúdio analisa o material, monta um **plano de edição em JSON**,
gera uma **montagem preliminar em MP4** (9:16) e entrega um **pacote para finalizar no CapCut**.

É uma extensão da skill [`reels-creative-director`](../.claude/skills/reels-creative-director/SKILL.md): quando o plano é
feito por IA (Claude Code ou API), as instruções de storytelling, roteiro e edição da skill são usadas.

---

## Como usar no iPad (passo a passo)

### 1. Abrir o estúdio (uma vez por sessão)

1. Abra o seu Codespace do repositório `gerador-carrossel` no Safari.
2. Toque no menu **☰** (canto superior esquerdo) > **Terminal** > **Run Task...** (Executar Tarefa).
3. Escolha **Reels: abrir estúdio**.
   - Na primeira vez, ele instala o FFmpeg e as bibliotecas sozinho (leva 1 a 3 minutos).
   - Se preferir digitar, o comando é: `bash estudio_reels/iniciar.sh`
4. Quando aparecer `Estúdio de Reels rodando na porta 8000`, abra a aba **PORTAS (PORTS)**, no painel de baixo.
5. Na linha da porta **8000**, toque no ícone de **globo** (Abrir no navegador). O estúdio abre numa nova aba do Safari.

> A porta fica **privada** (só abre com o seu login do GitHub). Não mude a visibilidade para "Public".
> Deixe a aba do Codespace aberta enquanto usa o estúdio: se o Codespace hibernar, o estúdio para.

### 2. Usar o estúdio

1. **Novo projeto.** (Para testar sem vídeos seus, toque em *Criar exemplo com vídeos sintéticos*.)
2. **Briefing:** objetivo, estilo, história, duração, proporção, ritmo e narração. Toque em *Salvar briefing*.
3. **Vídeos:** *Escolher vídeos* abre a galeria. Selecione vários. Cada um aparece com duração e resolução.
   - Marque **Indispensável** nos clipes que não podem faltar.
   - Escreva em uma linha o que acontece em cada clipe (ajuda muito o planejamento).
   - Use ↑ e ↓ para colocar na ordem da história.
4. **Analisar clipes.** Gera miniaturas, folhas de contato, cortes de cena e trechos com som.
5. **Plano de edição:** escolha uma das três formas (veja abaixo).
6. **Gerar montagem.** Assista ao vídeo na própria página.
7. **Baixar pacote completo (.zip).** Vai para o app Arquivos. Toque no .zip para descompactar e siga o `README.md` de dentro.

### Três formas de gerar o plano

| Forma | Custo | Quem decide | Quando usar |
|---|---|---|---|
| **Plano demonstrativo (sem IA)** | grátis | Regras fixas: ordem dos clipes, indispensáveis primeiro, sem cortar trechos com som, duração e ritmo pedidos | Testar o fluxo e ter um primeiro corte rápido. **Não entende o vídeo.** |
| **Claude Code** | incluído na sua assinatura | Claude, usando a skill e as folhas de contato | O jeito recomendado. Veja abaixo. |
| **Plano com IA (API paga)** | cobrado à parte | Modelo da Anthropic pela API | Só se você quiser o botão automático e tiver conta de API. |

**Claude Code (sem custo extra):** depois de *Analisar clipes*, abra o Claude Code no Codespace e escreva o comando que aparece
na seção 4 do estúdio, por exemplo:

```
/reels-creative-director monte o plano de edição do projeto 20261022-143000-ab12 do estúdio de Reels
```

O Claude lê a análise, olha as folhas de contato, escreve o `edit_plan.json` e confere com o validador. Depois toque em
**Recarregar plano** e em **Gerar montagem**.

---

## O que funciona e o que não funciona

**Funciona:**
- Envio de vários vídeos pelo Safari, em pedaços de 8 MB (aguenta arquivos grandes e conexões instáveis).
- Leitura de duração, resolução, rotação do iPhone, orientação, fps, áudio e HDR.
- Miniaturas, folhas de contato, detecção de cortes de cena e de trechos com som/silêncio.
- Plano em JSON validado por esquema ([ESQUEMA_PLANO.md](ESQUEMA_PLANO.md)) e por regras de tempo e ordem.
- Montagem em MP4 H.264 + AAC, 1080x1920 (ou 4:5 e 1:1), 30 fps, sem distorcer: corta para preencher ou mostra o clipe
  inteiro com fundo desfocado ou faixas pretas.
- Cortes secos (padrão), dissolver e fade para preto quando o plano pedir; velocidade de 0,5x a 3x; volume ou mudo por trecho.
- Textos na tela e legendas desenhados no preview; versão sem textos para o CapCut; cada trecho em arquivo separado.
- Relatório (`shot_report.md`), legendas (`captions.srt`, quando houver), instruções do CapCut e um .zip com tudo.
- Erros comuns explicados em português: arquivo que não é vídeo, envio incompleto, codec não suportado, falta de espaço.

**Limitações (importante):**
- **Ninguém "assiste" ao vídeo inteiro.** A análise usa quadros amostrados (até 12 por clipe + pontos de corte). Nem o
  planejador demonstrativo nem um modelo de IA veem o que acontece entre esses quadros.
- "Trecho com som" não significa "fala": pode ser música, vento ou ruído.
- **Sem transcrição, o estúdio não sabe o que é dito.** A transcrição é opcional (veja abaixo) e precisa ser revisada.
- O plano demonstrativo não entende o briefing: só usa duração, ritmo, narração, ordem e marcações.
- **Não existe projeto nativo do CapCut.** O CapCut não oferece importação oficial de linha do tempo criada fora dele.
  Existem ferramentas não oficiais que escrevem o arquivo interno de projeto do CapCut para **computador**, mas elas dependem
  da versão, podem quebrar a cada atualização e não servem para o CapCut do iPad. Por isso o pacote traz vídeos e arquivos de apoio.
- O CapCut do iPhone/iPad **não importa .srt** (segundo a [central de ajuda do CapCut](https://www.capcut.com/help/how-to-import-subtitles)).
  O `captions.srt` serve no CapCut para computador ou web, ou como referência.
- O estúdio **nunca** adiciona música, efeitos sonoros ou transições que não estejam no plano, e não baixa nada da internet.
- A verificação automática confere formato, resolução e duração. Se o vídeo ficou bom, só você decide assistindo.

---

## Opcionais

### Transcrição da fala (grátis, roda no Codespace)

```
.venv-reels/bin/python -m pip install -r estudio_reels/requirements-transcricao.txt
```

Depois reinicie o estúdio e analise os clipes de novo. No primeiro uso, ele baixa um modelo de cerca de 500 MB.
A análise fica mais lenta: em um Codespace de 2 núcleos, pode levar alguns minutos por clipe (não medi em vídeos reais).
Com transcrição, os trechos candidatos respeitam o começo e o fim das frases, e o pacote traz `captions.srt` como
**rascunho não revisado**.

### Plano pela API da Anthropic (pago)

- A assinatura do Claude e o Claude Code **não incluem** a API. É preciso uma conta em
  [console.anthropic.com](https://console.anthropic.com) com créditos, cobrada por uso.
- Custo estimado por plano com o modelo padrão (`claude-opus-5-5`, US$ 4 por milhão de tokens de entrada e US$ 20 por
  milhão de saída): em geral **US$ 0,30 a US$ 1,00**, dependendo do número de clipes. Uma rodada extra de correção pode dobrar
  o valor. O estúdio mostra a estimativa depois de cada chamada.
- Para ativar:
  1. Crie a chave no Console da Anthropic.
  2. No GitHub: **Settings > Codespaces > Secrets > New secret**. Nome: `ANTHROPIC_API_KEY`. Em *Repository access*, escolha `gerador-carrossel`.
  3. Reinicie o Codespace e rode: `.venv-reels/bin/python -m pip install -r estudio_reels/requirements-ia.txt`
- **Nunca** cole a chave em arquivos do projeto nem em mensagens.
- Para usar outro modelo, defina o secret `ESTUDIO_REELS_MODELO` (ex.: `claude-sonnet-5-5`, mais barato).

---

## Para quem programa

### Arquitetura

```
Safari (iPad) ──HTTP──> Flask (estudio_reels/app.py) ──> projetos.py (pastas, sem banco de dados)
                                                           ├── analise.py        FFprobe/FFmpeg + Pillow (+ transcricao.py opcional)
                                                           ├── planejador_demo.py  regras fixas, marcado "demonstrativo"
                                                           ├── planejador_ia.py    API da Anthropic (opcional)
                                                           ├── plano.py          esquema JSON + validação + linha do tempo
                                                           ├── renderizador.py   FFmpeg: trechos, união, textos, verificação
                                                           └── pacote.py         relatório, SRT, README, .zip
```

A análise e a renderização são separadas do planejamento: qualquer plano válido (escrito à mão, pelo Claude Code ou pela API)
é renderizado do mesmo jeito. Tarefas demoradas rodam uma por vez em segundo plano e a página consulta o estado a cada 2 s.

Dados de cada projeto (fora do Git, em `estudio_reels_dados/projetos/<id>/`):

```
projeto.json                  briefing, clipes (ordem, indispensável, descrição, metadados), estado
originais/                    vídeos enviados, nunca alterados
analise/analise.json          tudo o que a análise encontrou
analise/contexto_para_ia.md   resumo para o planejamento por IA
analise/<clipe>/folha_contato.jpg e quadros/
plano/edit_plan.json          plano atual (o anterior fica em edit_plan.anterior.json)
saida/pacote_capcut/          resultados; saida/pacote_capcut.zip
```

### Linha de comando

O atalho `estudio_reels/rodar.sh` usa o ambiente Python do estúdio (`.venv-reels`) e instala o que faltar.

```
bash estudio_reels/rodar.sh                  # interface web na porta 8000 (o mesmo que iniciar.sh)
bash estudio_reels/rodar.sh sistema          # confere FFmpeg, fontes, transcrição e API
bash estudio_reels/rodar.sh exemplo          # projeto sintético de ponta a ponta
bash estudio_reels/rodar.sh projetos         # lista os projetos
bash estudio_reels/rodar.sh analisar ID
bash estudio_reels/rodar.sh planejar ID [api]
bash estudio_reels/rodar.sh validar ID       # ou o caminho de um edit_plan.json
bash estudio_reels/rodar.sh renderizar ID
.venv-reels/bin/python -m pytest -q          # testes (usam só vídeos sintéticos)
```

### Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "O FFmpeg não está instalado" | Rode a tarefa **Reels: instalar dependências**. |
| A porta 8000 não aparece | Confira se a tarefa *Reels: abrir estúdio* ainda está rodando no terminal. |
| "Falta espaço no disco" | Apague projetos antigos (botão *Apagar este projeto*) ou envie vídeos em 1080p. |
| O envio parou no meio | Escolha o vídeo de novo. O pedaço que falhou é reenviado automaticamente até 3 vezes. |
| As cores de um vídeo HDR ficaram estranhas | O estúdio converte HDR para SDR; confira e ajuste a cor no CapCut. |
| A página parou de responder | O Codespace pode ter hibernado. Volte à aba do Codespace e rode a tarefa de novo. |
