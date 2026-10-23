# gerador-carrossel

## Skill `reels-creative-director`

Skill do Claude Code para criar Instagram Reels da ideia à edição no CapCut. Fica em `.claude/skills/reels-creative-director/`.

Como usar: abra o Claude Code neste repositório e digite `/reels-creative-director` seguido do tema, por exemplo:

```
/reels-creative-director Reel de 30 segundos sobre creatina para mulheres, gravado em casa
```

Ou peça normalmente ("cria um Reel sobre...") e o Claude carrega a skill sozinho.

## Estúdio de Reels (pré-edição automática)

Interface web para enviar clipes brutos pelo Safari do iPad, gerar um plano de edição em JSON, uma montagem preliminar em MP4
(9:16) e um pacote para finalizar no CapCut. Fica em `estudio_reels/`.

No Codespaces: **☰ > Terminal > Run Task... > Reels: abrir estúdio**, depois abra a porta 8000 na aba **PORTAS**.
Passo a passo, limitações e opções em [estudio_reels/README.md](estudio_reels/README.md).

## Publicador do TikTok (automático)

Publica de 1 a 3 vídeos por dia no TikTok a partir de uma pasta *Aprovados* do Google Drive, usando a API oficial e o GitHub
Actions (não precisa do Codespace aberto). Fica em `publicador_tiktok/`. Detalhes e passo a passo em
[publicador_tiktok/README.md](publicador_tiktok/README.md).
