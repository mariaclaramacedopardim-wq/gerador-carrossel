---
name: original-web-designer
description: Cria sites e apps de página única (HTML) para a Maria, com ilustrações geradas no Canva, fontes incomuns e layout e estética escolhidos conforme o tema e a função do site.
---

# Sites no estilo Canva

Esta skill cria sites de uma página só (um arquivo `.html`) no mesmo padrão do "Caderno da Maria", o site de estudos de medicina: funciona no celular e no computador, salva tudo no navegador com backup, usa figuras geradas no Canva e fontes fora do comum, e não tem cara de site feito por IA.

A regra central: **cada site novo tem layout e estética próprios**, escolhidos pelo tema e pela função. O que se repete entre os sites é a qualidade e a técnica, nunca a aparência.

## Quando usar

Sempre que a Maria pedir um site, app, painel, planner, tracker, página pessoal, ferramenta ou "algo parecido com o meu caderno" para qualquer finalidade: finanças, treino, receitas, leitura, viagem, plantões, consultório, casamento, portfólio, etc.

## Fluxo de trabalho

1. **Entender a função.** O que a pessoa vai fazer no site (registrar, consultar, planejar, mostrar para outros, estudar)? Quais dados precisam ficar salvos? Se faltar algo essencial, faça no máximo uma pergunta; senão, decida e diga o que decidiu.
2. **Escolher a direção.** Escolha um arquétipo de layout (seção "Layouts por função") e uma estética (seção "Estéticas por tema"). A combinação tem que ser diferente das dos sites que ela já tem (veja "Sites que já existem").
3. **Mostrar opções antes de construir tudo.** A Maria gosta de escolher. Monte 2 ou 3 direções curtas (nome da estética, layout, par de fontes, paleta, que figuras do Canva entram) e peça a escolha num cartão de decisão, recomendando uma. Enquanto ela não responde, adiante a recomendada.
4. **Gerar as figuras no Canva** (seção "Ilustrações do Canva").
5. **Construir o HTML** seguindo a "Base técnica" e a seção "Salvar e backup".
6. **Testar e tirar prévias** com Playwright: computador (1440×900), celular (390×844) e modo escuro. Confira que não há rolagem lateral, texto cortado ou figura pixelada. Anexe as prévias.
7. **Ajustar com ela** e só publicar quando ela aprovar.
8. **Publicar** (seção "Publicação").

## Sem cara de IA (regras fixas)

Estas regras vêm do que a Maria já recusou no caderno. Valem para todo site:

- **Nada de caixinhas arredondadas iguais** repetidas pela página inteira. Separe seções por réguas finas, espaço, colunas, recortes, fichas, molduras ou blocos de cor com formatos diferentes.
- **Nada de menu lateral padrão de aplicativo** com ícone + rótulo em lista. Use abas de divisória, índice numerado, barra inferior desenhada, menu em fita, sumário de revista, botões-carimbo, etc., conforme a estética.
- **Nada de etiquetas em pílula colorida.** Prefira versalete, sublinhado, marca-texto, carimbo, número.
- **Nada de gráfico de rosca nem anel de porcentagem.** Use números grandes na fonte de título com barras finas, réguas com marca de meta, tabelas tipográficas, pontos ou tracinhos.
- **Nada de ícones prontos de biblioteca** (Lucide, Heroicons, Material, Font Awesome) nem emoji como ícone. Os ícones são figuras do Canva ou desenhos SVG próprios no estilo da estética.
- **Nada de frases de enfeite**: sem citação do dia, sem "Você está indo muito bem!", sem subtítulo explicando cada aba, sem linhas de "Referência". Texto só onde ajuda a usar o site.
- **Nada de gradiente roxo-azul, glassmorphism genérico ou fundo com bolhas desfocadas.**
- **Fontes proibidas como principais**: Inter, Roboto, Poppins, Montserrat, Nunito, Manrope, Open Sans, Lato, Raleway, Space Grotesk, Outfit, Playfair Display, system-ui. São as fontes "clássicas de IA".
- **Enfeites só se combinarem com o tema.** No caderno de medicina ela pediu para tirar laços, cerejas e detalhes femininos e preferiu algo "chique e clean". Não presuma estética fofa porque o site é dela.
- **Detalhes artesanais dão vida**: textura de papel, carimbo levemente torto, post-it com fita, número grande vazado, uma fonte manuscrita só para anotações pessoais. Use 2 ou 3 por site, não todos. Ela achou o caderno "sem sal" quando ficou minimalista demais e pediu "um pouco menos minimal" depois.

