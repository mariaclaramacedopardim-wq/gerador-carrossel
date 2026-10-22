"""Transcrição opcional da fala com o pacote faster-whisper (roda no próprio Codespace).

Não vem instalada por padrão: ocupa espaço (o modelo "small" tem cerca de 500 MB)
e deixa a análise mais lenta. Para ativar:  .venv-reels/bin/python -m pip install -r estudio_reels/requirements-transcricao.txt
A transcrição é automática e precisa ser revisada antes de virar legenda.
"""

import json
import os
from pathlib import Path

MODELO = os.environ.get("ESTUDIO_REELS_WHISPER", "small")
_modelo_carregado = None


def disponivel():
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def transcrever(caminho_video, destino_json, idioma="pt"):
    """Retorna {"modelo", "idioma", "segmentos": [{inicio_s, fim_s, texto, palavras}]} ou None."""
    global _modelo_carregado
    if not disponivel():
        return None
    from faster_whisper import WhisperModel

    if _modelo_carregado is None:
        _modelo_carregado = WhisperModel(MODELO, device="cpu", compute_type="int8")
    segmentos, _info = _modelo_carregado.transcribe(str(caminho_video), language=idioma, word_timestamps=True, vad_filter=True)
    resultado = {"modelo": f"faster-whisper {MODELO}", "idioma": idioma, "revisada": False, "segmentos": []}
    for s in segmentos:
        resultado["segmentos"].append(
            {
                "inicio_s": round(s.start, 2),
                "fim_s": round(s.end, 2),
                "texto": s.text.strip(),
                "palavras": [
                    {"inicio_s": round(w.start, 2), "fim_s": round(w.end, 2), "texto": w.word.strip()}
                    for w in (s.words or [])
                ],
            }
        )
    Path(destino_json).write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado
