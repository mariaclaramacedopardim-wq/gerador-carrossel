# Estúdio de Carrosséis

Editor de carrosséis para Instagram, feito para funcionar bem no iPad. Ele guarda **várias marcas**, cada uma com seu estilo, cores, fontes, @ e logo, e **vários carrosséis**. Cada slide sai em **PNG de 1080 × 1350 px**, o formato retrato 4:5 do Instagram.

É feito com HTML, CSS e JavaScript puros: não precisa instalar nada nem "compilar".

## Como usar

### 1. Crie a marca (aba **Marca**)
1. Toque em **Nova marca** e dê um nome.
2. Escolha um **estilo**:
   - **Editorial**: serifas e itálicos, cara de revista.
   - **Minimalista**: limpo, muito respiro.
   - **Impacto**: caixa-alta e destaques fortes.
   - **Leve**: amigável, com marca-texto.

   O estilo já sugere cores e fontes.
3. Ajuste a **paleta**, as **cores**, as **fontes**, o seu **@** e o **logo**. Logo em PNG com fundo transparente fica melhor.

Tudo o que você muda na marca vale para todos os slides dos carrosséis dela.

### 2. Monte o carrossel (aba **Slide**)
1. Escolha um slide nas miniaturas e edite a chamada, o título e o texto.
2. Palavras entre `*asteriscos*` viram destaque. O jeito do destaque (itálico, cor, caixa ou marca-texto) depende do estilo.
3. Escolha o layout: **Capa**, **Texto**, **Citação**, **Imagem** ou **Final**. Nos layouts com foto, toque em **Escolher foto**.

### 3. Ou cole um roteiro (aba **Carrosséis**)
Peça ao Claude um roteiro neste formato, cole em **Colar roteiro** e toque em **Criar carrossel com o roteiro**:

```
# capa
Chamada: Café em casa
Título: 3 erros que estragam o seu *café*
Texto: E como evitar cada um

# texto
Chamada: 01
Título: Água *fervendo*
Texto: Use água entre 90 e 96 °C.

# citação
Citação: O café é a bebida da conversa.
Autor: Alguém

# final
Título: Salve para o *próximo* café
```

Cada slide começa com `#` e o layout. Os rótulos aceitos são:
- **Chamada**
- **Título** (na citação também vale **Citação**)
- **Texto** (na capa também vale **Subtítulo**; na citação, **Autor**)

### 4. Exporte
Toque em **Exportar todos** e depois em **Salvar no iPad / Compartilhar** para mandar as imagens ao app Fotos.

### 5. Canva (opcional)
Para retocar no Canva, envie as imagens exportadas pelo app do Canva (**Uploads**). Você também pode pedir ao Claude para criar o carrossel direto no Canva, com o conector do Canva ligado em claude.ai. Os detalhes estão em [CLAUDE.md](CLAUDE.md).

## Onde ficam os dados

- Marcas, carrosséis e fotos ficam salvos **no navegador do aparelho**, não no GitHub.
- Cada endereço guarda os seus dados separados. O endereço do Codespaces e o do GitHub Pages, por exemplo, são "lugares" diferentes.
- O Safari pode apagar dados de sites pouco usados. Por isso:
  - toque em **Salvar cópia** (aba **Carrosséis**) de vez em quando; o arquivo vai para o app Arquivos;
  - para levar tudo a outro aparelho ou endereço, use **Restaurar cópia**;
  - adicionar o site à Tela de Início do iPad (Compartilhar → **Adicionar à Tela de Início**) ajuda a manter os dados.

## Marcas prontas do projeto

O arquivo [`marcas/catalogo.json`](marcas/catalogo.json) pode trazer marcas prontas. Elas aparecem na aba **Marca** com o botão **Adicionar**, em qualquer aparelho. Exemplo de item:

```json
[
  {
    "name": "Padaria Sol",
    "styleId": "minimalista",
    "colors": { "bg": "#FFF8E7", "text": "#3B2A1A", "muted": "#8A7560", "accent": "#E09F3E" },
    "titleFontId": "bricolage",
    "bodyFontId": "dmsans",
    "handle": "@padariasol"
  }
]
```

Os códigos de estilo, paleta e fonte estão em [`js/data.js`](js/data.js).

## Abrir o editor

### No GitHub Codespaces (para testar mudanças)
No terminal do Codespace, rode:

```
python3 -m http.server 8000
```

Toque em **Abrir no navegador** no aviso que aparecer. Se o aviso não aparecer, abra a aba **Portas** e toque no globo ao lado da porta 8000.

Abrir o `index.html` direto não funciona: os arquivos JavaScript são módulos e precisam de um servidor.

### No GitHub Pages (para usar no dia a dia)
1. No GitHub, abra **Settings → Pages**.
2. Em **Source**, escolha **Deploy from a branch**.
3. Selecione o ramo `main` e a pasta `/ (root)` e salve.

Em alguns minutos o editor fica disponível em `https://<seu-usuário>.github.io/gerador-carrossel/`.

## Estrutura

```
index.html          → estrutura da página
css/style.css       → aparência do editor
js/data.js          → estilos, paletas, fontes, layouts, marcas e o exemplo
js/render.js        → desenho de cada slide no <canvas> (usado na tela e no PNG)
js/app.js           → interação: edição, marcas, carrosséis, cópia e exportação
js/roteiro.js       → transforma o roteiro colado em slides
js/storage.js       → salva no aparelho (textos no localStorage, fotos no IndexedDB)
marcas/catalogo.json → marcas prontas que aparecem no editor
CLAUDE.md           → instruções para o Claude ajudar neste projeto
```