## Estéticas por tema

Escolha uma e adapte. Cada uma traz par de fontes, paleta, texturas e o estilo de prompt das figuras do Canva. Todas as fontes listadas existem no Canva e no Google Fonts, então podem ser carregadas no site pelo link do Google Fonts.

| Estética | Combina com | Títulos / texto / detalhe | Paleta | Figuras do Canva | Detalhes |
|---|---|---|---|---|---|
| **Papelaria editorial** (a do caderno) | estudos, planners, diários | Instrument Serif / Schibsted Grotesk / Caveat | papel rosado, vinho, rosa-chá | gravura antiga em traço fino, uma cor | abas de divisória, furos de fichário, carimbo, papel milimetrado |
| **Gabinete de curiosidades** | coleções, leitura, botânica, ciência | Gloock ou Young Serif / Literata / IM Fell English | creme envelhecido, verde-musgo, ferrugem, tinta sépia | prancha científica, aquarela de herbário, litografia | molduras finas, legendas numeradas, etiquetas de museu |
| **Recibo e balcão** | finanças, compras, orçamento, controle de gastos | Space Mono ou DM Mono / Familjen Grotesk / Courier Prime | papel térmico, preto, um vermelho de carimbo | objetos em xilogravura, risografia de 2 cores | borda serrilhada, linhas pontilhadas, total sublinhado duas vezes |
| **Pôster suíço** | treino, metas, hábitos, produtividade | Big Shoulders Display ou Anton / Archivo / Archivo Narrow | branco, preto e uma cor forte (laranja, verde-ácido ou azul cobalto) | formas geométricas, silhuetas recortadas em papel colorido | grade visível, números gigantes, texto girado 90° |
| **Revista de viagem** | viagens, roteiros, lugares, restaurantes | Bodoni Moda ou DM Serif Display / Newsreader / Italiana | azul-mar, areia, terracota | selos postais, cartões-postais em guache, mapas ilustrados | carimbos de passaporte, legenda em itálico, fotos tortas com fita |
| **Cozinha de vó** | receitas, cardápio, mercado | Fraunces (ótico, macio) / Gelasio / Gaegu | manteiga, tomate, verde-oliva, azul de azulejo | ingredientes em guache, azulejo português, ilustração de livro de receitas antigo | fichas de receita, toalha xadrez só em detalhe, borda de azulejo |
| **Consultório sóbrio** | medicina profissional, pacientes, plantões, escalas | Libre Caslon Display / Hanken Grotesk / IBM Plex Mono | branco-gelo, verde-hospital acinzentado, grafite, um coral | gravura anatômica em traço fino, instrumentos antigos | réguas de prontuário, campos com linha de assinatura, numeração de ficha |
| **Clube noturno / vinil** | música, playlists, eventos, festas | Climate Crisis ou Unbounded / Bricolage Grotesque / Rubik Mono One | preto profundo, um neon (rosa ou verde) e cromado | capas de disco em risografia, colagem com meio-tom | grão de filme, texto em círculo, ingressos destacáveis |
| **Jardim japonês** | meditação, sono, autocuidado, rotina calma | Shippori Mincho / Zen Kaku Gothic New / Klee One | papel washi, carvão, vermelho de selo hanko | sumi-e (pincel a tinta), ondas em ukiyo-e | muito espaço vazio, selo vermelho quadrado, linhas verticais |
| **Ateliê / portfólio** | portfólio, trabalhos, apresentação pessoal | Syne ou Cormorant Garamond / Instrument Sans / Reenie Beanie | branco quente, preto e uma cor de assinatura | recortes de papel estilo Matisse, colagem | assimetria, legendas pequenas de galeria, assinatura manuscrita |

Se nenhuma servir, crie uma nova com a mesma estrutura (fontes, paleta, figuras, detalhes) e dê um nome a ela. Para achar fontes incomuns que combinem, você pode usar a ferramenta de recomendação de fontes, filtrando o que também existir no Google Fonts.

