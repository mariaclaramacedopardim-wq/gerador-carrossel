import json
import shutil

from tests.conftest import PASTA_TESTE, precisa_ffmpeg
from estudio_reels import fluxo, projetos


def _anexos(videos_teste, pasta):
    """Simula anexos do chat: o mesmo vídeo com um prefixo aleatório no nome."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for prefixo, nome in zip(("a2c17be9", "b1531ba7"), ("fala_vertical.mp4", "broll_horizontal.mp4")):
        destino = pasta / f"{prefixo}-{nome}"
        shutil.copy2(videos_teste[nome], destino)
        caminhos.append(destino)
    return caminhos


@precisa_ffmpeg
def test_importar_auto_revisar_e_restaurar(videos_teste, monkeypatch, tmp_path):
    monkeypatch.setenv("ESTUDIO_REELS_MEMORIA", str(PASTA_TESTE / "dados" / "memoria"))
    anexos = _anexos(videos_teste, tmp_path / "anexos")

    projeto = fluxo.importar(anexos, "Teste do fluxo", {"objetivo": "Testar o fluxo", "duracao_alvo_s": 8})
    id_projeto = projeto["id"]
    assert [c["arquivo"] for c in projeto["clipes"]] == ["fala_vertical.mp4", "broll_horizontal.mp4"]

    v1 = fluxo.auto(id_projeto)
    assert v1.name == "v1.mp4" and v1.exists()
    memoria = fluxo.pasta_memoria(id_projeto)
    assert (memoria / "planos" / "v1.json").exists()
    assert json.loads((memoria / "projeto.json").read_text())["briefing"]["objetivo"] == "Testar o fluxo"

    # Pedido de alteração: o agente edita o plano e renderiza de novo, sem refazer o briefing.
    caminho = projetos.caminho_plano(id_projeto)
    plano = json.loads(caminho.read_text())
    plano["textos_na_tela"] = [{"id": "T01", "texto": "Versão revisada", "inicio_s": 0, "fim_s": 1.5,
                                "posicao": "centro", "segmento_id": None}]
    caminho.write_text(json.dumps(plano))
    # Estilo de texto da identidade (fonte manuscrita amarela, sem caixa nem contorno).
    (projetos.pasta(id_projeto) / "estilo_textos.json").write_text(json.dumps(
        {"fonte": "GochiHand-Regular.ttf", "cor": "#EEF09C", "caixa": False, "contorno": False, "maiusculas": True}))
    v2 = fluxo.auto(id_projeto, pedido="Trocar o texto de abertura")
    assert v2.name == "v2.mp4" and v1.exists()
    historico = (memoria / "historico.md").read_text()
    assert "## v2" in historico and "Trocar o texto de abertura" in historico

    # Sessão nova: a pasta de dados some, a memória fica; os vídeos voltam com outro prefixo.
    shutil.rmtree(projetos.pasta(id_projeto))
    novos = []
    for a in anexos:
        destino = tmp_path / "anexos2" / a.name.replace(a.name[:8], "ffffffff").replace(".mp4", ".MP4")
        destino.parent.mkdir(exist_ok=True)
        shutil.copy2(a, destino)
        novos.append(destino)
    restaurado, ultima = fluxo.restaurar(id_projeto, novos)
    assert restaurado["id"] == id_projeto and ultima == "v2"
    assert json.loads(projetos.caminho_plano(id_projeto).read_text())["textos_na_tela"][0]["texto"] == "Versão revisada"
    assert json.loads((projetos.pasta(id_projeto) / "estilo_textos.json").read_text())["cor"] == "#EEF09C"
    assert fluxo.auto(id_projeto, pedido="Reabrir em outra sessão").name == "v3.mp4"
    assert (memoria / "planos" / "v1.json").exists() and (memoria / "planos" / "v3.json").exists()


def test_estilo_de_texto_invalido(tmp_path):
    import pytest
    from estudio_reels.ferramentas import ErroEstudio
    from estudio_reels.renderizador import ESTILO_PADRAO, ler_estilo

    assert ler_estilo(tmp_path / "nao_existe.json") == ESTILO_PADRAO
    (tmp_path / "e.json").write_text('{"sombra": true}')
    with pytest.raises(ErroEstudio):
        ler_estilo(tmp_path / "e.json")
