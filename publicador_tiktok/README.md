# Publicador do TikTok

Publica de 1 a 3 vídeos por dia no TikTok pela API oficial (Content Posting API, Direct Post), rodando no
**GitHub Actions**. Não depende do Codespace aberto.

```
Drive: pasta "Aprovados"  ->  GitHub Actions (a cada 30 min)  ->  TikTok
  video.mp4 + video.json        decide se é hora, publica 1        estado na branch tiktok-estado
```

## Como funciona

- **Aprovação:** só entra na fila o vídeo que você colocou na pasta **Aprovados** do Drive. Mover para lá é a sua aprovação.
- **Horários:** não são fixos. No primeiro disparo do dia o script sorteia de 1 a 3 horários em janelas de maior engajamento
  (07-09h, 12-14h, 18-22h, fuso de Brasília; a janela da noite tem mais chance). Ajuste em `config.py`. São referências gerais,
  não dados da sua conta. Como o cron do Actions atrasa, um horário vale por até 2 h depois de passar.
- **Fila:** ordem alfabética do nome do arquivo (use `01-`, `02-`...). Cada vídeo é identificado pelo ID e pelo checksum (md5)
  do Drive, então o mesmo conteúdo nunca é publicado duas vezes, mesmo reenviado com outro nome.
- **Legenda e hashtags por vídeo:** um `.json` com o mesmo nome base, na mesma pasta (`creatina.mp4` + `creatina.json`):
  ```json
  {
    "legenda": "Texto do post",
    "hashtags": ["creatina", "fitness"],
    "privacidade": "PUBLIC_TO_EVERYONE",
    "ia": false,
    "comentarios": true
  }
  ```
  Todos os campos são opcionais. Sem `.json`, vale `padroes.json`. Outros campos: `duet`, `stitch`, `capa_ms`,
  `conteudo_de_marca`, `promocao_propria`. Legenda inválida: o vídeo é pulado e aparece um aviso no log.
- **Estado:** `estado.json` na branch `tiktok-estado` (pública). Guarda só IDs, checksums, datas e status. Nunca legendas,
  nomes de arquivo ou tokens.
- **Falhas:** erro transitório (rede, instabilidade do TikTok) tenta de novo no próximo disparo, até 3 vezes. Recusa do TikTok
  (formato, duração, spam) marca o vídeo como `falhou`. Para tentar de novo, envie o arquivo outra vez. Erro de autorização ou
  de auditoria faz o workflow falhar, sem gastar o vídeo.

## Modos

| Variável (Settings > Secrets and variables > Actions > **Variables**) | Valores | Padrão |
|---|---|---|
| `TIKTOK_MODO` | `simulacao` (não envia nada) ou `real` | `simulacao` |
| `TIKTOK_PUBLICO` | `1` libera posts públicos | `0` (tudo `SELF_ONLY`) |
| `TIKTOK_POSTS_POR_DIA` | `1`, `2` ou `3` | `1` |

Enquanto o app do TikTok **não passar na auditoria**, a API só aceita posts privados. Por isso, sem `TIKTOK_PUBLICO=1`, o
publicador força `SELF_ONLY` mesmo que o `.json` peça público. Só ligue `TIKTOK_PUBLICO` depois da auditoria.

## O que cadastrar (Secrets)

| Secret | O que é |
|---|---|
| `GDRIVE_SA_KEY` | chave JSON da service account do Google (conteúdo inteiro) |
| `GDRIVE_FOLDER_ID` | ID da pasta **Aprovados** (a parte final do link da pasta) |
| `GDRIVE_PUBLICADOS_FOLDER_ID` | opcional: pasta **Publicados**, para onde o vídeo vai depois de postado |
| `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | do app no TikTok for Developers |
| `TIKTOK_REFRESH_TOKEN` | gerado pelo comando `autorizar` |
| `GH_SECRETS_PAT` | token fino do GitHub, só deste repositório, com **Secrets: Read and write** |

`GH_SECRETS_PAT` é necessário porque o TikTok pode trocar o refresh token a cada renovação e o `GITHUB_TOKEN` do workflow
não escreve em Secrets. Sem ele, o workflow avisa no log quando o token mudar.

Nunca cole tokens em issues, commits ou no chat.

## Passo a passo para ligar

1. **Drive:** crie as pastas *Aprovados* (e, se quiser, *Publicados*). No Google Cloud, crie uma service account, gere a chave
   JSON e compartilhe as pastas com o e-mail dela (leitor em *Aprovados*; editor se usar *Publicados*).
2. **TikTok for Developers:** crie o app com *Login Kit* e *Content Posting API* (Direct Post) e peça o escopo `video.publish`.
   Cadastre a URL de redirecionamento e as URLs públicas de política de privacidade e termos.
3. **Autorização (uma vez, no seu computador):**
   `TIKTOK_CLIENT_KEY=... TIKTOK_CLIENT_SECRET=... TIKTOK_REDIRECT_URI=... python -m publicador_tiktok autorizar`
   O token não é impresso: vai direto ao secret (se `GH_SECRETS_PAT` e `GITHUB_REPOSITORY` estiverem definidos) ou para
   `.tiktok_refresh_token`, que está no `.gitignore`. Cole no secret e apague o arquivo.
4. **Teste em simulação:** *Actions > TikTok - publicar vídeo aprovado > Run workflow > simulacao*. O log mostra o que seria publicado.
5. **Teste real privado:** defina `TIKTOK_MODO = real`. O post sai como privado, visível só para você.
6. **Auditoria:** com o fluxo funcionando, envie o app para auditoria no TikTok. Depois de aprovada, defina `TIKTOK_PUBLICO = 1`.

O agendamento só passa a valer depois que este código estiver na branch principal (workflows agendados rodam na branch padrão).

## Comandos

```
python -m publicador_tiktok publicar --estado _estado/estado.json   # uma execução
python -m publicador_tiktok status   --estado _estado/estado.json   # resumo da fila
python -m publicador_tiktok autorizar                               # autorização inicial
```

Testes: `pip install -r publicador_tiktok/requirements.txt pytest && pytest tests/test_tiktok_*.py`
(sem rede: o Drive e o TikTok são simulados).

## Limites conhecidos

- O fluxo de **autorização** e o envio real ao TikTok não foram testados contra a API de verdade (precisam das suas credenciais).
  Os testes simulam as respostas conforme a documentação oficial.
- O Actions pode atrasar o disparo em alguns minutos e, em repositório com pouca atividade, o GitHub desativa workflows
  agendados após 60 dias sem atividade. Se isso acontecer, reative em *Actions*.
- O limite de 3 posts por dia é uma trava do código; a conta do TikTok também tem limites próprios.
