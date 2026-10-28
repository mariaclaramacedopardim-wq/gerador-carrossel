"""Gera as imagens 4:5 (1080x1350) com foto de fundo + título, no estilo dos posts de frase do Pinterest.

Uso: python3 gerar_imagens.py <pasta_com_fotos> <pasta_saida>
Cada foto precisa se chamar NN.jpg (NN = número do conceito em CONCEITOS).
"""
import os
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

LARGURA, ALTURA = 1080, 1350
FONTE = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"

# número: (título, escurecimento 0-1, alinhamento vertical 0-1)
CONCEITOS = {
    1: ("às vezes o plano é só dirigir até a vontade de fugir passar", 0.50, 0.40),
    2: ("cresce na direção de quem te dá luz", 0.52, 0.42),
    3: ("meu maior projeto de vida é dormir até o problema se resolver sozinho", 0.40, 0.50),
    4: ("nem toda calmaria é paz. às vezes o mar só tá recuando pra voltar maior", 0.42, 0.42),
    5: ("minha personalidade é 30% café e 70% ansiedade bem disfarçada", 0.55, 0.45),
    6: ("a chuva lava a rua inteira e ninguém inventou nada pra lavar a cabeça", 0.50, 0.45),
    7: ("todo dia o sol vai embora e volta. você só tá no intervalo", 0.38, 0.40),
    8: ("li tanto sobre o amor que só faltou viver", 0.50, 0.45),
    9: ("me encontrei quando parei de me procurar nos outros", 0.45, 0.45),
    10: ("acordar cedo é um ato de fé que meu corpo não assinou", 0.45, 0.45),
    11: ("a vista só é bonita porque a subida foi um inferno", 0.40, 0.40),
    12: ("crescer dói, mas nenhuma planta se arrependeu de virar árvore", 0.42, 0.42),
    13: ("somos feitos de estrelas e mesmo assim eu me preocupo com o que ele pensa", 0.40, 0.42),
    14: ("ninguém avisa que crescer é se despedir de lugares que ainda moram em você", 0.45, 0.42),
    15: ("flor que nasce no asfalto não pediu permissão", 0.42, 0.42),
    16: ("meu relacionamento mais estável é com o delivery", 0.50, 0.45),
    17: ("seja farol. não fique procurando navio", 0.45, 0.42),
    18: ("o que passou virou foto. foto a gente guarda, não mora", 0.45, 0.45),
    19: ("tem dias que o único progresso é ter levantado da cama", 0.42, 0.42),
    20: ("a cidade nunca dorme e eu durmo mal em solidariedade", 0.48, 0.42),
}


def preencher(img, w, h):
    """Corta no centro para preencher w x h (object-fit: cover)."""
    escala = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def quebrar(draw, texto, fonte, largura_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return linhas


def gerar(foto, titulo, escuro, pos_y, saida):
    img = preencher(Image.open(foto).convert("RGB"), LARGURA, ALTURA)
    img = ImageEnhance.Color(img).enhance(0.85)
    img = ImageEnhance.Brightness(img).enhance(1 - escuro)
    # vinheta leve para dar clima e garantir leitura
    vinheta = Image.new("L", (LARGURA, ALTURA), 0)
    ImageDraw.Draw(vinheta).ellipse((-250, -150, LARGURA + 250, ALTURA + 150), fill=255)
    vinheta = vinheta.filter(ImageFilter.GaussianBlur(220))
    img = Image.composite(img, ImageEnhance.Brightness(img).enhance(0.55), vinheta)

    draw = ImageDraw.Draw(img)
    tamanho = 74
    while True:
        fonte = ImageFont.truetype(FONTE, tamanho)
        linhas = quebrar(draw, titulo, fonte, 780)
        if len(linhas) <= 5 or tamanho <= 54:
            break
        tamanho -= 4
    passo = round(tamanho * 1.2)
    altura_bloco = passo * len(linhas)
    y = round((ALTURA - altura_bloco) * pos_y)

    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sombra)
    for i, linha in enumerate(linhas):
        x = (LARGURA - sd.textlength(linha, font=fonte)) / 2
        sd.text((x, y + i * passo + 4), linha, font=fonte, fill=(0, 0, 0, 170))
    sombra = sombra.filter(ImageFilter.GaussianBlur(8))
    img = Image.alpha_composite(img.convert("RGBA"), sombra)
    draw = ImageDraw.Draw(img)
    for i, linha in enumerate(linhas):
        x = (LARGURA - draw.textlength(linha, font=fonte)) / 2
        draw.text((x, y + i * passo), linha, font=fonte, fill=(255, 255, 255, 255))
    img.convert("RGB").save(saida, quality=92)


if __name__ == "__main__":
    fotos, saida = sys.argv[1], sys.argv[2]
    os.makedirs(saida, exist_ok=True)
    for n, (titulo, escuro, pos) in CONCEITOS.items():
        foto = os.path.join(fotos, f"{n:02d}.jpg")
        if os.path.exists(foto):
            gerar(foto, titulo, escuro, pos, os.path.join(saida, f"{n:02d}.jpg"))
            print("ok", n)
