"""Planejador DEMONSTRATIVO: regras simples, sem inteligência artificial.

Serve para testar o fluxo de ponta a ponta sem pagar API. Ele não entende o
vídeo nem o briefing: segue a ordem dos clipes escolhida pela criadora, prioriza
os clipes marcados como indispensáveis, evita cortar no meio de um trecho com som
e respeita a duração e o ritmo pedidos. Todo plano gerado aqui sai marcado como
"demonstrativo" no JSON, no relatório e na interface.
"""

import re

from . import config
from .plano import linha_do_tempo

RITMO = {
    "rapido": {"ideal": 2.5, "maximo": 3.5},
    "medio": {"ideal": 4.0, "maximo": 6.0},
    "lento": {"ideal": 6.0, "maximo": 9.0},
}

OBSERVACAO = (
    "Plano DEMONSTRATIVO gerado por regras simples, sem IA. Ele não entende o conteúdo dos clipes nem o "
    "briefing: segue a ordem dos clipes, prioriza os indispensáveis, evita cortar trechos com som e respeita "
    "a duração e o ritmo. Revise a escolha de trechos, os textos e o objetivo de cada cena."
)


def _texto_gancho(briefing):
    base = (briefing.get("historia") or briefing.get("objetivo") or "").strip()
    if not base:
        return None
    frase = re.split(r"[.!?\n]", base)[0].strip()
    palavras = frase.split()
    texto = " ".join(palavras[:7])
    return texto + ("…" if len(palavras) > 7 else "")


def _pontuar(candidato, narracao, ideal):
    pontos = -abs(candidato["duracao_s"] - ideal) / ideal
    if narracao == "fala_dos_clipes" and candidato["tem_som"]:
        pontos += 2
    if narracao != "fala_dos_clipes" and not candidato["tem_som"]:
        pontos += 1
    return pontos


def _orientacao_saida(proporcao):
    largura, altura = config.PROPORCOES[proporcao]
    return "vertical" if altura > largura * 1.05 else "quadrado" if abs(altura - largura) < 10 else "horizontal"


