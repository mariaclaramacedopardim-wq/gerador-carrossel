# Fontes do projeto

Biblioteca de fontes para usar em qualquer criação de design, vídeo, Reel ou carrossel (HTML/CSS, Remotion, HyperFrames, Pillow, ffmpeg, Canva/Orshot por upload, etc.).

- `fonts.json`: catálogo legível por máquina (família, arquivo, peso, categoria, observações).
- `fonts.css`: `@font-face` pronto de todas as famílias. Em HTML: `<link rel="stylesheet" href="fonts/fonts.css">` e `font-family: 'Fraunces'`.
- Uma pasta por família, com a licença (`OFL.txt`) junto.

## Catálogo

| Família (nome CSS) | Pasta | Estilo | Acentos PT-BR | Observação |
|---|---|---|---|---|
| A Bebedera | `abebedera/` | display, peso 900 | sim | só woff2 (web/Remotion) |
| Brasswell Outline | `brasswell-outline/` | display contorno | sim | |
| Career | `career/` | display | sim | sem –, —, …, ¿ |
| Career Path | `career/` | display contorno | **não** | sem acentos, sem `! # % $` e aspas curvas |
| JFFF Earlysoft | `earlysoft/` | display | sim | |
| Eunomia (Light/Regular/Bold) | `eunomia/` | serifada | **não** | evitar em português |
| Exclusive Editorial | `exclusive-editorial/` | editorial | sim | pacote sem licença: confirmar uso comercial |
| Fraunces (roman + itálico) | `fraunces/` | serifada variável | sim | eixos wght 100–900, opsz, SOFT, WONK |
| Penna | `penna/` | display | **não** | CC0 |
| Perandory / Semi Condensed / Condensed | `perandory/` | display/título | sim | sem … |
| Pinyon Script | `pinyon-script/` | caligráfica | sim | |
| JFFF Puffora | `puffora/` | display | sim | |
| Quiet Folio | `quiet-folio/` | display serifada | sim | |
| Silken | `silken/` | display | sim | |
| Sunny Side | `sunny-side/` | display | sim | |
| JFFF Thornrose | `thornrose/` | display | sim | sem ¿ |
| Valcrest | `valcrest/` | display | sim | |
| Vellune | `vellune/` | display, Black | sim | |

Fontes sem acentos (Career Path, Eunomia, Penna) só servem para texto sem `ã é ç`; para o resto use outra fonte ou combine.

## Uso fora do navegador

Pillow / ffmpeg / Remotion usam os arquivos direto: `ImageFont.truetype("fonts/valcrest/Valcrest-Regular.ttf", 90)`, `drawtext=fontfile=fonts/silken/Silken-Regular.ttf`. No Fraunces variável, ajuste os eixos via `font-variation-settings` (CSS) ou instâncias fixas.

## Licenças

Quase todas são SIL OFL 1.1 (uso comercial permitido, com a licença junto, sem vender a fonte isolada). Penna é CC0. Exclusive Editorial veio sem arquivo de licença.

## Adicionar uma fonte nova

Crie `fonts/<nome-da-familia>/` com os arquivos (ttf/otf/woff2) e a licença, e acrescente a entrada em `fonts.json` e o `@font-face` em `fonts.css`.