Regras de tipografia: no máximo três famílias (título, texto, detalhe). A fonte de detalhe (manuscrita, máquina de escrever ou mono) aparece pouco. Tamanho base de texto entre 15 e 17 px. Títulos com `text-wrap: balance`.

## Layouts por função

Escolha pelo que a pessoa faz no site, não pelo tema.

| Função | Arquétipo de layout | Como fica |
|---|---|---|
| Registrar coisas todo dia (hábitos, gastos, treinos) | **Livro-caixa** | uma página longa com o dia de hoje no topo em destaque, lançamento rápido e o histórico em tabela tipográfica embaixo |
| Planejar no tempo (estudos, viagem, casamento) | **Linha do tempo / cronograma** | eixo vertical no celular e horizontal no computador, com marcos, hoje marcado e próximos passos |
| Consultar e colecionar (receitas, livros, filmes) | **Fichário / catálogo** | grade irregular de fichas com tamanhos diferentes (masonry), filtro por índice alfabético ou por cor, ficha abre em página inteira |
| Acompanhar números (finanças, peso, metas) | **Relatório editorial** | manchete com o número principal, colunas como jornal, barras finas, comparação com o mês anterior em texto |
| Estudar e revisar (flashcards, simulados) | **Caderno com abas** | abas de divisória para as seções, a carta ou questão ocupando o centro, progresso em régua |
| Mostrar para outros (portfólio, convite, página pessoal) | **Revista / pôster** | abertura grande com figura do Canva, seções em ritmo de páginas de revista, rolagem com momentos de pausa |
| Organizar tarefas (casa, plantões, escalas) | **Quadro de cortiça / kanban artesanal** | colunas como quadros, tarefas como bilhetes presos com alfinete ou fita, arrastar no computador e tocar para mover no celular |
| Rotina guiada (meditação, treino passo a passo, receita em execução) | **Uma coisa por vez** | tela cheia com um passo grande, avançar e voltar, cronômetro desenhado |
| Ferramenta de cálculo (doses, orçamento, conversões) | **Bancada** | formulário à esquerda, resultado grande à direita (empilha no celular), histórico de cálculos embaixo |
| Painel de várias áreas | **Mesa de trabalho** | objetos na "mesa" levam às seções (agenda, caderno, pasta), cada um desenhado no Canva |

Em todos: no celular, navegação na parte de cima ou de baixo com área de toque de pelo menos 44 px, margens laterais de 16 px, sem rolagem lateral.

## Ilustrações do Canva

As figuras são o que mais diferencia o site. Use sempre o Canva para gerar ícones, figura de abertura, ilustrações de seções vazias e enfeites.

1. **Defina um sufixo de estilo único** para o site inteiro e use em todos os prompts, para as figuras parecerem da mesma mão. Exemplo para "Consultório sóbrio": `gravura antiga em traço fino, uma única cor grafite, fundo branco liso, sem texto, sem sombra, centralizado, estilo prancha de anatomia do século XIX`.
2. **Ícones com significado literal da função**, não anatômicos por obrigação. No caderno, a Maria preferiu "flashcard = maço de fichas, agenda = agenda de couro, simulado = prova com lápis, backup = envelope com lacre".
3. **Gere com `generate-image`** (formato `SQUARE_1_1` para ícones, `LANDSCAPE_16_9` ou `PORTRAIT_4_5` para abertura). Gere um por vez ou em paralelo e acompanhe com `get-generate-image-job` quando não houver widget. Peça "fundo branco liso" para facilitar o recorte.
4. **Recorte o fundo** com `remove-background` usando o `media_id` do resultado, quando a figura for ficar sobre papel ou cor.
5. **Baixe a imagem** pelo link do resultado. Se não houver link direto, coloque a figura num design (`create-design`) e use `export-design` em PNG com `transparent_background: true`.
6. **Otimize e embuta**: com Pillow, redimensione (ícones 256 px, aberturas até 1200 px de largura), salve em WebP com qualidade 80 e embuta como `data:image/webp;base64,...` no HTML. Assim o site continua sendo um arquivo só. Mantenha o HTML final abaixo de 2 MB.
7. **No modo escuro**, ícones de traço escuro somem. Resolva com `filter: invert(1) hue-rotate(180deg)` só nas figuras de traço, ou gere uma versão clara.
8. Guarde os PNGs originais em `/mnt/project-files/<nome-do-site>/figuras/` para reaproveitar.

