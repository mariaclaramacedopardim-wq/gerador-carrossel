# Carrossel Editorial

Gerador de carrosséis para Instagram com tipografia editorial, feito com HTML, CSS e JavaScript puros, sem frameworks e sem etapa de build.

Cada slide sai em **PNG de 1080 × 1350 px** (formato retrato 4:5 do Instagram).

## Como usar

1. Escolha um slide nas miniaturas e edite a chamada, o título e o texto no painel **Slide**.
2. Para destacar palavras do título em itálico com a cor de destaque, escreva-as entre `*asteriscos*`.
3. Troque o layout (Capa, Texto, Citação, Imagem ou Final) e, nos layouts com foto, escolha uma imagem.
4. Na aba **Estilo**, escolha paleta, cores, fontes e o seu @.
5. Toque em **Exportar todos**. No iPad, use **Salvar no iPad / Compartilhar** para mandar as imagens ao app Fotos.

O projeto fica salvo automaticamente no navegador do aparelho.

## Estrutura

```
index.html      → estrutura da página
css/style.css   → aparência do editor
js/data.js      → paletas, fontes, layouts e o carrossel de exemplo
js/render.js    → desenho de cada slide no <canvas> (usado na tela e no PNG)
js/app.js       → interação: edição, miniaturas, salvamento e exportação
```

## Rodar localmente

Os arquivos JavaScript são módulos, então a página precisa ser servida por um servidor (abrir o `index.html` direto não funciona):

```
npx http-server .
```

Ou publique com o GitHub Pages (Settings → Pages → branch `main`, pasta `/ (root)`).
