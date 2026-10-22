"""Modo API: sem chave, o estúdio avisa e não finge. Com um cliente substituto (só para teste), o fluxo é conferido."""

import json
from types import SimpleNamespace

import pytest

from estudio_reels import planejador_demo, planejador_ia, projetos
from estudio_reels.ferramentas import ErroEstudio


def test_sem_chave_avisa(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(planejador_ia.IAIndisponivel, match="ANTHROPIC_API_KEY"):
        planejador_ia.verificar_disponibilidade()


class ClienteSubstituto:
    """Imita o formato de resposta do SDK. Não é IA: devolve planos prontos, um por chamada."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.pedidos = []
        self.messages = self

    def stream(self, **pedido):
        self.pedidos.append(pedido)
        texto = json.dumps(self.respostas.pop(0))
        resposta = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=texto)],
                                   usage=SimpleNamespace(input_tokens=20000, output_tokens=5000))

        class Contexto:
            def __enter__(self_):
                return SimpleNamespace(get_final_message=lambda: resposta)

            def __exit__(self_, *a):
                return False

        return Contexto()


def test_pedido_e_validacao(projeto_analisado):
    i = projeto_analisado["id"]
    analise = projetos.carregar_analise(i)
    bom = planejador_demo.gerar_plano(projeto_analisado, analise)
    ruim = json.loads(json.dumps(bom))
    ruim["segmentos"][0]["fim_s"] = 999
    cliente = ClienteSubstituto([ruim, bom])
    plano, custo = planejador_ia.gerar_plano(projeto_analisado, analise, projetos.pasta(i), cliente=cliente, modelo="claude-opus-5-5")
    assert plano["planejador"] == {**bom["planejador"], "tipo": "api_anthropic", "modelo": "claude-opus-5-5"}
    assert len(cliente.pedidos) == 2  # uma rodada de correção
    primeiro = cliente.pedidos[0]
    assert primeiro["model"] == "claude-opus-5-5"
    assert primeiro["output_config"]["format"]["type"] == "json_schema"
    assert "reels-creative-director" in primeiro["system"]
    conteudo = primeiro["messages"][0]["content"]
    assert sum(1 for b in conteudo if b["type"] == "image") == len(analise["clipes"])
    assert "corrija" in cliente.pedidos[1]["messages"][-1]["content"].lower()
    assert custo == pytest.approx(2 * (20000 * 4 + 5000 * 20) / 1_000_000)


def test_plano_invalido_duas_vezes_gera_erro(projeto_analisado):
    i = projeto_analisado["id"]
    analise = projetos.carregar_analise(i)
    ruim = planejador_demo.gerar_plano(projeto_analisado, analise)
    ruim["segmentos"][0]["fim_s"] = 999
    with pytest.raises(ErroEstudio, match="inválido"):
        planejador_ia.gerar_plano(projeto_analisado, analise, projetos.pasta(i), cliente=ClienteSubstituto([ruim, ruim]))
