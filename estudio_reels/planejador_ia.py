"""Planejador OPCIONAL pela API da Anthropic (cobrado à parte da assinatura do Claude).

Requisitos:
- Uma chave de API criada em console.anthropic.com, com créditos. A assinatura do
  Claude (Pro/Max) e o Claude Code NÃO dão acesso a esta API.
- A chave guardada como secret do Codespaces com o nome ANTHROPIC_API_KEY.
  Nunca escreva a chave em arquivos do projeto.
- O pacote "anthropic":  .venv-reels/bin/python -m pip install -r estudio_reels/requirements-ia.txt

O modelo recebe o briefing, os metadados, os trechos candidatos, a transcrição
(se houver), as folhas de contato (quadros amostrados) e as instruções da skill
reels-creative-director. Ele NÃO assiste ao vídeo: vê só os quadros amostrados.
"""

import base64
import json
import os
from pathlib import Path

from . import config
from .ferramentas import ErroEstudio
from .plano import esquema_para_api, validar

PRECO_POR_MILHAO = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}
REFERENCIAS_DA_SKILL = ["SKILL.md", "references/creative-strategy.md", "references/scriptwriting.md", "references/capcut-workflow.md"]


class IAIndisponivel(ErroEstudio):
    pass


def verificar_disponibilidade():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise IAIndisponivel(
            "A API da Anthropic não está configurada (falta o secret ANTHROPIC_API_KEY). "
            "Use o plano demonstrativo ou peça o plano ao Claude Code. Veja o README do estúdio."
        )
    try:
        import anthropic  # noqa: F401
    except ImportError as e:
        raise IAIndisponivel("Falta instalar o pacote 'anthropic': .venv-reels/bin/python -m pip install -r estudio_reels/requirements-ia.txt") from e


def _instrucoes():
    partes = [
        "Você é a editora audiovisual da skill reels-creative-director. Sua tarefa é transformar o briefing e a análise "
        "dos clipes brutos em um plano de pré-edição de Instagram Reels, no formato JSON pedido.",
        "Regras específicas do plano:",
        "- Use somente arquivos e tempos que existem na análise. Tempos em segundos, dentro da duração de cada clipe.",
        "- Prefira começar e terminar trechos nos candidatos, cortes de cena ou limites de frase, para não interromper fala ou ação.",
        "- Escolha trechos pela história do briefing, pela continuidade, pela variedade visual, pela clareza da fala e pelo ritmo; "
        "nunca só por serem curtos ou movimentados.",
        "- Inclua todos os clipes marcados como INDISPENSÁVEL.",
        "- Você só vê quadros amostrados e a transcrição (quando existe). Não afirme nada sobre o que não foi visto; "
        "quando houver dúvida, registre em 'avisos' e em 'observacoes'.",
        "- Não invente música, efeitos ou transições que não foram pedidos. Corte seco é o padrão.",
        "- duracao_s = (fim_s - inicio_s) / velocidade. duracao_total_estimada_s = soma das durações menos as transições.",
        "- Textos na tela com no máximo cerca de 7 palavras e pelo menos 1,5 s na tela; tempos de textos e legendas são do vídeo final.",
        "- planejador.tipo deve ser 'api_anthropic'. Escreva em português do Brasil.",
        "",
        "Instruções da skill reels-creative-director (aplique, não copie):",
    ]
    for rel in REFERENCIAS_DA_SKILL:
        caminho = config.PASTA_SKILL / rel
        if caminho.exists():
            partes.append(f"\n<arquivo nome=\"{rel}\">\n{caminho.read_text(encoding='utf-8')}\n</arquivo>")
    return "\n".join(partes)


def _conteudo_usuario(pasta_job, analise):
    conteudo = [{"type": "text", "text": (Path(pasta_job) / "analise" / "contexto_para_ia.md").read_text(encoding="utf-8")}]
    for clipe in analise["clipes"]:
        if not clipe.get("folha_contato"):
            continue
        caminho = Path(pasta_job) / "analise" / Path(clipe["arquivo"]).stem / clipe["folha_contato"]
        conteudo.append({"type": "text", "text": f"Folha de contato de {clipe['arquivo']} (quadros amostrados, com o tempo de cada um):"})
        conteudo.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                      "data": base64.standard_b64encode(caminho.read_bytes()).decode("ascii")}})
    conteudo.append({"type": "text", "text": "Monte o plano de edição completo."})
    return conteudo


