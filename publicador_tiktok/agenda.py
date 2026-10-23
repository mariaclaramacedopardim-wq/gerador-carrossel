"""Escolha dos horários do dia: sorteados dentro de janelas de engajamento, nunca fixos."""

import random
from datetime import datetime, timedelta

from . import config


def _minutos(texto):
    hora, minuto = texto.split(":")
    return int(hora) * 60 + int(minuto)


def sortear_horarios(quantidade, janelas=None, rng=None):
    """Sorteia `quantidade` horários "HH:MM", cada um numa janela diferente (o peso favorece as janelas melhores)."""
    janelas = list(janelas or config.JANELAS)
    rng = rng or random.SystemRandom()
    quantidade = min(quantidade, len(janelas))
    escolhidas = []
    restantes = janelas[:]
    for _ in range(quantidade):
        peso_total = sum(j[2] for j in restantes)
        ponto = rng.uniform(0, peso_total)
        acumulado = 0
        for janela in restantes:
            acumulado += janela[2]
            if ponto <= acumulado:
                escolhidas.append(janela)
                restantes.remove(janela)
                break
    horarios = []
    for inicio, fim, _peso in escolhidas:
        minuto = rng.randint(_minutos(inicio), _minutos(fim) - 1)
        horarios.append(f"{minuto // 60:02d}:{minuto % 60:02d}")
    return sorted(horarios)


def garantir_plano_do_dia(estado, agora, quantidade=None, rng=None):
    """Cria o plano do dia na primeira execução e o mantém nas seguintes."""
    dia = estado.dia(agora.date().isoformat())
    if not dia["horarios"]:
        dia["horarios"] = sortear_horarios(quantidade or config.POSTS_POR_DIA, rng=rng)
    return dia


def horario_devido(dia, agora, tolerancia_h=None):
    """Devolve o primeiro horário que já passou, não foi usado e ainda está na tolerância.

    Horários que passaram da tolerância vão para `perdidos` (alterando `dia`).
    """
    tolerancia = timedelta(hours=config.TOLERANCIA_ATRASO_H if tolerancia_h is None else tolerancia_h)
    for horario in dia["horarios"]:
        if horario in dia["usados"] or horario in dia["perdidos"]:
            continue
        hora, minuto = map(int, horario.split(":"))
        momento = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if momento > agora:
            continue
        if agora - momento <= tolerancia:
            return horario
        dia["perdidos"].append(horario)
    return None
