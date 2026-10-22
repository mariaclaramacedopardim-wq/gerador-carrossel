"""Acesso ao FFmpeg/FFprobe e mensagens de erro amigáveis."""

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from . import config


class ErroEstudio(Exception):
    """Erro com mensagem pensada para a usuária (em português simples)."""

    def __init__(self, mensagem, detalhe=""):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhe = detalhe


class ErroEspaco(ErroEstudio):
    pass


def verificar_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ErroEstudio(
            "O FFmpeg não está instalado neste Codespace. "
            "Rode a tarefa 'Reels: instalar dependências' (ou o comando bash estudio_reels/instalar.sh)."
        )


@lru_cache(maxsize=1)
def filtros_disponiveis():
    verificar_ffmpeg()
    saida = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True
    ).stdout
    nomes = set()
    for linha in saida.splitlines():
        partes = linha.split()
        if len(partes) >= 3 and "->" in partes[2]:
            nomes.add(partes[1])
    return nomes


def tem_filtro(nome):
    try:
        return nome in filtros_disponiveis()
    except ErroEstudio:
        return False


def espaco_livre(pasta):
    pasta = Path(pasta)
    while not pasta.exists():
        pasta = pasta.parent
    return shutil.disk_usage(pasta).free


def garantir_espaco(pasta, bytes_necessarios):
    livre = espaco_livre(pasta)
    if livre - bytes_necessarios < config.RESERVA_DISCO:
        livre_mb = livre // (1024 * 1024)
        precisa_mb = (bytes_necessarios + config.RESERVA_DISCO) // (1024 * 1024)
        raise ErroEspaco(
            f"Falta espaço no disco do Codespace: há {livre_mb} MB livres e esta etapa precisa de "
            f"cerca de {precisa_mb} MB. Apague projetos antigos na interface ou use clipes menores (1080p)."
        )


def traduzir_erro_ffmpeg(stderr):
    """Converte o final do log do FFmpeg em uma mensagem compreensível."""
    texto = stderr or ""
    baixo = texto.lower()
    if "no space left on device" in baixo:
        return ErroEspaco("O disco do Codespace ficou cheio durante o processamento. Libere espaço e tente de novo.", texto[-2000:])
    if "invalid data found" in baixo or "moov atom not found" in baixo:
        return ErroEstudio("Um dos arquivos não é um vídeo válido ou está incompleto (o envio pode ter sido interrompido).", texto[-2000:])
    if "decoder" in baixo and ("not found" in baixo or "unknown" in baixo):
        return ErroEstudio("Um dos vídeos usa um formato (codec) que o FFmpeg deste Codespace não consegue ler. Exporte o clipe em H.264 ou HEVC e envie de novo.", texto[-2000:])
    if "no such file or directory" in baixo:
        return ErroEstudio("Um arquivo citado no plano não foi encontrado.", texto[-2000:])
    return ErroEstudio("O FFmpeg não conseguiu processar o vídeo. Veja o detalhe técnico no relatório.", texto[-2000:])


def rodar_ffmpeg(argumentos, timeout=None):
    verificar_ffmpeg()
    comando = ["ffmpeg", "-hide_banner", "-nostdin", "-y", *map(str, argumentos)]
    resultado = subprocess.run(comando, capture_output=True, text=True, timeout=timeout)
    if resultado.returncode != 0:
        raise traduzir_erro_ffmpeg(resultado.stderr)
    return resultado.stderr


def ffprobe_json(caminho):
    verificar_ffmpeg()
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(caminho)],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise ErroEstudio(
            f"Não consegui ler '{Path(caminho).name}'. O arquivo pode estar corrompido, incompleto ou não ser um vídeo.",
            resultado.stderr[-2000:],
        )
    return json.loads(resultado.stdout or "{}")


def encontrar_fonte():
    """Procura uma fonte sem serifa em negrito para os textos na tela."""
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for caminho in candidatos:
        if Path(caminho).exists():
            return caminho
    if shutil.which("fc-match"):
        r = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout and Path(r.stdout).exists():
            return r.stdout
    return None


def estado_do_sistema():
    import os

    estado = {
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "textos_na_tela": tem_filtro("drawtext"),
        "transicoes": tem_filtro("xfade"),
        "conversao_hdr": tem_filtro("zscale") and tem_filtro("tonemap"),
        "fonte": encontrar_fonte(),
        "api_anthropic_configurada": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "espaco_livre_mb": espaco_livre(config.PASTA_DADOS) // (1024 * 1024),
    }
    try:
        import faster_whisper  # noqa: F401

        estado["transcricao"] = True
    except ImportError:
        estado["transcricao"] = False
    try:
        import anthropic  # noqa: F401

        estado["sdk_anthropic"] = True
    except ImportError:
        estado["sdk_anthropic"] = False
    return estado
