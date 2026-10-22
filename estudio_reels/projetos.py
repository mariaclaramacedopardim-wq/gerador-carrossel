"""Projetos (um por Reels) guardados em pastas, sem banco de dados.

estudio_reels_dados/projetos/<id>/
  projeto.json          briefing, clipes, estado
  originais/            vídeos enviados (nunca alterados)
  analise/              metadados, quadros, folhas de contato, contexto_para_ia.md
  plano/edit_plan.json  plano de edição
  saida/pacote_capcut/  resultados; saida/pacote_capcut.zip
"""

import json
import re
import secrets
import shutil
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import analise as analise_mod
from . import config, pacote, plano as plano_mod, planejador_demo, planejador_ia, renderizador
from .ferramentas import ErroEstudio

BRIEFING_PADRAO = {
    "objetivo": "",
    "estilo": "",
    "historia": "",
    "duracao_alvo_s": 30,
    "proporcao": "9:16",
    "tratamento_orientacao": "encaixar_desfocado",
    "ritmo": "medio",
    "narracao": "fala_dos_clipes",
}
OPCOES = {
    "proporcao": set(config.PROPORCOES),
    "tratamento_orientacao": {"preencher", "encaixar_desfocado", "encaixar_barras"},
    "ritmo": {"rapido", "medio", "lento"},
    "narracao": {"fala_dos_clipes", "narracao_off", "sem_fala"},
}
PADRAO_ID = re.compile(r"^[0-9]{8}-[0-9]{6}-[a-z0-9]{4}$")

_trava = threading.Lock()
_fila = ThreadPoolExecutor(max_workers=1)  # uma tarefa pesada por vez (o Codespace básico tem 2 núcleos)
EXECUTAR_EM_SEGUNDO_PLANO = True


def raiz():
    pasta = config.PASTA_DADOS / "projetos"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def pasta(id_projeto):
    if not PADRAO_ID.match(id_projeto or ""):
        raise ErroEstudio("Projeto inválido.")
    caminho = raiz() / id_projeto
    if not (caminho / "projeto.json").exists():
        raise ErroEstudio("Projeto não encontrado.")
    return caminho


def carregar(id_projeto):
    return json.loads((pasta(id_projeto) / "projeto.json").read_text(encoding="utf-8"))