def estimar_custo(uso, modelo):
    entrada, saida = PRECO_POR_MILHAO.get(modelo, PRECO_POR_MILHAO["claude-opus-5-5"])
    return round((uso.input_tokens * entrada + uso.output_tokens * saida) / 1_000_000, 4)


def _ler_resposta(resposta):
    if resposta.stop_reason == "refusal":
        raise ErroEstudio("O modelo recusou o pedido. Tente reformular o briefing ou use o plano demonstrativo.")
    if resposta.stop_reason == "max_tokens":
        raise ErroEstudio("A resposta do modelo foi cortada por ser longa demais. Tente com menos clipes.")
    texto = next((b.text for b in resposta.content if b.type == "text"), None)
    if not texto:
        raise ErroEstudio("A resposta do modelo veio sem o plano.")
    return json.loads(texto)


def _chamar(cliente, modelo, mensagens):
    pedido = dict(
        model=modelo,
        max_tokens=64000,
        system=_instrucoes(),
        thinking={"type": "adaptive"},
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": esquema_para_api()}},
        messages=mensagens,
    )
    try:
        with cliente.messages.stream(**pedido) as stream:
            return stream.get_final_message()
    except Exception as e:
        try:
            import anthropic
        except ImportError:
            raise e
        if isinstance(e, anthropic.APIError):
            raise _traduzir_erro_api(e, anthropic) from e
        raise


def _traduzir_erro_api(e, anthropic):
    if isinstance(e, anthropic.AuthenticationError):
        return ErroEstudio("A chave da API foi recusada. Confira o secret ANTHROPIC_API_KEY.")
    if isinstance(e, anthropic.PermissionDeniedError):
        return ErroEstudio("A chave da API não tem permissão para este modelo.")
    if isinstance(e, anthropic.RateLimitError):
        return ErroEstudio("Limite de uso da API atingido. Espere alguns minutos e tente de novo.")
    if isinstance(e, anthropic.BadRequestError):
        return ErroEstudio("A API recusou o pedido (pode ser falta de créditos ou pedido grande demais).", str(e))
    if isinstance(e, anthropic.APIStatusError):
        return ErroEstudio(f"A API respondeu com erro {e.status_code}. Tente de novo mais tarde.", str(e))
    return ErroEstudio("Não consegui conectar à API da Anthropic. Confira a internet do Codespace.", str(e))


def gerar_plano(job, analise, pasta_job, cliente=None, modelo=None):
    """Pede o plano ao modelo. Faz no máximo uma rodada de correção se o plano vier inválido."""
    if cliente is None:
        verificar_disponibilidade()
        import anthropic

        cliente = anthropic.Anthropic()
    modelo = modelo or config.MODELO_IA
    duracoes = {c["arquivo"]: c["metadados"]["duracao_s"] for c in analise["clipes"]}
    mensagens = [{"role": "user", "content": _conteudo_usuario(pasta_job, analise)}]
    custo, erros = 0.0, []
    for _tentativa in range(2):
        resposta = _chamar(cliente, modelo, mensagens)
        custo += estimar_custo(resposta.usage, modelo)
        plano = _ler_resposta(resposta)
        plano["planejador"]["tipo"] = "api_anthropic"
        plano["planejador"]["modelo"] = modelo
        erros = validar(plano, duracoes)
        if not erros:
            return plano, custo
        mensagens += [
            {"role": "assistant", "content": resposta.content},
            {"role": "user", "content": "O plano tem estes erros de validação. Corrija e devolva o plano completo:\n- " + "\n- ".join(erros)},
        ]
    raise ErroEstudio("O modelo devolveu um plano inválido mesmo após uma correção:\n- " + "\n- ".join(erros))
