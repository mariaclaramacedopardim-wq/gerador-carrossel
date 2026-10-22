"""Geração do vídeo, proporção, duração, pacote do CapCut e erros previsíveis."""

import copy
import json
import zipfile

import pytest

from estudio_reels import ferramentas, pacote, planejador_demo, projetos, renderizador
from estudio_reels.ferramentas import ErroEspaco, ErroEstudio, ffprobe_json
from estudio_reels.plano import linha_do_tempo, validar
from tests.conftest import precisa_ffmpeg

pytestmark = precisa_ffmpeg


def _probe(caminho):
    dados = ffprobe_json(caminho)
    v = next(s for s in dados["streams"] if s["codec_type"] == "video")
    a = next((s for s in dados["streams"] if s["codec_type"] == "audio"), None)
    return v, a, float(dados["format"]["duration"])


def test_plano_demonstrativo(projeto_analisado):
    analise = projetos.carregar_analise(projeto_analisado["id"])
    p = planejador_demo.gerar_plano(projeto_analisado, analise)
    duracoes = {c["arquivo"]: c["metadados"]["duracao_s"] for c in analise["clipes"]}
    assert validar(p, duracoes) == []
    assert p["planejador"]["tipo"] == "demonstrativo" and "sem IA" in p["planejador"]["observacao"]
    assert "fala_vertical.mp4" in {s["arquivo_origem"] for s in p["segmentos"]}  # indispensável entra
    ordem_clipes = [c["arquivo"] for c in projeto_analisado["clipes"]]
    indices = [ordem_clipes.index(s["arquivo_origem"]) for s in p["segmentos"]]
    assert indices == sorted(indices)  # segue a ordem escolhida pela criadora
    assert abs(p["duracao_total_estimada_s"] - p["briefing"]["duracao_alvo_s"]) <= p["briefing"]["duracao_alvo_s"] * 0.25
    assert all(s["transicao_entrada"]["tipo"] == "corte" for s in p["segmentos"])  # nada de transição não pedida


def test_fluxo_completo_gera_mp4_vertical(projeto_analisado):
    i = projeto_analisado["id"]
    projetos.planejar(i, "demonstrativo")
    projetos.renderizar(i)
    estado = projetos.carregar(i)["estado"]
    assert estado["erro"] is None, estado
    plano, _ = projetos.ler_plano(i)
    saida = projetos.pasta(i) / "saida" / "pacote_capcut"
    for nome in ("reels_preview.mp4", "reels_base_sem_textos.mp4"):
        v, a, duracao = _probe(saida / nome)
        assert (v["width"], v["height"]) == (1080, 1920)
        assert v["codec_name"] == "h264" and a["codec_name"] == "aac"
        assert abs(duracao - plano["duracao_total_estimada_s"]) < 0.25
    for nome in ("edit_plan.json", "shot_report.md", "README.md", "textos_na_tela.txt"):
        assert (saida / nome).exists()
    assert len(list((saida / "clips").glob("*.mp4"))) == len(plano["segmentos"])
    relatorio = (saida / "shot_report.md").read_text(encoding="utf-8")
    assert "DEMONSTRATIVO" in relatorio and "não foi decidido por IA" in relatorio
    with zipfile.ZipFile(projetos.pasta(i) / "saida" / "pacote_capcut.zip") as z:
        nomes = z.namelist()
    assert "pacote_capcut/reels_preview.mp4" in nomes and "pacote_capcut/edit_plan.json" in nomes


def _plano_personalizado(projeto_analisado):
    analise = projetos.carregar_analise(projeto_analisado["id"])
    p = planejador_demo.gerar_plano(projeto_analisado, analise)
    p["planejador"]["tipo"] = "manual"
    return p


def test_transicoes_velocidade_barras_e_legendas(projeto_analisado, tmp_path):
    p = _plano_personalizado(projeto_analisado)
    segs = p["segmentos"]
    assert len(segs) >= 2
    segs[1]["transicao_entrada"] = {"tipo": "dissolver", "duracao_s": 0.5}
    segs[1]["enquadramento"]["modo"] = "encaixar_barras"
    segs[0]["velocidade"] = 1.5
    segs[0]["duracao_s"] = round((segs[0]["fim_s"] - segs[0]["inicio_s"]) / 1.5, 2)
    _, total = linha_do_tempo(p)
    p["duracao_total_estimada_s"] = total
    p["textos_na_tela"] = [{"id": "T01", "texto": "Ação, reação e ênfase: teste", "inicio_s": 0, "fim_s": 1.5, "posicao": "centro", "segmento_id": None}]
    p["legendas"] = {"fonte": "escrita_pela_criadora", "revisadas": True, "queimar_no_preview": True,
                     "itens": [{"inicio_s": 0.2, "fim_s": 1.4, "texto": "Legenda de teste"}]}
    pasta = projetos.pasta(projeto_analisado["id"])
    assert validar(p) == []
    resumo = renderizador.renderizar(p, pasta / "originais", tmp_path / "saida", tmp_path / "temp")
    assert all(v["resolucao_ok"] and v["duracao_ok"] and v["codecs_ok"] for v in resumo["verificacao"]), resumo
    pacote.gerar_pacote(p, {"clipes": []}, resumo, projeto_analisado, tmp_path / "saida")
    srt = (tmp_path / "saida" / "captions.srt").read_text(encoding="utf-8")
    assert "00:00:00,200 --> 00:00:01,400" in srt and "Legenda de teste" in srt


