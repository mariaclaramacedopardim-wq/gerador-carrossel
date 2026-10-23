"""Valores padrão do publicador. Nada aqui é segredo; os segredos vêm de variáveis de ambiente (GitHub Secrets)."""

import json
import os
from pathlib import Path

RAIZ_PACOTE = Path(__file__).resolve().parent

FUSO = os.environ.get("TIKTOK_FUSO", "America/Sao_Paulo")

# Quantos vídeos por dia (1 a 3). Começa em 1 até o fluxo estar validado.
LIMITE_DIARIO = 3
POSTS_POR_DIA = max(1, min(LIMITE_DIARIO, int(os.environ.get("TIKTOK_POSTS_POR_DIA", "1"))))

# Janelas de maior engajamento para o público brasileiro: (início, fim, peso do sorteio).
# São referências gerais de mercado, não dados da sua conta. Ajuste quando houver métricas.
JANELAS = [("07:00", "09:00", 1), ("12:00", "14:00", 2), ("18:00", "22:00", 3)]

# O cron do Actions atrasa. Um horário sorteado ainda vale por até este tempo depois de passar.
TOLERANCIA_ATRASO_H = 2

# Tentativas por vídeo em falhas transitórias (instabilidade do TikTok, rede).
MAX_TENTATIVAS = 3

# Privacidade pedida quando o vídeo não define a sua. Só vale se TIKTOK_PUBLICO=1 (app auditado).
PRIVACIDADE_PADRAO = "PUBLIC_TO_EVERYONE"
PRIVACIDADE_SEGURA = "SELF_ONLY"

TAMANHO_CHUNK = 10 * 1024 * 1024
LIMITE_LEGENDA = 2200  # unidades UTF-16, como o TikTok conta

ESPERA_STATUS_S = 10
TEMPO_MAXIMO_STATUS_S = 600

DIAS_DE_HISTORICO = 30


def carregar_padroes():
    caminho = RAIZ_PACOTE / "padroes.json"
    if not caminho.exists():
        return {"legenda_padrao": "", "hashtags_padrao": []}
    return json.loads(caminho.read_text(encoding="utf-8"))
