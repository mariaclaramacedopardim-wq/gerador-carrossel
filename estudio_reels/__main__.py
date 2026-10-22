"""Linha de comando do estúdio (atalho: bash estudio_reels/rodar.sh ...).

python -m estudio_reels                      inicia a interface web (porta 8000)
python -m estudio_reels sistema              confere FFmpeg, fontes, transcrição e API
python -m estudio_reels projetos             lista os projetos
python -m estudio_reels exemplo              cria e processa um projeto com vídeos sintéticos
python -m estudio_reels analisar ID          analisa os clipes de um projeto
python -m estudio_reels planejar ID [api]    gera o plano (demonstrativo ou pela API)
python -m estudio_reels validar ID|ARQUIVO   valida um edit_plan.json
python -m estudio_reels renderizar ID        gera o MP4 e o pacote do CapCut

Fluxo autônomo (vídeos que já estão no disco, por exemplo anexos do chat):
python -m estudio_reels importar [--nome N] [--briefing B.json] VIDEO...   cria o projeto
python -m estudio_reels auto ID [--replanejar] [--pedido TEXTO]            analisa, planeja se preciso, renderiza e guarda vN
python -m estudio_reels versoes ID                                         lista as versões geradas
python -m estudio_reels restaurar ID VIDEO...                              retoma um projeto da memória em outra sessão
"""

import json
import sys
from pathlib import Path

from . import projetos
from .ferramentas import ErroEstudio, estado_do_sistema


def _mostrar_estado(id_projeto):
    estado = projetos.carregar(id_projeto)["estado"]
    if estado["erro"]:
        print("ERRO:", estado["erro"])
        if estado.get("detalhe"):
            print(estado["detalhe"])
        return 1
    print("OK:", estado["etapa"])
    return 0


def main(argumentos):
    projetos.EXECUTAR_EM_SEGUNDO_PLANO = False
    comando = argumentos[0] if argumentos else "servidor"
    try:
        if comando == "servidor":
            from .app import iniciar

            iniciar()
        elif comando == "sistema":
            print(json.dumps(estado_do_sistema(), ensure_ascii=False, indent=2))
        elif comando == "projetos":
            for p in projetos.listar():
                print(f"{p['id']}  {p['clipes']} clipe(s)  {p['nome']}")
        elif comando == "exemplo":
            from .amostras import criar_projeto_exemplo

            p = criar_projeto_exemplo()
            print("Projeto criado:", p["id"])
            for etapa in (projetos.analisar, lambda i: projetos.planejar(i, "demonstrativo"), projetos.renderizar):
                etapa(p["id"])
                if _mostrar_estado(p["id"]):
                    return 1
            print("Resultados em:", projetos.pasta(p["id"]) / "saida")
        elif comando == "analisar":
            projetos.analisar(argumentos[1])
            return _mostrar_estado(argumentos[1])
        elif comando == "planejar":
            modo = "api" if len(argumentos) > 2 and argumentos[2] == "api" else "demonstrativo"
            projetos.planejar(argumentos[1], modo)
            return _mostrar_estado(argumentos[1])
        elif comando == "validar":
            alvo = argumentos[1]
            if Path(alvo).is_file():
                from . import plano

                erros = plano.validar(plano.carregar(alvo))
            else:
                _, erros = projetos.ler_plano(alvo)
                if not projetos.caminho_plano(alvo).exists():
                    erros = [f"Não existe {projetos.caminho_plano(alvo)}"]
            if erros:
                print("O plano tem problemas:")
                for e in erros:
                    print(" -", e)
                return 1
            print("Plano válido.")
        elif comando == "renderizar":
            projetos.renderizar(argumentos[1])
            return _mostrar_estado(argumentos[1])
        elif comando in ("importar", "auto", "versoes", "restaurar"):
            return _fluxo(comando, argumentos[1:])
        else:
            print(__doc__)
            return 1
    except (ErroEstudio, ValueError) as e:
        print("ERRO:", getattr(e, "mensagem", str(e)))
        return 1
    except IndexError:
        print(__doc__)
        return 1
    return 0


def _opcao(argumentos, nome, com_valor=True):
    """Tira --nome [valor] da lista e devolve o valor (ou True/None)."""
    if nome not in argumentos:
        return None
    i = argumentos.index(nome)
    if not com_valor:
        del argumentos[i]
        return True
    valor = argumentos[i + 1]
    del argumentos[i:i + 2]
    return valor


def _fluxo(comando, argumentos):
    from . import fluxo

    if comando == "importar":
        nome = _opcao(argumentos, "--nome") or ""
        arquivo_briefing = _opcao(argumentos, "--briefing")
        briefing = json.loads(Path(arquivo_briefing).read_text(encoding="utf-8")) if arquivo_briefing else None
        p = fluxo.importar(argumentos, nome, briefing)
        print("Projeto criado:", p["id"])
        for c in p["clipes"]:
            m = c["metadados"]
            print(f"  {c['arquivo']}: {m['duracao_s']} s, {m['largura']}x{m['altura']}, áudio: {'sim' if m['tem_audio'] else 'não'}")
        print("Memória:", fluxo.pasta_memoria(p["id"]))
    elif comando == "auto":
        replanejar = bool(_opcao(argumentos, "--replanejar", com_valor=False))
        pedido = _opcao(argumentos, "--pedido")
        destino = fluxo.auto(argumentos[0], replanejar=replanejar, pedido=pedido)
        print("Versão pronta:", destino)
    elif comando == "versoes":
        for v in fluxo.versoes(argumentos[0]):
            print(v)
    elif comando == "restaurar":
        p, ultima = fluxo.restaurar(argumentos[0], argumentos[1:])
        print("Projeto restaurado:", p["id"], "| último plano:", ultima or "nenhum")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