def test_proporcao_4_5(projeto_analisado, tmp_path):
    p = _plano_personalizado(projeto_analisado)
    p["formato_saida"].update(largura=1080, altura=1350)
    p["briefing"]["proporcao"] = "4:5"
    resumo = renderizador.renderizar(p, projetos.pasta(projeto_analisado["id"]) / "originais", tmp_path / "s", tmp_path / "t")
    v = resumo["verificacao"][0]
    assert (v["largura"], v["altura"]) == (1080, 1350) and v["duracao_ok"]


def test_filtro_nao_distorce():
    meta = {"largura": 1280, "altura": 720}
    enq = {"modo": "preencher", "foco_x": 0.5, "foco_y": 0.5, "zoom": 1.0}
    filtro = renderizador.filtro_enquadramento(meta, enq, 1080, 1920, False)
    # escala proporcional: 1280x720 * (1920/720) = 3414x1920, depois corta 1080 de largura
    assert "scale=3414:1920" in filtro and "crop=1080:1920:1167:0" in filtro


def test_erro_arquivo_ausente(projeto_analisado, tmp_path):
    p = _plano_personalizado(projeto_analisado)
    p["segmentos"][0]["arquivo_origem"] = "nao_existe.mp4"
    with pytest.raises(ErroEstudio, match="não está no projeto"):
        renderizador.renderizar(p, projetos.pasta(projeto_analisado["id"]) / "originais", tmp_path / "s", tmp_path / "t")


def test_erro_plano_invalido(projeto_analisado, tmp_path):
    p = _plano_personalizado(projeto_analisado)
    p["segmentos"][0]["fim_s"] = 999
    with pytest.raises(ErroEstudio, match="tem problemas"):
        renderizador.renderizar(p, projetos.pasta(projeto_analisado["id"]) / "originais", tmp_path / "s", tmp_path / "t")


def test_erro_falta_de_espaco(projeto_analisado, tmp_path, monkeypatch):
    p = _plano_personalizado(projeto_analisado)
    monkeypatch.setattr(ferramentas, "espaco_livre", lambda pasta: 10 * 1024 * 1024)
    with pytest.raises(ErroEspaco, match="Falta espaço"):
        renderizador.renderizar(p, projetos.pasta(projeto_analisado["id"]) / "originais", tmp_path / "s", tmp_path / "t")


def test_erro_original_corrompido(projeto_analisado, tmp_path):
    p = _plano_personalizado(projeto_analisado)
    originais = tmp_path / "originais"
    originais.mkdir()
    for s in p["segmentos"]:
        (originais / s["arquivo_origem"]).write_bytes(b"corrompido" * 1000)
    with pytest.raises(ErroEstudio, match="Não consegui ler"):
        renderizador.renderizar(p, originais, tmp_path / "s", tmp_path / "t")


def test_erro_vira_estado_do_projeto(projeto_analisado):
    i = projeto_analisado["id"]
    projetos.planejar(i, "demonstrativo")
    plano, _ = projetos.ler_plano(i)
    (projetos.pasta(i) / "originais" / plano["segmentos"][0]["arquivo_origem"]).write_bytes(b"lixo")
    projetos.renderizar(i)
    estado = projetos.carregar(i)["estado"]
    assert estado["etapa"] == "render_erro" and "Não consegui ler" in estado["erro"]


def test_traducao_de_erros_do_ffmpeg():
    assert isinstance(ferramentas.traduzir_erro_ffmpeg("... No space left on device"), ErroEspaco)
    assert "codec" in ferramentas.traduzir_erro_ffmpeg("Decoder (codec av1) not found").mensagem
    assert "não é um vídeo válido" in ferramentas.traduzir_erro_ffmpeg("moov atom not found").mensagem