def salvar(projeto):
    destino = raiz() / projeto["id"] / "projeto.json"
    temporario = destino.with_suffix(".tmp")
    with _trava:
        temporario.write_text(json.dumps(projeto, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(destino)


def atualizar(id_projeto, funcao):
    with _trava:
        caminho = pasta(id_projeto) / "projeto.json"
        projeto = json.loads(caminho.read_text(encoding="utf-8"))
        funcao(projeto)
        temporario = caminho.with_suffix(".tmp")
        temporario.write_text(json.dumps(projeto, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(caminho)
        return projeto


def limpar_briefing(dados):
    b = dict(BRIEFING_PADRAO)
    for chave in ("objetivo", "estilo", "historia"):
        if chave in dados:
            b[chave] = str(dados[chave] or "").strip()[:2000]
    if "duracao_alvo_s" in dados:
        try:
            b["duracao_alvo_s"] = min(180, max(3, float(dados["duracao_alvo_s"])))
        except (TypeError, ValueError):
            raise ErroEstudio("A duração precisa ser um número de segundos (entre 3 e 180).")
    for chave, validas in OPCOES.items():
        if chave in dados:
            if dados[chave] not in validas:
                raise ErroEstudio(f"Opção inválida para {chave}: {dados[chave]}")
            b[chave] = dados[chave]
    return b


def criar(briefing=None, nome=""):
    agora = datetime.now()
    id_projeto = f"{agora:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
    caminho = raiz() / id_projeto
    for sub in ("originais", "analise", "plano", "saida"):
        (caminho / sub).mkdir(parents=True)
    projeto = {
        "id": id_projeto,
        "nome": (nome or "").strip()[:80] or f"Reels de {agora:%d/%m %H:%M}",
        "criado_em": agora.isoformat(timespec="seconds"),
        "briefing": limpar_briefing(briefing or {}),
        "clipes": [],
        "analise_desatualizada": True,
        "estado": {"etapa": "pronto_para_envio", "rodando": False, "mensagem": "", "erro": None, "detalhe": None},
        "ultimo_custo_ia_usd": None,
    }
    salvar(projeto)
    return projeto


def listar():
    projetos = []
    for arquivo in sorted(raiz().glob("*/projeto.json"), reverse=True):
        try:
            p = json.loads(arquivo.read_text(encoding="utf-8"))
            projetos.append({"id": p["id"], "nome": p["nome"], "criado_em": p["criado_em"], "clipes": len(p["clipes"])})
        except (OSError, ValueError, KeyError):
            continue
    return projetos


def apagar(id_projeto):
    shutil.rmtree(pasta(id_projeto))


def nome_seguro(nome_original, existentes):
    caminho = Path(nome_original or "video.mp4")
    extensao = caminho.suffix.lower()
    if extensao not in config.EXTENSOES_VIDEO:
        raise ErroEstudio(f"'{caminho.name}' não parece um vídeo (extensões aceitas: {', '.join(sorted(config.EXTENSOES_VIDEO))}).")
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", caminho.stem).strip("_")[:50] or "video"
    nome, n = f"{base}{extensao}", 2
    while nome in existentes:
        nome, n = f"{base}_{n}{extensao}", n + 1
    return nome


def registrar_clipe(id_projeto, nome_arquivo):
    """Chamado quando o envio de um arquivo termina: confere se é vídeo e guarda os metadados."""
    caminho = pasta(id_projeto) / "originais" / nome_arquivo
    try:
        meta = analise_mod.ler_metadados(caminho)
    except ErroEstudio:
        caminho.unlink(missing_ok=True)
        raise

    def adicionar(p):
        p["clipes"] = [c for c in p["clipes"] if c["arquivo"] != nome_arquivo]
        p["clipes"].append({"arquivo": nome_arquivo, "indispensavel": False, "descricao": "", "metadados": meta})
        p["analise_desatualizada"] = True

    return atualizar(id_projeto, adicionar)


def remover_clipe(id_projeto, nome_arquivo):
    def remover(p):
        if nome_arquivo not in [c["arquivo"] for c in p["clipes"]]:
            raise ErroEstudio("Clipe não encontrado.")
        p["clipes"] = [c for c in p["clipes"] if c["arquivo"] != nome_arquivo]
        p["analise_desatualizada"] = True

    projeto = atualizar(id_projeto, remover)
    (pasta(id_projeto) / "originais" / nome_arquivo).unlink(missing_ok=True)
    shutil.rmtree(pasta(id_projeto) / "analise" / Path(nome_arquivo).stem, ignore_errors=True)
    return projeto


def atualizar_clipes(id_projeto, lista):
    """Recebe a lista na nova ordem, com indispensavel/descricao de cada clipe."""
    def aplicar(p):
        atuais = {c["arquivo"]: c for c in p["clipes"]}
        nova = []
        for item in lista:
            c = atuais.pop(item.get("arquivo"), None)
            if c is None:
                continue
            c["indispensavel"] = bool(item.get("indispensavel"))
            c["descricao"] = str(item.get("descricao") or "").strip()[:300]
            nova.append(c)
        p["clipes"] = nova + list(atuais.values())

    return atualizar(id_projeto, aplicar)


def atualizar_briefing(id_projeto, dados):
    briefing = limpar_briefing(dados)
    return atualizar(id_projeto, lambda p: p.update(briefing=briefing, nome=(str(dados.get("nome") or "").strip()[:80] or p["nome"])))


# --- Plano ----------------------------------------------------------------

def caminho_plano(id_projeto):
    return pasta(id_projeto) / "plano" / "edit_plan.json"


def carregar_analise(id_projeto):
    caminho = pasta(id_projeto) / "analise" / "analise.json"
    if not caminho.exists():
        raise ErroEstudio("Analise os clipes antes de gerar o plano.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def ler_plano(id_projeto):
    """Retorna (plano ou None, lista de erros)."""
    caminho = caminho_plano(id_projeto)
    if not caminho.exists():
        return None, []
    try:
        plano = plano_mod.carregar(caminho)
    except ValueError as e:
        return None, [str(e)]
    projeto = carregar(id_projeto)
    duracoes = {c["arquivo"]: c["metadados"]["duracao_s"] for c in projeto["clipes"]}
    return plano, plano_mod.validar(plano, duracoes)


def salvar_plano_manual(id_projeto, plano):
    projeto = carregar(id_projeto)
    duracoes = {c["arquivo"]: c["metadados"]["duracao_s"] for c in projeto["clipes"]}
    erros = plano_mod.validar(plano, duracoes)
    if not erros:
        plano_mod.salvar(plano, caminho_plano(id_projeto))
    return erros


# --- Tarefas demoradas ----------------------------------------------------

def _mudar_estado(id_projeto, **campos):
    atualizar(id_projeto, lambda p: p["estado"].update(campos))


def _executar(id_projeto, etapa, funcao):
    _mudar_estado(id_projeto, etapa=etapa, rodando=True, mensagem="Na fila...", erro=None, detalhe=None)

    def tarefa():
        try:
            funcao(lambda texto: _mudar_estado(id_projeto, mensagem=texto))
            _mudar_estado(id_projeto, etapa=etapa + "_ok", rodando=False, mensagem="Concluído.")
        except ErroEstudio as e:
            _mudar_estado(id_projeto, etapa=etapa + "_erro", rodando=False, mensagem="", erro=e.mensagem, detalhe=e.detalhe)
        except Exception as e:  # erro inesperado: mostra o detalhe técnico para facilitar o suporte
            _mudar_estado(id_projeto, etapa=etapa + "_erro", rodando=False, mensagem="",
                          erro=f"Erro inesperado: {e}", detalhe=traceback.format_exc()[-3000:])

    if EXECUTAR_EM_SEGUNDO_PLANO:
        _fila.submit(tarefa)
    else:
        tarefa()


def _ocupado(id_projeto):
    if carregar(id_projeto)["estado"]["rodando"]:
        raise ErroEstudio("Este projeto já está processando algo. Espere terminar.")


def analisar(id_projeto):
    _ocupado(id_projeto)
    projeto = carregar(id_projeto)
    if not projeto["clipes"]:
        raise ErroEstudio("Envie pelo menos um vídeo antes de analisar.")

    def trabalho(progresso):
        p = carregar(id_projeto)
        analise_mod.analisar_job(p, pasta(id_projeto), progresso)
        atualizar(id_projeto, lambda x: x.update(analise_desatualizada=False))

    _executar(id_projeto, "analise", trabalho)


def planejar(id_projeto, modo):
    _ocupado(id_projeto)
    carregar_analise(id_projeto)
    if modo == "api":
        planejador_ia.verificar_disponibilidade()
    elif modo != "demonstrativo":
        raise ErroEstudio("Modo de plano inválido.")

    def trabalho(progresso):
        p = carregar(id_projeto)
        if p["analise_desatualizada"]:
            raise ErroEstudio("Os clipes mudaram depois da última análise. Toque em 'Analisar clipes' de novo.")
        analise = carregar_analise(id_projeto)
        if modo == "demonstrativo":
            progresso("Montando plano demonstrativo (sem IA)")
            novo = planejador_demo.gerar_plano(p, analise)
        else:
            progresso(f"Pedindo o plano ao modelo {config.MODELO_IA} (pode levar alguns minutos)")
            novo, custo = planejador_ia.gerar_plano(p, analise, pasta(id_projeto))
            atualizar(id_projeto, lambda x: x.update(ultimo_custo_ia_usd=custo))
        erros = plano_mod.validar(novo, {c["arquivo"]: c["metadados"]["duracao_s"] for c in analise["clipes"]})
        if erros:
            raise ErroEstudio("O plano gerado não passou na validação:\n- " + "\n- ".join(erros))
        plano_mod.salvar(novo, caminho_plano(id_projeto))

    _executar(id_projeto, "plano", trabalho)


def renderizar(id_projeto):
    _ocupado(id_projeto)
    plano, erros = ler_plano(id_projeto)
    if plano is None and not erros:
        raise ErroEstudio("Gere ou carregue um plano de edição antes de montar o vídeo.")
    if erros:
        raise ErroEstudio("O plano tem problemas:\n- " + "\n- ".join(erros))

    def trabalho(progresso):
        base = pasta(id_projeto)
        p = carregar(id_projeto)
        saida = base / "saida" / "pacote_capcut"
        (base / "saida" / "pacote_capcut.zip").unlink(missing_ok=True)
        temp = base / "saida" / "_temp"
        try:
            estilo = renderizador.ler_estilo(base / "estilo_textos.json")
            resumo = renderizador.renderizar(plano, base / "originais", saida, temp, progresso, estilo)
            progresso("Montando o pacote para o CapCut")
            analise = carregar_analise(id_projeto) if (base / "analise" / "analise.json").exists() else {"clipes": []}
            pacote.gerar_pacote(plano, analise, resumo, p, saida)
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    _executar(id_projeto, "render", trabalho)


def resultados(id_projeto):
    base = pasta(id_projeto) / "saida"
    saida = base / "pacote_capcut"
    if not (saida / "reels_preview.mp4").exists() or not (base / "pacote_capcut.zip").exists():
        return None
    arquivos = sorted(str(a.relative_to(base)) for a in saida.rglob("*") if a.is_file())
    return {"zip": "saida/pacote_capcut.zip", "arquivos": ["saida/" + a for a in arquivos]}
