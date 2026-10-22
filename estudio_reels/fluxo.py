"""Fluxo autônomo: importar vídeos do disco, montar de ponta a ponta e guardar versões.

Usado pelo Claude Code (na nuvem ou no Codespace) quando os vídeos chegam como
arquivos e não pelo envio da página. Não substitui nada do estúdio: chama as
mesmas etapas (analisar, planejar, renderizar) e acrescenta duas coisas:

- versões numeradas (v1, v2...) de cada montagem, sem apagar as anteriores;
- memória do projeto em estudio_reels_memoria/<id>/ (só texto, versionada no Git):
  briefing, clipes, planos de cada versão e histórico de pedidos. Com ela, uma
  sessão nova retoma o projeto sem repetir o briefing (os vídeos precisam ser
  enviados de novo, porque não vão para o GitHub).
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from . import config, projetos
from .ferramentas import ErroEstudio
from .plano import carregar as carregar_plano, linha_do_tempo, validar

# Anexos do chat chegam como "a2c17be9-IMG_3935.MOV"; o prefixo muda a cada envio.
PREFIXO_ANEXO = re.compile(r"^[0-9a-f]{8}-")


def pasta_memoria(id_projeto):
    raiz = Path(os.environ.get("ESTUDIO_REELS_MEMORIA", config.RAIZ_REPO / "estudio_reels_memoria"))
    return raiz / id_projeto


def nome_do_clipe(caminho):
    """Nome estável do clipe: tira o prefixo aleatório dos anexos, para o plano continuar valendo em outra sessão."""
    return PREFIXO_ANEXO.sub("", Path(caminho).name)


def _nome_no_projeto(caminho):
    """Nome que o clipe recebe dentro do projeto (mesma limpeza do envio: IMG_3935.MOV vira IMG_3935.mov)."""
    return projetos.nome_seguro(nome_do_clipe(caminho), set())


def _exigir_ok(id_projeto):
    estado = projetos.carregar(id_projeto)["estado"]
    if estado["erro"]:
        raise ErroEstudio(estado["erro"], estado.get("detalhe") or "")


def importar(caminhos, nome="", briefing=None, id_projeto=None):
    """Cria um projeto (ou recria um com id conhecido) com vídeos que já estão no disco."""
    if not caminhos:
        raise ErroEstudio("Informe pelo menos um vídeo.")
    for c in caminhos:
        if not Path(c).is_file():
            raise ErroEstudio(f"Arquivo não encontrado: {c}")
    projeto = projetos.criar(briefing or {}, nome)
    if id_projeto and id_projeto != projeto["id"]:
        if not projetos.PADRAO_ID.match(id_projeto):
            raise ErroEstudio("Id de projeto inválido.")
        if (projetos.raiz() / id_projeto).exists():
            raise ErroEstudio(f"O projeto {id_projeto} já existe nesta máquina.")
        (projetos.raiz() / projeto["id"]).rename(projetos.raiz() / id_projeto)
        projeto = projetos.atualizar(id_projeto, lambda p: p.update(id=id_projeto))
    id_projeto = projeto["id"]
    originais = projetos.pasta(id_projeto) / "originais"
    for c in caminhos:
        existentes = {p.name for p in originais.iterdir()}
        nome_final = projetos.nome_seguro(nome_do_clipe(c), existentes)
        shutil.copy2(c, originais / nome_final)
        projetos.registrar_clipe(id_projeto, nome_final)
    salvar_memoria(id_projeto)
    return projetos.carregar(id_projeto)


def auto(id_projeto, replanejar=False, pedido=None):
    """Analisa (se preciso), garante um plano e renderiza. Retorna o caminho da nova versão.

    Se já existe um plano (escrito pelo Claude Code ou à mão), ele é usado; só sem
    plano, ou com replanejar=True, o planejador demonstrativo gera um.
    """
    projetos.EXECUTAR_EM_SEGUNDO_PLANO = False
    projeto = projetos.carregar(id_projeto)
    caminho_analise = projetos.pasta(id_projeto) / "analise" / "analise.json"
    if projeto["analise_desatualizada"] or not caminho_analise.exists():
        projetos.analisar(id_projeto)
        _exigir_ok(id_projeto)
    if replanejar or not projetos.caminho_plano(id_projeto).exists():
        projetos.planejar(id_projeto, "demonstrativo")
        _exigir_ok(id_projeto)
    projetos.renderizar(id_projeto)
    _exigir_ok(id_projeto)
    return versao(id_projeto, pedido=pedido)


def versoes(id_projeto):
    pasta = projetos.pasta(id_projeto) / "saida" / "versoes"
    return sorted(pasta.glob("v*.mp4"), key=lambda p: int(p.stem[1:])) if pasta.exists() else []


def versao(id_projeto, pedido=None):
    """Guarda a montagem atual como vN.mp4 e registra o plano e o pedido na memória."""
    base = projetos.pasta(id_projeto)
    preview = base / "saida" / "pacote_capcut" / "reels_preview.mp4"
    if not preview.exists():
        raise ErroEstudio("Ainda não há montagem para guardar. Renderize primeiro.")
    # Continua a numeração da memória: depois de restaurar em outra sessão, a próxima versão não sobrescreve as antigas.
    planos_memoria = list((pasta_memoria(id_projeto) / "planos").glob("v*.json"))
    n = max([int(v.stem[1:]) for v in versoes(id_projeto)] + [int(p.stem[1:]) for p in planos_memoria] + [0]) + 1
    destino = base / "saida" / "versoes" / f"v{n}.mp4"
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(preview, destino)
    plano = carregar_plano(projetos.caminho_plano(id_projeto))
    (base / "plano" / "versoes").mkdir(exist_ok=True)
    shutil.copy2(projetos.caminho_plano(id_projeto), base / "plano" / "versoes" / f"v{n}.json")
    salvar_memoria(id_projeto, plano=plano, numero=n, pedido=pedido)
    return destino


def salvar_memoria(id_projeto, plano=None, numero=None, pedido=None):
    """Grava o que é preciso para retomar o projeto em outra sessão (só texto, sem vídeos)."""
    projeto = projetos.carregar(id_projeto)
    pasta = pasta_memoria(id_projeto)
    pasta.mkdir(parents=True, exist_ok=True)
    resumo = {k: projeto[k] for k in ("id", "nome", "criado_em", "briefing")}
    resumo["clipes"] = [
        {"arquivo": c["arquivo"], "indispensavel": c["indispensavel"], "descricao": c["descricao"],
         "duracao_s": c["metadados"]["duracao_s"], "resolucao": f"{c['metadados']['largura']}x{c['metadados']['altura']}"}
        for c in projeto["clipes"]
    ]
    (pasta / "projeto.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    estilo = projetos.pasta(id_projeto) / "estilo_textos.json"
    if estilo.exists():
        shutil.copy2(estilo, pasta / "estilo_textos.json")
    historico = pasta / "historico.md"
    if not historico.exists():
        historico.write_text(f"# Histórico — {projeto['nome']} ({id_projeto})\n", encoding="utf-8")
    if plano is not None and numero is not None:
        (pasta / "planos").mkdir(exist_ok=True)
        (pasta / "planos" / f"v{numero}.json").write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _, total = linha_do_tempo(plano)
        linhas = [
            "", f"## v{numero} — {datetime.now():%d/%m/%Y %H:%M}",
            f"- Pedido: {pedido or 'primeira versão'}",
            f"- Planejador: {plano['planejador']['tipo']} | {len(plano['segmentos'])} trechos | {total:.1f} s",
        ]
        with historico.open("a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
    return pasta


def restaurar(id_projeto, caminhos):
    """Recria nesta máquina um projeto da memória, com os vídeos enviados de novo, e reaplica o último plano."""
    memoria = pasta_memoria(id_projeto)
    if not (memoria / "projeto.json").exists():
        raise ErroEstudio(f"Não há memória do projeto {id_projeto} em {memoria}.")
    resumo = json.loads((memoria / "projeto.json").read_text(encoding="utf-8"))
    esperados = {c["arquivo"] for c in resumo["clipes"]}
    recebidos = {_nome_no_projeto(c) for c in caminhos}
    faltando = sorted(esperados - recebidos)
    if faltando:
        raise ErroEstudio("Faltam vídeos deste projeto: " + ", ".join(faltando) + ". Envie-os com o mesmo nome.")
    ordem = {c["arquivo"]: i for i, c in enumerate(resumo["clipes"])}
    caminhos = sorted((c for c in caminhos if _nome_no_projeto(c) in esperados), key=lambda c: ordem[_nome_no_projeto(c)])
    projeto = importar(caminhos, resumo["nome"], resumo["briefing"], id_projeto=id_projeto)
    projetos.atualizar_clipes(id_projeto, [{k: c[k] for k in ("arquivo", "indispensavel", "descricao")} for c in resumo["clipes"]])
    if (memoria / "estilo_textos.json").exists():
        shutil.copy2(memoria / "estilo_textos.json", projetos.pasta(id_projeto) / "estilo_textos.json")
    planos = sorted((memoria / "planos").glob("v*.json"), key=lambda p: int(p.stem[1:])) if (memoria / "planos").exists() else []
    if planos:
        plano = carregar_plano(planos[-1])
        duracoes = {c["arquivo"]: c["metadados"]["duracao_s"] for c in projetos.carregar(id_projeto)["clipes"]}
        erros = validar(plano, duracoes)
        if erros:
            raise ErroEstudio("O último plano salvo não vale para estes vídeos:\n- " + "\n- ".join(erros))
        projetos.caminho_plano(id_projeto).write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return projeto, (planos[-1].stem if planos else None)