Se o Canva não estiver conectado, avise a Maria e ofereça reconectar. Não troque as figuras por ícones de biblioteca sem ela concordar.

## Base técnica

- Um único `index.html` com CSS e JS dentro. Sem frameworks; JavaScript simples. Bibliotecas só se forem realmente necessárias (por exemplo, um gráfico específico), por CDN com versão fixa.
- Cabeçalho: `lang="pt-BR"`, `viewport` com `viewport-fit=cover`, `theme-color`, `apple-mobile-web-app-capable`, `apple-mobile-web-app-title` curto e um favicon próprio (SVG ou PNG do Canva), para ela poder pôr o site na tela de início do iPhone.
- Cores em variáveis no `:root`, com modo escuro em `@media (prefers-color-scheme: dark)` e também por `[data-theme]` para um botão de alternar tema. O modo escuro mantém a estética (papel vira papel escuro, não cinza genérico).
- Respeitar `env(safe-area-inset-*)` no topo e embaixo.
- Navegação entre seções por hash (`#inicio`, `#registros`) para o botão voltar funcionar.
- Acessível: contraste suficiente, `button` de verdade nos botões, `aria-current` na seção ativa, `prefers-reduced-motion` desliga animações.
- Datas e números em português (`toLocaleDateString('pt-BR')`, `Intl.NumberFormat('pt-BR')`, R$ quando for dinheiro).

## Salvar e backup

Todo site que guarda dados usa este padrão:

```js
const KEY = 'nome-do-site-v1';
const blank = () => ({ v: 1, criadoEm: new Date().toISOString(), lastBackup: null, /* dados */ });
let S;
try { S = JSON.parse(localStorage.getItem(KEY)) || blank(); } catch { S = blank(); }
function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch { toast('Não consegui salvar neste navegador.'); } }
```

- Salve a cada alteração, sem botão "salvar".
- Se o formato dos dados mudar, suba `v` e escreva uma migração que preserve os dados antigos. Nunca apague dados de quem já usa.
- Tenha uma seção **Backup** com:
  - **Baixar backup**: gera `backup-<site>-AAAA-MM-DD.json` e marca `S.lastBackup`.
  - **Copiar backup**: copia o JSON para a área de transferência (no iPhone, baixar às vezes não funciona).
  - **Restaurar**: aceita arquivo ou texto colado, valida antes, pede confirmação e substitui.
  - Aviso discreto quando o último backup tiver mais de 7 dias.
- Diga em uma linha, na própria seção, que os dados ficam só neste navegador e neste aparelho.

## Textos

- Português do Brasil, frases curtas, tom direto, sem exclamação em excesso.
- Rótulos dizem o que o botão faz ("Lançar gasto", "Virar carta"), nunca "Enviar" ou "OK".
- Estados vazios com uma figura do Canva e uma frase dizendo o primeiro passo.
- Sem citações, frases motivacionais ou referências bibliográficas, a menos que ela peça.

## Sites que já existem

Não repita estas combinações. Ao criar um site novo, acrescente ele aqui na próxima vez que a skill for atualizada.

- **Caderno da Maria** (estudos de medicina): papelaria editorial, rosa-vinho, Instrument Serif + Schibsted Grotesk + manuscrita, abas de divisória, folha de fichário com furos, carimbos vinho com anel duplo como ícones, papel milimetrado na faixa do dia. Publicado em `gerador-carrossel/caderno` no GitHub Pages.

## Publicação

- Entregue o HTML em `/mnt/project-files/<nome-do-site>/index.html` com as prévias em `/mnt/project-files/<nome-do-site>/visual/`.
- Para pôr no ar, o padrão é o GitHub Pages do repositório `gerador-carrossel`, numa pasta própria (`gerador-carrossel/<nome-do-site>/`), por pull request. Explique o clique de **Merge pull request** e **Confirm merge**, ou faça o merge se ela pedir.
- Depois de publicado, diga o link e como forçar a atualização: no Safari do iPhone, puxar a página para baixo ou fechar e abrir a aba; no atalho da tela de início, fechar o app e abrir de novo; no computador, Ctrl+Shift+R (Cmd+Shift+R no Mac). O GitHub pode mostrar a versão antiga por até 10 minutos.
