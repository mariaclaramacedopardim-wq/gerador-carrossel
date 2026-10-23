"""Legenda, hashtags e opções de cada vídeo, lidas de um .json ao lado do MP4 (mesmo nome base)."""

import json

from . import config


class ErroMetadados(Exception):
    pass


def _tamanho_utf16(texto):
    return len(texto.encode("utf-16-le")) // 2


def _normalizar_hashtags(valor):
    if isinstance(valor, str):
        valor = valor.split()
    resultado = []
    for item in valor or []:
        item = str(item).strip()
        if item:
            resultado.append(item if item.startswith("#") else "#" + item)
    return resultado


def ler(texto_json, padroes=None):
    """Interpreta o .json do vídeo (ou None se ele não existir) e devolve as opções já com os padrões."""
    padroes = padroes if padroes is not None else config.carregar_padroes()
    bruto = {}
    if texto_json:
        try:
            bruto = json.loads(texto_json)
        except json.JSONDecodeError as erro:
            raise ErroMetadados(f"O arquivo de legenda não é um JSON válido ({erro.msg}).") from erro
        if not isinstance(bruto, dict):
            raise ErroMetadados("O arquivo de legenda precisa ser um objeto JSON.")

    legenda = str(bruto.get("legenda", padroes.get("legenda_padrao", ""))).strip()
    hashtags = _normalizar_hashtags(bruto.get("hashtags", padroes.get("hashtags_padrao", [])))
    titulo = "\n".join(parte for parte in (legenda, " ".join(hashtags)) if parte)
    if _tamanho_utf16(titulo) > config.LIMITE_LEGENDA:
        raise ErroMetadados(f"A legenda com hashtags passa de {config.LIMITE_LEGENDA} caracteres.")

    return {
        "titulo": titulo,
        "privacidade": str(bruto.get("privacidade", config.PRIVACIDADE_PADRAO)),
        "ia": bool(bruto.get("ia", False)),
        "comentarios": bool(bruto.get("comentarios", True)),
        "duet": bool(bruto.get("duet", True)),
        "stitch": bool(bruto.get("stitch", True)),
        "capa_ms": int(bruto.get("capa_ms", 1000)),
        "conteudo_de_marca": bool(bruto.get("conteudo_de_marca", False)),
        "promocao_propria": bool(bruto.get("promocao_propria", False)),
    }
