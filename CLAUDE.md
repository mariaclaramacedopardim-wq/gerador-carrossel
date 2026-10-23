# Instruções do repositório

## Fontes

As fontes da marca/projeto ficam em `fonts/` (catálogo em `fonts/README.md` e `fonts/fonts.json`, `@font-face` em `fonts/fonts.css`). Em qualquer criação com texto (design, carrossel, vídeo, Reel, thumbnail, legendas), escolha as fontes dessa pasta antes de recorrer a fontes externas. Texto em português: não use Career Path, Eunomia nem Penna (não têm acentos).

## Aprovação visual antes da produção (obrigatório, em qualquer sessão)

Em toda tarefa de design de imagens ou edição de vídeo, antes de gastar tokens ou tempo na produção final:

1. Gere um wireframe (design de imagem) ou imagens-chave/storyboard (edição de vídeo): quadros representativos do look, da tipografia, do layout e dos clipes escolhidos.
2. Apresente ao usuário e PARE. Espere aprovação explícita do caminho.
3. Só depois produza o resultado final (render completo, exportações, masterização). Se o usuário mudar a direção visual, gere novos quadros e peça aprovação de novo.

Correções técnicas (bug, tipo, loudness) não exigem nova aprovação.

## B-rolls do Pexels (obrigatório quando aplicável)

Em edições de vídeo que usem imagens de apoio (b-roll), use como fonte preferencial o Pexels (vídeos, filtro vertical/portrait para Reels).
1. Antes de buscar, teste se `pexels.com`/`api.pexels.com`/`videos.pexels.com` estão acessíveis. Se houver chave de API (`PEXELS_API_KEY`), use a API oficial de vídeos.
2. Se o Pexels estiver bloqueado, avise o usuário logo, diga qual domínio precisa ser liberado e use Pixabay (via conector Orshot) como alternativa, dizendo que não é Pexels.
3. Registre no relatório, para cada clipe: fonte, autor, ID e licença. Siga a regra de aprovação visual (quadros-chave antes da produção final).