def gerar_plano(job, analise):
    b = job["briefing"]
    alvo = float(b["duracao_alvo_s"])
    ritmo = RITMO[b["ritmo"]]
    largura, altura = config.PROPORCOES[b["proporcao"]]
    por_nome = {c["arquivo"]: c for c in analise["clipes"]}
    clipes = [c for c in job["clipes"] if c["arquivo"] in por_nome]

    avisos, escolhidos = [], []  # escolhidos: (indice_clipe, candidato, prioridade)

    def melhores(clipe):
        candidatos = [c for c in por_nome[clipe["arquivo"]]["candidatos"] if c["duracao_s"] >= 1.0]
        # Pequena preferência pelos trechos mais cedo no clipe: costumam ser o começo da fala ou da ação.
        return sorted(candidatos, key=lambda c: -(_pontuar(c, b["narracao"], ritmo["ideal"]) - 0.15 * candidatos.index(c)))

    def duracao_prevista():
        return sum(min(c["duracao_s"], _limite(c)) for _, c, _ in escolhidos)

    def _limite(c):
        return ritmo["maximo"] * (1.6 if c["tem_som"] and b["narracao"] == "fala_dos_clipes" else 1.0)

    # 1) um trecho de cada clipe indispensável; 2) um de cada opcional enquanto couber; 3) trechos extras.
    for i, clipe in enumerate(clipes):
        if clipe.get("indispensavel") and melhores(clipe):
            escolhidos.append((i, melhores(clipe)[0], 0))
    for i, clipe in enumerate(clipes):
        if not clipe.get("indispensavel") and melhores(clipe) and duracao_prevista() < alvo:
            escolhidos.append((i, melhores(clipe)[0], 1))
    rodada = 1
    while duracao_prevista() < alvo * 0.95 and rodada < 6:
        adicionou = False
        for i, clipe in enumerate(clipes):
            if duracao_prevista() >= alvo * 0.95:
                break
            usados = [c for j, c, _ in escolhidos if j == i]
            livres = [c for c in melhores(clipe) if all(c["fim_s"] <= u["inicio_s"] or c["inicio_s"] >= u["fim_s"] for u in usados)]
            if livres:
                escolhidos.append((i, livres[0], 2))
                adicionou = True
        if not adicionou:
            break
        rodada += 1

    # Ordem narrativa = ordem dos clipes definida pela criadora e, dentro do clipe, ordem cronológica.
    escolhidos.sort(key=lambda e: (e[0], e[1]["inicio_s"]))

    segmentos = []
    for i, cand, prioridade in escolhidos:
        clipe = clipes[i]
        meta = por_nome[clipe["arquivo"]]["metadados"]
        inicio, fim = cand["inicio_s"], cand["fim_s"]
        observacoes = [f"Trecho candidato {cand['id']} ({cand['motivo']})."]
        if fim - inicio > _limite(cand):
            fim = round(inicio + _limite(cand), 2)
            if cand["tem_som"]:
                observacoes.append("Cortado antes do fim do trecho com som: confira se a fala não foi interrompida.")
        segmentos.append({"clipe": clipe, "meta": meta, "cand": cand, "inicio": inicio, "fim": fim,
                          "prioridade": prioridade, "observacoes": observacoes})

    # Se passou muito da duração pedida, retira trechos extras e opcionais do fim para o começo.
    def total():
        return sum(s["fim"] - s["inicio"] for s in segmentos)

    for prioridade in (2, 1):
        while total() > alvo * 1.1 and len(segmentos) > 1:
            removiveis = [s for s in segmentos if s["prioridade"] == prioridade]
            # Só retira um trecho inteiro se o vídeo continuar perto da duração pedida; senão, encurta (abaixo).
            if not removiveis or total() - (removiveis[-1]["fim"] - removiveis[-1]["inicio"]) < alvo * 0.9:
                break
            segmentos.remove(removiveis[-1])
    if total() > alvo * 1.1:
        excesso = total() - alvo
        for s in sorted(segmentos, key=lambda s: -(s["fim"] - s["inicio"])):
            folga = (s["fim"] - s["inicio"]) - 1.5
            corte = min(folga, excesso)
            if corte > 0:
                s["fim"] = round(s["fim"] - corte, 2)
                excesso -= corte
                if s["cand"]["tem_som"]:
                    s["observacoes"].append("Encurtado para caber na duração: confira se a fala não foi interrompida.")
            if excesso <= 0:
                break

    orient_saida = _orientacao_saida(b["proporcao"])
    plano_segmentos = []
    for n, s in enumerate(segmentos, 1):
        meta, cand, clipe = s["meta"], s["cand"], s["clipe"]
        sid = f"S{n:02d}"
        if n == 1:
            papel, objetivo = "gancho", "Abrir o vídeo. Confira se este trecho prende a atenção nos primeiros 1 a 3 segundos."
        elif n == len(segmentos):
            papel, objetivo = "conclusao", "Fechar o vídeo. Confira se este trecho entrega o que o gancho prometeu e leva ao CTA."
        elif not cand["tem_som"] and b["narracao"] == "fala_dos_clipes":
            papel, objetivo = "broll", "Imagem de apoio entre falas (escolhida por não ter som relevante)."
        else:
            papel, objetivo = "desenvolvimento", "Desenvolver a história na ordem dos clipes."
        if clipe.get("descricao"):
            objetivo += f" Descrição da criadora para o clipe: {clipe['descricao']}"
        modo = "preencher" if meta["orientacao"] == orient_saida else b["tratamento_orientacao"]
        if not meta["tem_audio"]:
            audio = {"modo": "mudo", "volume": 0}
        elif b["narracao"] == "fala_dos_clipes":
            audio = {"modo": "original", "volume": 1.0}
        else:
            audio = {"modo": "original", "volume": 0.3}
            s["observacoes"].append("Som original baixo (30%) para deixar espaço para narração ou música no CapCut.")
        plano_segmentos.append({
            "id": sid,
            "ordem": n,
            "arquivo_origem": clipe["arquivo"],
            "inicio_s": round(s["inicio"], 2),
            "fim_s": round(s["fim"], 2),
            "duracao_s": round(s["fim"] - s["inicio"], 2),
            "papel": papel,
            "objetivo_narrativo": objetivo,
            "obrigatorio": bool(clipe.get("indispensavel")),
            "enquadramento": {"modo": modo, "foco_x": 0.5, "foco_y": 0.5, "zoom": 1.0},
            "audio": audio,
            "velocidade": 1.0,
            "transicao_entrada": {"tipo": "corte", "duracao_s": 0},
            "tratamento_visual": "Sem filtro. Cor original do clipe.",
            "observacoes": " ".join(s["observacoes"]),
        })
        if meta["orientacao"] != orient_saida:
            if modo == "preencher":
                msg = f"{clipe['arquivo']} é {meta['orientacao']}: será cortado para preencher a tela. Confira se ninguém fica fora do quadro (ajuste foco_x)."
            else:
                msg = f"{clipe['arquivo']} é {meta['orientacao']}: aparece inteiro, com {'fundo desfocado' if modo == 'encaixar_desfocado' else 'faixas pretas'}."
            avisos.append({"tipo": "enquadramento", "segmento_id": sid, "mensagem": msg})
        for texto in por_nome[clipe["arquivo"]]["avisos"]:
            if "horizontal" not in texto.lower():
                tipo = "audio" if "áudio" in texto.lower() else "qualidade"
                avisos.append({"tipo": tipo, "segmento_id": sid, "mensagem": f"{clipe['arquivo']}: {texto}"})
        if "interrompida" in plano_segmentos[-1]["observacoes"]:
            avisos.append({"tipo": "corte", "segmento_id": sid, "mensagem": "O corte pode interromper uma fala. Ouça este trecho com atenção."})

    plano = {
        "versao_esquema": "1.0",
        "planejador": {"tipo": "demonstrativo", "modelo": None, "observacao": OBSERVACAO},
        "briefing": {k: b[k] for k in ("objetivo", "estilo", "historia", "duracao_alvo_s", "proporcao", "tratamento_orientacao", "ritmo", "narracao")},
        "formato_saida": {"largura": largura, "altura": altura, "fps": config.FPS_SAIDA},
        "segmentos": plano_segmentos,
        "textos_na_tela": [],
        "legendas": {"fonte": "nenhuma", "revisadas": False, "queimar_no_preview": False, "itens": []},
        "audio_geral": _audio_geral(b["narracao"]),
        "orientacoes_edicao": {
            "transicoes_e_efeitos": "Cortes secos entre todos os trechos (padrão profissional). Nenhuma transição ou efeito foi adicionado. "
                                    "Use transição só onde houver mudança de lugar ou de tempo.",
            "tratamento_visual": "Nenhum filtro foi aplicado. No CapCut, faça ajustes leves (contraste +5 a +15, saturação 0 a +10) "
                                 "e aplique o mesmo ajuste a todos os clipes do mesmo local.",
            "ajustes_no_capcut": [
                "Revise o início e o fim de cada trecho: o planejador demonstrativo não sabe onde a ação ou a fala começa de verdade.",
                "Troque o texto do gancho pelo texto final do roteiro (no máximo cerca de 7 palavras por tela).",
                "Gere legendas automáticas no CapCut e revise palavra por palavra.",
                "Assista uma vez sem som (os textos contam a história?) e uma vez só ouvindo (a voz está clara?).",
                "Remova o clipe final com logo do CapCut, se aparecer, e exporte em 1080p e 30 fps.",
            ],
        },
        "avisos": avisos,
        "clipes_nao_usados": [],
        "duracao_total_estimada_s": 0,
    }
    posicoes, total_final = linha_do_tempo(plano)
    plano["duracao_total_estimada_s"] = total_final

    texto = _texto_gancho(b)
    if texto:
        fim_texto = min(3.0, posicoes[0]["fim_s"])
        plano["textos_na_tela"].append({"id": "T01", "texto": texto, "inicio_s": 0, "fim_s": round(fim_texto, 2),
                                        "posicao": "topo", "segmento_id": "S01"})
        avisos.append({"tipo": "conteudo", "segmento_id": "S01",
                       "mensagem": "O texto do gancho foi copiado do início do briefing. Substitua pelo texto final do roteiro."})

    plano["legendas"] = _legendas(plano, posicoes, por_nome, b["narracao"])

    usados = {s["arquivo_origem"] for s in plano_segmentos}
    for clipe in clipes:
        if clipe["arquivo"] not in usados:
            plano["clipes_nao_usados"].append({"arquivo": clipe["arquivo"], "motivo": "Não coube na duração pedida (clipe opcional) ou não tem trecho com pelo menos 1 s."})
    for clipe in job["clipes"]:
        if clipe["arquivo"] not in por_nome:
            plano["clipes_nao_usados"].append({"arquivo": clipe["arquivo"], "motivo": "Clipe não analisado."})

    if total_final < alvo * 0.8:
        avisos.append({"tipo": "duracao", "segmento_id": None,
                       "mensagem": f"A montagem tem {total_final:.1f} s, bem menos que os {alvo:.0f} s pedidos: faltou material utilizável."})
    elif total_final > alvo * 1.15:
        avisos.append({"tipo": "duracao", "segmento_id": None,
                       "mensagem": f"A montagem tem {total_final:.1f} s, mais que os {alvo:.0f} s pedidos, para não descartar trechos indispensáveis."})
    return plano


