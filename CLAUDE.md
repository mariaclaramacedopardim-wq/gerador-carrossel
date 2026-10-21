# Instruções para o Claude

## Quem usa e como falar
- Quem usa este projeto é iniciante em programação e trabalha pelo **iPad**, com GitHub Codespaces e o app do Claude.
- Responda sempre em **português simples**, sem jargão. Quando um termo técnico for inevitável, explique em uma frase.
- Antes de alterar arquivos, diga o que vai mudar. Trabalhe em um ramo separado e abra um pull request; não envie direto para o `main`.

## O projeto
O editor é um site estático em HTML, CSS e JavaScript puros, sem frameworks, sem build e sem dependências. Mantenha assim.

- `js/data.js`: estilos (`STYLES`), paletas, fontes, layouts e a criação de marcas e carrosséis.
- `js/render.js`: desenha os slides no `<canvas>` de 1080 × 1350. A mesma função serve para a tela e para o PNG.
- `js/app.js`: interface, com as abas Slide, Marca e Carrosséis, a cópia de segurança e a exportação.
- `js/roteiro.js`: converte o roteiro colado em slides.
- `js/storage.js`: textos no `localStorage` (chave `carrossel-estudio:v2`) e imagens no IndexedDB.
- Comentários e textos da interface em português, no mesmo tom dos arquivos existentes.
- Fonte nova: adicione em `js/data.js` **e** no `<link>` do Google Fonts em `index.html`.

Para testar, sirva a pasta com `python3 -m http.server 8000` e abra no navegador. Não há testes automatizados.

## Criar uma marca nova
Quando pedirem uma marca (ex.: "uma marca para uma confeitaria, tom acolhedor"):
1. Proponha um estilo (`editorial`, `minimalista`, `impacto` ou `leve`), 4 cores e um par de fontes que existam em `js/data.js`. Explique a escolha em poucas linhas.
2. Verifique o contraste: `text` sobre `bg` precisa ser bem legível (pelo menos 4,5:1), e `accent` precisa aparecer sobre `bg`.
3. Com aprovação, adicione a marca em `marcas/catalogo.json` (formato no README). Ela aparece no editor, aba **Marca**, em **Marcas prontas do projeto**.
4. Se houver descrição de público e tom de voz, guarde em `marcas/<nome-da-marca>.md` para orientar os textos futuros.

## Escrever um carrossel
Entregue o texto no formato de roteiro, pronto para colar na aba **Carrosséis**:

```
# capa
Chamada: ...
Título: ... com *destaque*
Texto: ...

# texto
Chamada: 01
Título: ...
Texto: ...

# final
Título: ...
Texto: ...
```

- Layouts: `capa`, `texto`, `citação`, `imagem`, `final`. Use `imagem` só quando houver uma foto para o slide.
- Títulos curtos (até ~8 palavras), um destaque com `*asteriscos*` por título no máximo, textos de 1 a 3 frases.
- Entre 5 e 10 slides: capa → conteúdo numerado (01, 02…) → final com chamada para ação.
- Se existir `marcas/<marca>.md`, siga o tom de voz descrito lá.
- Entregue o roteiro num bloco de código, para facilitar copiar no iPad.

## Canva
A conta tem **Canva Pro**, e o Canva é usado junto com o editor:
- **Editor → Canva:** os PNGs exportados vão para o Canva pelo app (Uploads) para os retoques.
- **Direto no Canva:** com o conector do Canva ligado em claude.ai, dá para listar os kits de marca, criar designs a partir de modelos, preencher com os textos do roteiro e exportar.
  - Use o tamanho 1080 × 1350 px.
  - Use as cores e fontes da marca (veja `marcas/catalogo.json`), para os dois caminhos darem o mesmo resultado.
  - As fotos precisam estar no Canva (Uploads) ou ser enviadas na conversa.
- Sempre confirme antes de criar, alterar ou exportar designs na conta do Canva.
