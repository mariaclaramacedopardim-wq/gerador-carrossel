# Pré-edição automática (Estúdio de Reels)

Use este guia quando a criadora pedir para **planejar a edição de um projeto do Estúdio de Reels** (pasta `estudio_reels/`
deste repositório), por exemplo: "monte o plano de edição do projeto 20261022-143000-ab12".

Aqui você é a editora: transforma o briefing e a análise dos clipes brutos em um `edit_plan.json` que o estúdio renderiza
em MP4. Você não renderiza nada; o estúdio faz isso quando ela toca em **Gerar montagem**.

## 1. Encontrar o material

Os projetos ficam em `estudio_reels_dados/projetos/<ID>/` (fora do Git). Leia, nesta ordem:

1. `analise/contexto_para_ia.md`: briefing, clipes na ordem escolhida, marcação INDISPENSÁVEL/opcional, descrição de cada
   clipe, metadados, cortes de cena, trechos com som, transcrição (se houver) e trechos candidatos.
2. As folhas de contato `analise/<clipe>/folha_contato.jpg` (abra as imagens com a ferramenta de leitura). Cada quadro tem o
   tempo em segundos.
3. Se precisar de detalhe: `analise/analise.json` e `projeto.json`.

Se `analise/` estiver vazia ou o projeto disser `"analise_desatualizada": true`, peça para ela tocar em **Analisar clipes** antes.
Para listar os projetos: `bash estudio_reels/rodar.sh projetos`.

## 2. Limites honestos

- Você só vê **quadros amostrados**. Não descreva ações, falas ou expressões que não aparecem nos quadros ou na transcrição.
- Sem transcrição, você **não sabe o que é dito**. Use a descrição da criadora e os trechos com som; registre a incerteza em
  `avisos` (tipo `conteudo`) e em `observacoes`.
- "Trecho com som" pode ser música ou ruído, não necessariamente fala.

## 3. Planejar com a skill

Aplique o resto da skill como se estivesse montando o roteiro, agora com material já gravado:

- Gancho nos primeiros 1 a 3 s, entrega do que o gancho promete, fechamento com CTA ([creative-strategy.md](creative-strategy.md)).
- Ritmo: mudança de imagem a cada 2 a 4 s no corpo; corte seco como padrão ([capcut-workflow.md](capcut-workflow.md)).
- Textos na tela de até ~7 palavras, no mínimo 1,5 s, na área segura ([scriptwriting.md](scriptwriting.md)).
- Inclua todos os clipes INDISPENSÁVEIS. Escolha trechos pela história, continuidade, variedade visual, clareza da fala e
  ritmo, **nunca** só por serem curtos ou movimentados.
- Comece e termine trechos nos candidatos, cortes de cena ou limites de frase, para não interromper fala ou ação.
- Clipes horizontais em 9:16: `encaixar_desfocado` quando a pessoa ou a ação ocupa a largura; `preencher` com `foco_x`
  ajustado quando o assunto cabe numa faixa vertical (diga nos avisos que é preciso conferir).
- Não adicione música, efeitos ou transições que não foram pedidos. Música é só orientação em `audio_geral.musica`.
- Saúde e estética: siga as regras de ética e evidência do [SKILL.md](../SKILL.md) nos textos na tela.

## 4. Escrever e validar o plano

1. Siga o formato de [`estudio_reels/ESQUEMA_PLANO.md`](../../../../estudio_reels/ESQUEMA_PLANO.md)
   (esquema formal em `estudio_reels/esquema_plano.json`).
2. Use `"planejador": {"tipo": "claude_code", "modelo": null, "observacao": "..."}` e explique na observação o que você viu
   (quadros, transcrição) e o que não pôde conferir.
3. Calcule `duracao_s = (fim_s - inicio_s) / velocidade` e `duracao_total_estimada_s` = soma das durações menos as transições.
4. Salve em `estudio_reels_dados/projetos/<ID>/plano/edit_plan.json`. Se já existir um plano, copie-o antes para
   `edit_plan.anterior.json` na mesma pasta.
5. Rode `bash estudio_reels/rodar.sh validar <ID>` e corrija até aparecer "Plano válido."
6. Responda à criadora com: um resumo da história em 2 a 3 frases, a lista de cenas (tempo no vídeo final, clipe, papel),
   os avisos principais e o próximo passo: **"No estúdio, toque em Recarregar plano e depois em Gerar montagem."**

Não faça commit dos dados do projeto: `estudio_reels_dados/` fica fora do Git de propósito.
