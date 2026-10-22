"""Esquema, validação e linha do tempo do plano de edição (edit_plan.json)."""

import json
import shutil
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from . import config

CAMINHO_ESQUEMA = config.RAIZ_PACOTE / "esquema_plano.json"
TOLERANCIA_S = 0.05


@lru_cache(maxsize=1)
def esquema():
    return json.loads(CAMINHO_ESQUEMA.read_text(encoding="utf-8"))


def duracao_transicao(segmento, indice):
    """Sobreposição (s) entre este segmento e o anterior. O primeiro nunca sobrepõe."""
    t = segmento["transicao_entrada"]
    if indice == 0 or t["tipo"] == "corte":
        return 0.0
    return float(t["duracao_s"])


def linha_do_tempo(plano):
    """Posição de cada segmento no vídeo final, já descontando as transições."""
    posicoes, cursor = [], 0.0
    segmentos = sorted(plano["segmentos"], key=lambda s: s["ordem"])
    for i, s in enumerate(segmentos):
        inicio = cursor - duracao_transicao(s, i)
        fim = inicio + s["duracao_s"]
        posicoes.append({"id": s["id"], "inicio_s": round(inicio, 3), "fim_s": round(fim, 3)})
        cursor = fim
    return posicoes, round(cursor, 3)


def validar(plano, duracoes_origem=None):
    """Retorna a lista de erros (vazia quando o plano é válido).

    duracoes_origem: {nome_do_arquivo: duração em segundos} para conferir se os
    trechos existem nos clipes enviados.
    """
    erros = []
    for e in sorted(Draft202012Validator(esquema()).iter_errors(plano), key=lambda e: list(e.absolute_path)):
        local = "/".join(str(p) for p in e.absolute_path) or "(raiz)"
        erros.append(f"Esquema: {local}: {e.message}")
    if erros:
        return erros

    segmentos = sorted(plano["segmentos"], key=lambda s: s["ordem"])
    ordens = [s["ordem"] for s in segmentos]
    if ordens != list(range(1, len(segmentos) + 1)):
        erros.append(f"A ordem dos segmentos deve ser 1, 2, 3... sem repetir nem pular (recebido: {ordens}).")
    ids = [s["id"] for s in segmentos]
    if len(set(ids)) != len(ids):
        erros.append("Há segmentos com o mesmo id.")

    for i, s in enumerate(segmentos):
        nome = s["id"]
        if s["fim_s"] <= s["inicio_s"]:
            erros.append(f"{nome}: fim_s ({s['fim_s']}) precisa ser maior que inicio_s ({s['inicio_s']}).")
            continue
        esperado = (s["fim_s"] - s["inicio_s"]) / s["velocidade"]
        if abs(esperado - s["duracao_s"]) > TOLERANCIA_S:
            erros.append(f"{nome}: duracao_s deveria ser {esperado:.2f} ((fim - início) / velocidade), mas é {s['duracao_s']}.")
        if duracoes_origem is not None:
            if s["arquivo_origem"] not in duracoes_origem:
                erros.append(f"{nome}: o arquivo '{s['arquivo_origem']}' não está entre os clipes enviados.")
            elif s["fim_s"] > duracoes_origem[s["arquivo_origem"]] + TOLERANCIA_S:
                erros.append(
                    f"{nome}: termina em {s['fim_s']} s, mas '{s['arquivo_origem']}' só tem {duracoes_origem[s['arquivo_origem']]:.2f} s."
                )
        t = s["transicao_entrada"]
        if i == 0 and t["tipo"] != "corte":
            erros.append(f"{nome}: o primeiro segmento não pode ter transição de entrada (use 'corte').")
        if i > 0 and t["tipo"] != "corte":
            if t["duracao_s"] <= 0:
                erros.append(f"{nome}: a transição '{t['tipo']}' precisa de duracao_s maior que zero.")
            limite = min(s["duracao_s"], segmentos[i - 1]["duracao_s"]) / 2
            if t["duracao_s"] > limite:
                erros.append(f"{nome}: a transição de {t['duracao_s']} s é longa demais para segmentos tão curtos (máximo {limite:.2f} s).")
        if s["audio"]["modo"] == "original" and s["velocidade"] != 1 and not (0.5 <= s["velocidade"] <= 2):
            erros.append(f"{nome}: com áudio original, a velocidade precisa ficar entre 0,5x e 2x.")

    if erros:
        return erros

    _, total = linha_do_tempo(plano)
    if abs(total - plano["duracao_total_estimada_s"]) > 0.15:
        erros.append(f"duracao_total_estimada_s deveria ser {total:.2f} (soma dos segmentos menos as transições).")
    for t in plano["textos_na_tela"]:
        if t["fim_s"] <= t["inicio_s"]:
            erros.append(f"{t['id']}: fim_s precisa ser maior que inicio_s.")
        if t["fim_s"] > total + TOLERANCIA_S:
            erros.append(f"{t['id']}: termina em {t['fim_s']} s, depois do fim do vídeo ({total:.2f} s).")
        if t["segmento_id"] is not None and t["segmento_id"] not in ids:
            erros.append(f"{t['id']}: segmento_id '{t['segmento_id']}' não existe.")
    for j, leg in enumerate(plano["legendas"]["itens"], 1):
        if leg["fim_s"] <= leg["inicio_s"] or leg["fim_s"] > total + TOLERANCIA_S:
            erros.append(f"Legenda {j}: tempos inválidos ({leg['inicio_s']}–{leg['fim_s']}).")
    for a in plano["avisos"]:
        if a["segmento_id"] is not None and a["segmento_id"] not in ids:
            erros.append(f"Aviso cita segmento inexistente: {a['segmento_id']}.")
    return erros


def carregar(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"O arquivo de plano não é um JSON válido (linha {e.lineno}, coluna {e.colno}): {e.msg}") from e


def salvar(plano, caminho):
    """Salva o plano. A versão anterior, se houver, vira edit_plan.anterior.json."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        shutil.copy2(caminho, caminho.with_name("edit_plan.anterior.json"))
    caminho.write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def esquema_para_api():
    """Cópia do esquema sem as restrições numéricas e de tamanho.

    As saídas estruturadas da API aceitam um subconjunto de JSON Schema; as
    restrições retiradas aqui continuam sendo conferidas por validar().
    """
    retirar = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
               "minItems", "maxItems", "pattern", "$schema", "$id", "title"}

    def limpar(no):
        if isinstance(no, dict):
            return {k: limpar(v) for k, v in no.items() if k not in retirar}
        if isinstance(no, list):
            return [limpar(v) for v in no]
        return no

    return limpar(esquema())
