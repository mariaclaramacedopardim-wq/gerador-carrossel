"""Caminhos e valores padrão do estúdio."""

import os
from pathlib import Path

RAIZ_PACOTE = Path(__file__).resolve().parent
RAIZ_REPO = RAIZ_PACOTE.parent
PASTA_SKILL = RAIZ_REPO / ".claude" / "skills" / "reels-creative-director"

# Onde ficam os projetos (vídeos enviados, análises e resultados).
# Esta pasta está no .gitignore: nada dela vai para o GitHub.
PASTA_DADOS = Path(os.environ.get("ESTUDIO_REELS_DADOS", RAIZ_REPO / "estudio_reels_dados"))

PORTA = int(os.environ.get("ESTUDIO_REELS_PORTA", "8000"))

EXTENSOES_VIDEO = {".mov", ".mp4", ".m4v", ".webm", ".mkv", ".avi", ".3gp", ".hevc"}

# Espaço livre mínimo que o estúdio mantém no disco (em bytes).
RESERVA_DISCO = 500 * 1024 * 1024

PROPORCOES = {
    "9:16": (1080, 1920),
    "4:5": (1080, 1350),
    "1:1": (1080, 1080),
}

FPS_SAIDA = 30

# Modelo usado apenas no modo opcional "API Anthropic".
MODELO_IA = os.environ.get("ESTUDIO_REELS_MODELO", "claude-opus-5-5")
