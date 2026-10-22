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

## Fluxo autônomo pelo chat (Claude Code na nuvem)

Para editar sem abrir o Codespace: numa sessão do Claude Code com este repositório, anexe os vídeos brutos e peça o Reels.
O Claude pergunta só o essencial, monta com o Estúdio de Reels, devolve o MP4 no chat e gera uma nova versão a cada pedido
de alteração. O briefing, os planos e o histórico ficam em `estudio_reels_memoria/` para retomar em outra sessão (os vídeos
precisam ser anexados de novo). Detalhes em
[`.claude/skills/reels-creative-director/references/fluxo-autonomo.md`](.claude/skills/reels-creative-director/references/fluxo-autonomo.md).
