"""Servidor web do estúdio (Flask). Abra no Safari pela porta encaminhada do Codespaces."""

import json
import posixpath
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory

from . import amostras, config, projetos
from .ferramentas import ErroEstudio, ErroEspaco, estado_do_sistema, garantir_espaco

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # cada pedaço de envio; os vídeos vão em pedaços de 8 MB


@app.errorhandler(ErroEstudio)
def _erro_estudio(e):
    status = 507 if isinstance(e, ErroEspaco) else 400
    return jsonify({"erro": e.mensagem, "detalhe": e.detalhe}), status


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/sistema")
def sistema():
    return jsonify(estado_do_sistema() | {"modelo_ia": config.MODELO_IA})


@app.get("/api/projetos")
def listar_projetos():
    return jsonify(projetos.listar())


@app.post("/api/projetos")
def criar_projeto():
    dados = request.get_json(silent=True) or {}
    return jsonify(projetos.criar(dados.get("briefing"), dados.get("nome", "")))


@app.post("/api/projetos/exemplo")
def criar_exemplo():
    return jsonify(amostras.criar_projeto_exemplo())


def _visao(id_projeto):
    projeto = projetos.carregar(id_projeto)
    plano, erros = projetos.ler_plano(id_projeto)
    analise = None
    caminho_analise = projetos.pasta(id_projeto) / "analise" / "analise.json"
    if caminho_analise.exists():
        dados = json.loads(caminho_analise.read_text(encoding="utf-8"))
        analise = {
            "limitacoes": dados["limitacoes"],
            "transcricao_disponivel": dados["transcricao_disponivel"],
            "clipes": {
                c["arquivo"]: {
                    "folha_contato": f"analise/{Path(c['arquivo']).stem}/{c['folha_contato']}" if c.get("folha_contato") else None,
                    "miniatura": f"analise/{Path(c['arquivo']).stem}/quadros/{c['quadros'][0]['arquivo']}" if c["quadros"] else None,
                    "cortes_de_cena_s": c["cortes_de_cena_s"],
                    "trechos_com_som_s": c["trechos_com_som_s"],
                    "candidatos": len(c["candidatos"]),
                    "transcrito": bool(c["transcricao"]),
                    "avisos": c["avisos"],
                }
                for c in dados["clipes"]
            },
        }
    return projeto | {"analise": analise, "plano": plano, "erros_plano": erros, "resultados": projetos.resultados(id_projeto)}


@app.get("/api/projetos/<id_projeto>")
def ver_projeto(id_projeto):
    return jsonify(_visao(id_projeto))


@app.delete("/api/projetos/<id_projeto>")
def apagar_projeto(id_projeto):
    projetos.apagar(id_projeto)
    return jsonify({"ok": True})


@app.post("/api/projetos/<id_projeto>/briefing")
def salvar_briefing(id_projeto):
    projetos.atualizar_briefing(id_projeto, request.get_json(silent=True) or {})
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/clipes")
def salvar_clipes(id_projeto):
    projetos.atualizar_clipes(id_projeto, (request.get_json(silent=True) or {}).get("clipes", []))
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/envio")
def iniciar_envio(id_projeto):
    """Reserva um nome seguro para o arquivo que vai ser enviado em pedaços."""
    dados = request.get_json(silent=True) or {}
    tamanho = int(dados.get("tamanho") or 0)
    pasta = projetos.pasta(id_projeto) / "originais"
    garantir_espaco(pasta, tamanho)
    existentes = {p.name for p in pasta.iterdir()}
    nome = projetos.nome_seguro(dados.get("nome"), existentes)
    (pasta / (nome + ".parcial")).write_bytes(b"")
    return jsonify({"arquivo": nome})


@app.put("/api/projetos/<id_projeto>/envio/<arquivo>")
def enviar_pedaco(id_projeto, arquivo):
    pasta = projetos.pasta(id_projeto) / "originais"
    parcial = pasta / (arquivo + ".parcial")
    if "/" in arquivo or not parcial.exists():
        raise ErroEstudio("Envio não encontrado. Comece o envio de novo.")
    posicao = int(request.args.get("posicao", "0"))
    if posicao != parcial.stat().st_size:
        return jsonify({"erro": "Pedaço fora de ordem.", "recebido": parcial.stat().st_size}), 409
    pedaco = request.get_data()
    garantir_espaco(pasta, len(pedaco))
    with parcial.open("ab") as f:
        f.write(pedaco)
    if request.args.get("fim") == "1":
        parcial.rename(pasta / arquivo)
        projeto = projetos.registrar_clipe(id_projeto, arquivo)
        clipe = next(c for c in projeto["clipes"] if c["arquivo"] == arquivo)
        return jsonify({"concluido": True, "clipe": clipe})
    return jsonify({"recebido": parcial.stat().st_size})


@app.delete("/api/projetos/<id_projeto>/clipes/<arquivo>")
def remover_clipe(id_projeto, arquivo):
    projetos.remover_clipe(id_projeto, arquivo)
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/analisar")
def analisar(id_projeto):
    projetos.analisar(id_projeto)
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/planejar")
def planejar(id_projeto):
    projetos.planejar(id_projeto, (request.get_json(silent=True) or {}).get("modo", "demonstrativo"))
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/plano")
def salvar_plano(id_projeto):
    try:
        plano = json.loads(request.get_data(as_text=True))
    except json.JSONDecodeError as e:
        return jsonify({"erros": [f"JSON inválido (linha {e.lineno}, coluna {e.colno}): {e.msg}"]}), 400
    erros = projetos.salvar_plano_manual(id_projeto, plano)
    if erros:
        return jsonify({"erros": erros}), 400
    return jsonify(_visao(id_projeto))


@app.post("/api/projetos/<id_projeto>/renderizar")
def renderizar(id_projeto):
    projetos.renderizar(id_projeto)
    return jsonify(_visao(id_projeto))


@app.get("/arquivos/<id_projeto>/<path:caminho>")
def baixar(id_projeto, caminho):
    base = projetos.pasta(id_projeto)
    caminho = posixpath.normpath(caminho)
    if caminho.split("/")[0] not in ("saida", "analise", "plano"):
        abort(404)
    return send_from_directory(base, caminho, as_attachment=request.args.get("baixar") == "1", conditional=True)


def iniciar():
    from .ferramentas import verificar_ffmpeg

    try:
        verificar_ffmpeg()
    except ErroEstudio as e:
        print("ATENÇÃO:", e.mensagem)
    print(f"\nEstúdio de Reels rodando na porta {config.PORTA}.")
    print("No Codespaces: abra a aba PORTAS (PORTS) e toque no ícone de globo da porta", config.PORTA, "\n")
    app.run(host="0.0.0.0", port=config.PORTA, threaded=True, debug=False)
