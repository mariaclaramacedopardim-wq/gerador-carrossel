"""Leitura de metadados, miniaturas, cortes de cena e trechos com som."""

import pytest

from estudio_reels import analise
from estudio_reels.ferramentas import ErroEstudio
from tests.conftest import precisa_ffmpeg

pytestmark = precisa_ffmpeg


def test_metadados(videos_teste):
    m = analise.ler_metadados(videos_teste["fala_vertical.mp4"])
    assert (m["largura"], m["altura"], m["orientacao"]) == (720, 1280, "vertical")
    assert abs(m["duracao_s"] - 8) < 0.1 and round(m["fps"]) == 30 and m["tem_audio"]
    h = analise.ler_metadados(videos_teste["broll_horizontal.mp4"])
    assert h["orientacao"] == "horizontal" and not h["tem_audio"]


def test_analise_completa(videos_teste, tmp_path):
    r = analise.analisar_clipe(videos_teste["fala_vertical.mp4"], tmp_path / "fala")
    assert any(abs(c - 4.0) < 0.3 for c in r["cortes_de_cena_s"]), r["cortes_de_cena_s"]
    # som de 0 a 3 s e de 4,5 a 8 s, com silêncio no meio
    assert len(r["trechos_com_som_s"]) == 2
    assert abs(r["trechos_com_som_s"][0][1] - 3.0) < 0.3 and abs(r["trechos_com_som_s"][1][0] - 4.5) < 0.3
    assert (tmp_path / "fala" / "folha_contato.jpg").exists()
    assert len(r["quadros"]) >= 5 and all((tmp_path / "fala" / "quadros" / q["arquivo"]).exists() for q in r["quadros"])
    assert all(c["tem_som"] for c in r["candidatos"])
    for c in r["candidatos"]:  # candidatos não atravessam o corte de cena
        assert c["fim_s"] <= 4.0 + 0.25 or c["inicio_s"] >= 4.0 - 0.01


def test_clipe_sem_audio_vira_broll(videos_teste, tmp_path):
    r = analise.analisar_clipe(videos_teste["broll_horizontal.mp4"], tmp_path / "h")
    assert r["candidatos"] and not any(c["tem_som"] for c in r["candidatos"])
    assert any("horizontal" in a for a in r["avisos"]) and any("sem áudio" in a for a in r["avisos"])


def test_arquivo_invalido(tmp_path):
    falso = tmp_path / "falso.mp4"
    falso.write_bytes(b"isto nao e um video" * 100)
    with pytest.raises(ErroEstudio, match="Não consegui ler"):
        analise.ler_metadados(falso)


def test_originais_preservados(projeto_analisado):
    import hashlib

    from estudio_reels import projetos

    i = projeto_analisado["id"]
    pasta = projetos.pasta(i) / "originais"
    antes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pasta.iterdir()}
    projetos.planejar(i, "demonstrativo")
    projetos.renderizar(i)
    depois = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pasta.iterdir()}
    assert antes == depois and len(antes) == 3


def test_contexto_para_ia(projeto_analisado):
    from estudio_reels import projetos

    texto = (projetos.pasta(projeto_analisado["id"]) / "analise" / "contexto_para_ia.md").read_text(encoding="utf-8")
    assert "INDISPENSÁVEL" in texto and "Limitações" in texto and "folha_contato.jpg" in texto
