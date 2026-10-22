"""Vídeos sintéticos para testar o estúdio sem usar vídeos pessoais.

São padrões de teste gerados pelo próprio FFmpeg (barras, cores e tons de áudio),
sem nenhuma pessoa ou conteúdo real.
"""

from pathlib import Path

from .ferramentas import rodar_ffmpeg

COMUNS = ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "30"]


def criar_amostras(pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    fala = pasta / "fala_vertical.mp4"
    if not fala.exists():
        # 8 s vertical; muda de imagem aos 4 s (corte de cena); som 0–3 s e 4,5–8 s, silêncio no meio.
        rodar_ffmpeg([
            "-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=30:duration=4",
            "-f", "lavfi", "-i", "smptebars=size=720x1280:rate=30:duration=4",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=1.5",
            "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=3.5",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v];[2:a][3:a][4:a]concat=n=3:v=0:a=1[a]",
            "-map", "[v]", "-map", "[a]", *COMUNS, "-c:a", "aac", "-t", "8", fala,
        ])
    horizontal = pasta / "broll_horizontal.mp4"
    if not horizontal.exists():
        # 5 s horizontal, sem trilha de áudio.
        rodar_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=5", *COMUNS, "-an", horizontal])
    detalhe = pasta / "detalhe_vertical.mp4"
    if not detalhe.exists():
        # 4 s vertical com som contínuo baixo.
        rodar_ffmpeg([
            "-f", "lavfi", "-i", "gradients=size=720x1280:rate=30:duration=4:speed=0.05",
            "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=4",
            "-af", "volume=0.3", *COMUNS, "-c:a", "aac", "-shortest", detalhe,
        ])
    return [fala, horizontal, detalhe]


def criar_projeto_exemplo():
    """Cria um projeto com os vídeos sintéticos, pronto para analisar."""
    import shutil

    from . import config, projetos

    amostras = criar_amostras(config.PASTA_DADOS / "amostras")
    projeto = projetos.criar(
        {
            "objetivo": "Testar o estúdio de ponta a ponta com vídeos sintéticos.",
            "estilo": "Didático e direto.",
            "historia": "Teste do fluxo completo do estúdio. Abre com a fala, mostra o detalhe e fecha.",
            "duracao_alvo_s": 12,
        },
        nome="Exemplo com vídeos sintéticos",
    )
    for origem in amostras:
        shutil.copy2(origem, projetos.pasta(projeto["id"]) / "originais" / origem.name)
        projetos.registrar_clipe(projeto["id"], origem.name)
    lista = [{"arquivo": a.name, "indispensavel": a.name == "fala_vertical.mp4", "descricao": ""} for a in amostras]
    return projetos.atualizar_clipes(projeto["id"], lista)
