# Esquema do plano de edição (`edit_plan.json`)

O esquema formal (JSON Schema 2020-12) está em [`esquema_plano.json`](esquema_plano.json). Além dele, `plano.py` confere
regras de tempo e ordem que um esquema sozinho não expressa. Valide qualquer plano com:

```
bash estudio_reels/rodar.sh validar ID_DO_PROJETO
bash estudio_reels/rodar.sh validar caminho/para/edit_plan.json
```

## Convenções

- **Todos os tempos são em segundos** (números decimais, ex.: `3.25`).
- `inicio_s` / `fim_s` de um **segmento** são tempos do **arquivo de origem**.
- `inicio_s` / `fim_s` de **textos na tela** e **legendas** são tempos do **vídeo final**.
- Todos os campos são obrigatórios; campos opcionais aceitam `null` ou lista vazia. Campos desconhecidos são recusados.

## Campos principais

| Campo | Tipo | Significado |
|---|---|---|
| `versao_esquema` | `"1.0"` | Versão deste formato. |
| `planejador.tipo` | `demonstrativo` \| `claude_code` \| `api_anthropic` \| `manual` | Quem decidiu o plano. `demonstrativo` = regras simples, sem IA. |
| `planejador.modelo` | texto ou `null` | Modelo de IA usado, quando houver. |
| `planejador.observacao` | texto | Como o plano foi feito e o que conferir. |
| `briefing` | objeto | Cópia do briefing: objetivo, estilo, história, `duracao_alvo_s`, proporção, tratamento de orientação, ritmo, narração. |
| `formato_saida` | `{largura, altura, fps}` | Ex.: `1080 x 1920`, 30 fps. |
| `segmentos` | lista | Os trechos, na ordem do vídeo (ver abaixo). |
| `textos_na_tela` | lista | `{id "T01", texto, inicio_s, fim_s, posicao topo/centro/inferior, segmento_id}`. |
| `legendas` | objeto | `{fonte, revisadas, queimar_no_preview, itens: [{inicio_s, fim_s, texto}]}`. Gera `captions.srt` quando há itens. |
| `audio_geral` | objeto | Orientações de `musica`, `narracao`, `efeitos_sonoros` (o estúdio nunca adiciona música). |
| `orientacoes_edicao` | objeto | `transicoes_e_efeitos`, `tratamento_visual`, `ajustes_no_capcut` (lista). |
| `avisos` | lista | `{tipo corte/audio/qualidade/enquadramento/duracao/conteudo, segmento_id, mensagem}`. |
| `clipes_nao_usados` | lista | `{arquivo, motivo}`. |
| `duracao_total_estimada_s` | número | Soma das durações dos segmentos menos as transições. |

### Cada segmento

| Campo | Tipo | Significado |
|---|---|---|
| `id` | `"S01"`, `"S02"`... | Identificador. |
| `ordem` | inteiro | Posição no vídeo: 1, 2, 3... sem pular nem repetir. |
| `arquivo_origem` | texto | Nome do clipe enviado (como aparece na lista do estúdio). |
| `inicio_s`, `fim_s` | número | Trecho usado do clipe de origem. |
| `duracao_s` | número | Duração no vídeo final = `(fim_s - inicio_s) / velocidade`. |
| `papel` | `gancho` \| `contexto` \| `desenvolvimento` \| `demonstracao` \| `prova` \| `virada` \| `conclusao` \| `cta` \| `broll` | Função na história. |
| `objetivo_narrativo` | texto | Por que esta cena está aqui. |
| `obrigatorio` | sim/não | `false` = cena **[OPCIONAL]**, pode sair sem quebrar o vídeo. |
| `enquadramento` | `{modo, foco_x, foco_y, zoom}` | `preencher` corta para encher a tela (`foco_x` 0 = esquerda, 0,5 = centro, 1 = direita); `encaixar_desfocado` mostra o clipe inteiro com o próprio clipe desfocado ao fundo; `encaixar_barras` mostra inteiro com faixas pretas. `zoom` de 1 a 2. Nenhum modo distorce a imagem. |
| `audio` | `{modo original/mudo, volume 0–2}` | Som do trecho. |
| `velocidade` | 0,5 a 3 | 1 = normal. Com áudio original, entre 0,5 e 2. |
| `transicao_entrada` | `{tipo corte/dissolver/fade_preto, duracao_s}` | Como este trecho entra. O primeiro é sempre `corte`. A transição sobrepõe os trechos e encurta o total. |
| `tratamento_visual` | texto | Orientação de cor/estilo para o CapCut (o estúdio não aplica filtros). |
| `observacoes` | texto | Notas sobre o corte. |

## Regras conferidas além do esquema

- `fim_s` maior que `inicio_s`; o trecho cabe na duração do clipe de origem; o arquivo existe no projeto.
- `duracao_s` bate com `(fim_s - inicio_s) / velocidade` (tolerância de 0,05 s).
- `ordem` é 1, 2, 3...; `id` não se repete.
- Transição: nunca no primeiro segmento; com duração > 0; no máximo metade do menor dos dois trechos vizinhos.
- `duracao_total_estimada_s` bate com a linha do tempo calculada (tolerância de 0,15 s).
- Textos e legendas terminam antes do fim do vídeo; `segmento_id` e avisos apontam para segmentos que existem.

## Exemplo resumido

```json
{
  "versao_esquema": "1.0",
  "planejador": {"tipo": "claude_code", "modelo": null, "observacao": "Planejado com a skill reels-creative-director."},
  "briefing": {"objetivo": "Mostrar meu aquecimento de corrida", "estilo": "calmo", "historia": "...", "duracao_alvo_s": 20,
               "proporcao": "9:16", "tratamento_orientacao": "encaixar_desfocado", "ritmo": "medio", "narracao": "fala_dos_clipes"},
  "formato_saida": {"largura": 1080, "altura": 1920, "fps": 30},
  "segmentos": [
    {"id": "S01", "ordem": 1, "arquivo_origem": "IMG_4512.MOV", "inicio_s": 1.2, "fim_s": 4.4, "duracao_s": 3.2,
     "papel": "gancho", "objetivo_narrativo": "Apresentar o problema olhando para a câmera.", "obrigatorio": true,
     "enquadramento": {"modo": "preencher", "foco_x": 0.5, "foco_y": 0.4, "zoom": 1.0},
     "audio": {"modo": "original", "volume": 1.0}, "velocidade": 1.0,
     "transicao_entrada": {"tipo": "corte", "duracao_s": 0},
     "tratamento_visual": "Contraste +10 no CapCut.", "observacoes": ""}
  ],
  "textos_na_tela": [{"id": "T01", "texto": "Aquecer não é perder tempo", "inicio_s": 0, "fim_s": 2.5, "posicao": "topo", "segmento_id": "S01"}],
  "legendas": {"fonte": "nenhuma", "revisadas": false, "queimar_no_preview": false, "itens": []},
  "audio_geral": {"musica": "Sem música no preview; escolher no CapCut, 10–20% sob a fala.", "narracao": "Fala original.", "efeitos_sonoros": "Nenhum."},
  "orientacoes_edicao": {"transicoes_e_efeitos": "Cortes secos.", "tratamento_visual": "Natural.", "ajustes_no_capcut": ["Gerar legendas automáticas e revisar."]},
  "avisos": [],
  "clipes_nao_usados": [],
  "duracao_total_estimada_s": 3.2
}
```