def _audio_geral(narracao):
    musica = ("Nenhuma música foi adicionada. Se quiser música, escolha no CapCut (Áudio > Sons) ou um áudio do Instagram "
              "na hora de publicar. Sob fala, deixe a música entre 10% e 20%.")
    if narracao == "fala_dos_clipes":
        narr = "A fala vem do som original dos clipes. Confira se cada frase está completa e compreensível."
    elif narracao == "narracao_off":
        narr = "Grave a narração no CapCut (Áudio > Narração) por cima da montagem. O som original ficou em 30%."
    else:
        narr = "Vídeo sem fala: a história precisa ser contada pelas imagens e pelos textos na tela."
    return {"musica": musica, "narracao": narr, "efeitos_sonoros": "Nenhum efeito sonoro foi adicionado. Se usar, poucos (3 a 5 em 30 s), alinhados a cortes ou textos."}


def _legendas(plano, posicoes, por_nome, narracao):
    vazio = {"fonte": "nenhuma", "revisadas": False, "queimar_no_preview": False, "itens": []}
    if narracao != "fala_dos_clipes":
        return vazio
    itens = []
    for seg, pos in zip(plano["segmentos"], posicoes):
        transc = por_nome[seg["arquivo_origem"]].get("transcricao")
        if not transc:
            continue
        for frase in transc["segmentos"]:
            ini, fim = max(frase["inicio_s"], seg["inicio_s"]), min(frase["fim_s"], seg["fim_s"])
            if fim - ini < 0.3:
                continue
            itens.append({
                "inicio_s": round(pos["inicio_s"] + (ini - seg["inicio_s"]) / seg["velocidade"], 2),
                "fim_s": round(pos["inicio_s"] + (fim - seg["inicio_s"]) / seg["velocidade"], 2),
                "texto": frase["texto"],
            })
    if not itens:
        return vazio
    return {"fonte": "transcricao_automatica", "revisadas": False, "queimar_no_preview": False, "itens": itens}
