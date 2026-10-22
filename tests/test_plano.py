"""Esquema JSON, tempos e ordem dos cortes."""

import copy

import pytest

from estudio_reels import plano


def plano_minimo():
    def seg(n, arquivo, ini, fim, transicao=None):
        return {
            "id": f"S{n:02d}", "ordem": n, "arquivo_origem": arquivo, "inicio_s": ini, "fim_s": fim,
            "duracao_s": round(fim - ini, 2), "papel": "desenvolvimento", "objetivo_narrativo": "teste",
            "obrigatorio": True, "enquadramento": {"modo": "preencher", "foco_x": 0.5, "foco_y": 0.5, "zoom": 1.0},
            "audio": {"modo": "original", "volume": 1.0}, "velocidade": 1.0,
            "transicao_entrada": transicao or {"tipo": "corte", "duracao_s": 0},
            "tratamento_visual": "", "observacoes": "",
        }

    return {
        "versao_esquema": "1.0",
        "planejador": {"tipo": "manual", "modelo": None, "observacao": "teste"},
        "briefing": {"objetivo": "", "estilo": "", "historia": "", "duracao_alvo_s": 6, "proporcao": "9:16",
                     "tratamento_orientacao": "encaixar_desfocado", "ritmo": "medio", "narracao": "fala_dos_clipes"},
        "formato_saida": {"largura": 1080, "altura": 1920, "fps": 30},
        "segmentos": [seg(1, "a.mp4", 0, 3), seg(2, "b.mp4", 1, 4, {"tipo": "dissolver", "duracao_s": 0.5})],
        "textos_na_tela": [{"id": "T01", "texto": "Oi", "inicio_s": 0, "fim_s": 2, "posicao": "topo", "segmento_id": "S01"}],
        "legendas": {"fonte": "nenhuma", "revisadas": False, "queimar_no_preview": False, "itens": []},
        "audio_geral": {"musica": "", "narracao": "", "efeitos_sonoros": ""},
        "orientacoes_edicao": {"transicoes_e_efeitos": "", "tratamento_visual": "", "ajustes_no_capcut": []},
        "avisos": [],
        "clipes_nao_usados": [],
        "duracao_total_estimada_s": 5.5,
    }


def test_plano_valido():
    assert plano.validar(plano_minimo(), {"a.mp4": 5, "b.mp4": 5}) == []


def test_linha_do_tempo_desconta_transicao():
    posicoes, total = plano.linha_do_tempo(plano_minimo())
    assert posicoes == [{"id": "S01", "inicio_s": 0, "fim_s": 3}, {"id": "S02", "inicio_s": 2.5, "fim_s": 5.5}]
    assert total == 5.5


@pytest.mark.parametrize("alterar, trecho_erro", [
    (lambda p: p.pop("segmentos"), "segmentos"),
    (lambda p: p["segmentos"][0].update(inicio_s="0"), "inicio_s"),
    (lambda p: p["segmentos"][0]["enquadramento"].update(modo="esticar"), "modo"),
    (lambda p: p.update(campo_extra=1), "campo_extra"),
    (lambda p: p["planejador"].update(tipo="ia_magica"), "tipo"),
])
def test_esquema_rejeita(alterar, trecho_erro):
    p = plano_minimo()
    alterar(p)
    erros = plano.validar(p)
    assert erros and any(trecho_erro in e for e in erros), erros


def test_fim_antes_do_inicio():
    p = plano_minimo()
    p["segmentos"][0].update(inicio_s=3, fim_s=2)
    assert any("maior que inicio_s" in e for e in plano.validar(p))


def test_duracao_inconsistente():
    p = plano_minimo()
    p["segmentos"][0]["duracao_s"] = 9
    assert any("duracao_s deveria ser" in e for e in plano.validar(p))


def test_velocidade_entra_na_duracao():
    p = plano_minimo()
    p["segmentos"][0].update(velocidade=2.0, duracao_s=1.5)
    p["duracao_total_estimada_s"] = 4.0
    assert plano.validar(p) == []


def test_ordem_com_buraco_ou_repetida():
    p = plano_minimo()
    p["segmentos"][1]["ordem"] = 3
    assert any("ordem" in e for e in plano.validar(p))
    p["segmentos"][1]["ordem"] = 1
    assert any("ordem" in e for e in plano.validar(p))


def test_trecho_alem_da_duracao_do_clipe():
    erros = plano.validar(plano_minimo(), {"a.mp4": 2.0, "b.mp4": 5})
    assert any("só tem 2.00 s" in e for e in erros)


def test_arquivo_inexistente():
    erros = plano.validar(plano_minimo(), {"a.mp4": 5})
    assert any("b.mp4" in e for e in erros)


def test_primeiro_segmento_sem_transicao():
    p = plano_minimo()
    p["segmentos"][0]["transicao_entrada"] = {"tipo": "dissolver", "duracao_s": 0.5}
    assert any("primeiro segmento" in e for e in plano.validar(p))


def test_transicao_longa_demais():
    p = plano_minimo()
    p["segmentos"][1]["transicao_entrada"]["duracao_s"] = 2.0
    p["duracao_total_estimada_s"] = 4.0
    assert any("longa demais" in e for e in plano.validar(p))


def test_total_errado_e_texto_depois_do_fim():
    p = plano_minimo()
    p["duracao_total_estimada_s"] = 10
    assert any("duracao_total_estimada_s" in e for e in plano.validar(p))
    p = plano_minimo()
    p["textos_na_tela"][0]["fim_s"] = 8
    assert any("depois do fim" in e for e in plano.validar(p))


def test_esquema_para_api_sem_restricoes_numericas():
    texto = str(plano.esquema_para_api())
    assert "minimum" not in texto and "pattern" not in texto
    assert "additionalProperties" in texto


def test_salvar_guarda_versao_anterior(tmp_path):
    destino = tmp_path / "edit_plan.json"
    plano.salvar(plano_minimo(), destino)
    segundo = copy.deepcopy(plano_minimo())
    segundo["planejador"]["observacao"] = "nova"
    plano.salvar(segundo, destino)
    assert (tmp_path / "edit_plan.anterior.json").exists()
    assert plano.carregar(destino)["planejador"]["observacao"] == "nova"


def test_json_invalido(tmp_path):
    ruim = tmp_path / "x.json"
    ruim.write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ValueError, match="não é um JSON válido"):
        plano.carregar(ruim)


def test_exemplo_da_documentacao_e_valido():
    import json
    import re

    from estudio_reels import config

    texto = (config.RAIZ_PACOTE / "ESQUEMA_PLANO.md").read_text(encoding="utf-8")
    exemplo = json.loads(re.search(r"```json\n(.*?)```", texto, re.S).group(1))
    assert plano.validar(exemplo) == []


def test_cli_validar(tmp_path, capsys):
    from estudio_reels.__main__ import main

    arquivo = tmp_path / "edit_plan.json"
    plano.salvar(plano_minimo(), arquivo)
    assert main(["validar", str(arquivo)]) == 0 and "Plano válido" in capsys.readouterr().out
    ruim = plano_minimo()
    ruim["segmentos"][0]["fim_s"] = -1
    plano.salvar(ruim, arquivo)
    assert main(["validar", str(arquivo)]) == 1
