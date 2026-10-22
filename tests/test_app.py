"""Interface web: envio em pedaços, análise, plano, montagem e download."""

import json

import pytest

from estudio_reels.app import app
from tests.conftest import precisa_ffmpeg


@pytest.fixture
def cliente():
    app.config["TESTING"] = True
    return app.test_client()


def test_pagina_inicial(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "Estúdio de Reels" in r.get_data(as_text=True)


def _enviar(cliente, id_projeto, caminho, nome=None, pedacos=3):
    dados = caminho.read_bytes()
    r = cliente.post(f"/api/projetos/{id_projeto}/envio", json={"nome": nome or caminho.name, "tamanho": len(dados)})
    assert r.status_code == 200, r.json
    arquivo = r.json["arquivo"]
    tamanho = -(-len(dados) // pedacos)
    for i in range(pedacos):
        parte = dados[i * tamanho:(i + 1) * tamanho]
        fim = "&fim=1" if i == pedacos - 1 else ""
        r = cliente.put(f"/api/projetos/{id_projeto}/envio/{arquivo}?posicao={i * tamanho}{fim}", data=parte)
    return r


@precisa_ffmpeg
def test_fluxo_pela_interface(cliente, videos_teste):
    p = cliente.post("/api/projetos", json={"briefing": {"objetivo": "Teste", "duracao_alvo_s": 10}}).json
    i = p["id"]
    for nome, caminho in videos_teste.items():
        r = _enviar(cliente, i, caminho, nome=f"IMG 0001 {nome}")
        assert r.status_code == 200 and r.json["concluido"], r.json
    visao = cliente.get(f"/api/projetos/{i}").json
    assert len(visao["clipes"]) == 3 and all(" " not in c["arquivo"] for c in visao["clipes"])
    assert visao["clipes"][0]["metadados"]["duracao_s"] > 0

    ordem = [{"arquivo": c["arquivo"], "indispensavel": True, "descricao": "abertura"} for c in reversed(visao["clipes"])]
    visao = cliente.post(f"/api/projetos/{i}/clipes", json={"clipes": ordem}).json
    assert [c["arquivo"] for c in visao["clipes"]] == [o["arquivo"] for o in ordem]

    assert cliente.post(f"/api/projetos/{i}/analisar").status_code == 200
    visao = cliente.post(f"/api/projetos/{i}/planejar", json={"modo": "demonstrativo"}).json
    assert visao["plano"]["planejador"]["tipo"] == "demonstrativo" and visao["erros_plano"] == []
    visao = cliente.post(f"/api/projetos/{i}/renderizar").json
    assert visao["estado"]["erro"] is None and visao["resultados"]
    zip_ = cliente.get(f"/arquivos/{i}/{visao['resultados']['zip']}?baixar=1")
    assert zip_.status_code == 200 and zip_.data[:2] == b"PK"
    video = cliente.get(f"/arquivos/{i}/saida/pacote_capcut/reels_preview.mp4")
    assert video.status_code == 200 and len(video.data) > 1000

    # plano editado à mão: inválido é recusado com a explicação
    plano = visao["plano"]
    plano["segmentos"][0]["fim_s"] = 999
    r = cliente.post(f"/api/projetos/{i}/plano", data=json.dumps(plano))
    assert r.status_code == 400 and r.json["erros"]
    r = cliente.post(f"/api/projetos/{i}/plano", data="{ isto não é json")
    assert r.status_code == 400 and "JSON inválido" in r.json["erros"][0]


@precisa_ffmpeg
def test_envio_fora_de_ordem(cliente, videos_teste):
    i = cliente.post("/api/projetos", json={}).json["id"]
    arquivo = cliente.post(f"/api/projetos/{i}/envio", json={"nome": "a.mp4", "tamanho": 10}).json["arquivo"]
    r = cliente.put(f"/api/projetos/{i}/envio/{arquivo}?posicao=500", data=b"x")
    assert r.status_code == 409 and r.json["recebido"] == 0


def test_extensao_recusada(cliente):
    i = cliente.post("/api/projetos", json={}).json["id"]
    r = cliente.post(f"/api/projetos/{i}/envio", json={"nome": "foto.jpg", "tamanho": 10})
    assert r.status_code == 400 and "não parece um vídeo" in r.json["erro"]


@precisa_ffmpeg
def test_arquivo_que_nao_e_video(cliente, tmp_path):
    i = cliente.post("/api/projetos", json={}).json["id"]
    falso = tmp_path / "falso.mov"
    falso.write_bytes(b"nada de video aqui" * 50)
    r = _enviar(cliente, i, falso, pedacos=1)
    assert r.status_code == 400 and "Não consegui ler" in r.json["erro"]
    assert cliente.get(f"/api/projetos/{i}").json["clipes"] == []


def test_falta_de_espaco_no_envio(cliente, monkeypatch):
    from estudio_reels import ferramentas

    monkeypatch.setattr(ferramentas, "espaco_livre", lambda pasta: 100 * 1024 * 1024)
    i = cliente.post("/api/projetos", json={}).json["id"]
    r = cliente.post(f"/api/projetos/{i}/envio", json={"nome": "grande.mov", "tamanho": 5 * 1024**3})
    assert r.status_code == 507 and "Falta espaço" in r.json["erro"]


def test_briefing_invalido_e_projeto_inexistente(cliente):
    i = cliente.post("/api/projetos", json={}).json["id"]
    assert cliente.post(f"/api/projetos/{i}/briefing", json={"ritmo": "turbo"}).status_code == 400
    assert cliente.get("/api/projetos/../../etc").status_code in (400, 404)
    assert cliente.get("/api/projetos/20990101-000000-zzzz").status_code == 400


def test_plano_sem_analise(cliente):
    i = cliente.post("/api/projetos", json={}).json["id"]
    r = cliente.post(f"/api/projetos/{i}/planejar", json={"modo": "demonstrativo"})
    assert r.status_code == 400 and "Analise os clipes" in r.json["erro"]


def test_download_fora_das_pastas_permitidas(cliente):
    i = cliente.post("/api/projetos", json={}).json["id"]
    assert cliente.get(f"/arquivos/{i}/projeto.json").status_code == 404
    assert cliente.get(f"/arquivos/{i}/saida/../projeto.json").status_code == 404
