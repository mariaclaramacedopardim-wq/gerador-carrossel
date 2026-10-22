"""Pacote de finalização para o CapCut: relatório, legendas, instruções e .zip."""

import json
import zipfile
from datetime import datetime
from pathlib import Path

from .analise import LIMITACOES
from .plano import linha_do_tempo

NOMES_PLANEJADOR = {
    "demonstrativo": "Planejador DEMONSTRATIVO (regras simples, sem IA)",
    "claude_code": "Claude Code (assinatura), usando a skill reels-creative-director",
    "api_anthropic": "API da Anthropic",
    "manual": "Plano escrito ou editado manualmente",
}


def _tempo_srt(segundos):
    ms = int(round(segundos * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def gerar_srt(itens):
    blocos = []
    for i, leg in enumerate(sorted(itens, key=lambda x: x["inicio_s"]), 1):
        blocos.append(f"{i}\n{_tempo_srt(leg['inicio_s'])} --> {_tempo_srt(leg['fim_s'])}\n{leg['texto'].strip()}\n")
    return "\n".join(blocos)


def _fmt(t):
    return f"{t:.2f}".replace(".", ",")


def gerar_relatorio(plano, analise, resumo_render, job):
    posicoes = {p["id"]: p for p in linha_do_tempo(plano)[0]}
    p, b = plano["planejador"], plano["briefing"]
    l = [
        f"# Relatório da montagem — {job['id']}",
        "",
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
        "",
        f"**Quem planejou:** {NOMES_PLANEJADOR[p['tipo']]}{' — modelo ' + p['modelo'] if p.get('modelo') else ''}.",
        "",
        f"> {p['observacao']}",
        "",
    ]
    if p["tipo"] == "demonstrativo":
        l += ["> ⚠️ **Este plano não foi decidido por IA.** As escolhas abaixo seguem regras fixas e servem para testar o fluxo "
              "e ter um primeiro corte. Revise tudo antes de publicar.", ""]
    l += [
        "## Briefing",
        f"- Objetivo: {b['objetivo'] or '—'}",
        f"- Estilo: {b['estilo'] or '—'}",
        f"- História: {b['historia'] or '—'}",
        f"- Duração pedida: {_fmt(b['duracao_alvo_s'])} s · duração da montagem: {_fmt(plano['duracao_total_estimada_s'])} s",
        f"- Proporção {b['proporcao']} · ritmo {b['ritmo']} · narração: {b['narracao'].replace('_', ' ')}",
        "",
        "## Cenas e cortes",
        "",
        "| # | No vídeo final | Arquivo de origem | Trecho usado | Papel | Objetivo narrativo | Enquadramento | Áudio | Entrada |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in sorted(plano["segmentos"], key=lambda s: s["ordem"]):
        pos = posicoes[s["id"]]
        audio = "mudo" if s["audio"]["modo"] == "mudo" else f"original {int(s['audio']['volume'] * 100)}%"
        vel = f" · {s['velocidade']}x" if s["velocidade"] != 1 else ""
        obrig = "" if s["obrigatorio"] else " [OPCIONAL]"
        l.append(
            f"| {s['ordem']} | {_fmt(pos['inicio_s'])}–{_fmt(pos['fim_s'])} s | {s['arquivo_origem']} | "
            f"{_fmt(s['inicio_s'])}–{_fmt(s['fim_s'])} s{vel} | {s['papel']}{obrig} | {s['objetivo_narrativo']} | "
            f"{s['enquadramento']['modo']} | {audio} | {s['transicao_entrada']['tipo']} |"
        )
    obs = [s for s in plano["segmentos"] if s["observacoes"]]
    if obs:
        l += ["", "**Observações por cena**", ""] + [f"- {s['id']}: {s['observacoes']}" for s in obs]

    l += ["", "## Textos na tela", ""]
    if plano["textos_na_tela"]:
        l += [f"- {t['id']} ({_fmt(t['inicio_s'])}–{_fmt(t['fim_s'])} s, {t['posicao']}): \"{t['texto']}\"" for t in plano["textos_na_tela"]]
    else:
        l.append("- Nenhum.")
    leg = plano["legendas"]
    l += ["", "## Legendas", ""]
    if leg["itens"]:
        estado = "revisadas" if leg["revisadas"] else "**NÃO revisadas** (transcrição automática: confira palavra por palavra)"
        l.append(f"- {len(leg['itens'])} legendas, fonte: {leg['fonte'].replace('_', ' ')}, {estado}. Arquivo: captions.srt.")
    else:
        l.append("- Sem legendas: não há transcrição disponível. Use as Legendas automáticas do CapCut.")

    ag, oe = plano["audio_geral"], plano["orientacoes_edicao"]
    l += [
        "", "## Áudio", f"- Música: {ag['musica']}", f"- Narração: {ag['narracao']}", f"- Efeitos sonoros: {ag['efeitos_sonoros']}",
        "", "## Transições, efeitos e tratamento visual", f"- {oe['transicoes_e_efeitos']}", f"- {oe['tratamento_visual']}",
        "", "## Avisos", "",
    ]
    avisos = plano["avisos"] + [{"tipo": "renderizacao", "segmento_id": None, "mensagem": a} for a in resumo_render["avisos_renderizacao"]]
    l += [f"- [{a['tipo']}{' · ' + a['segmento_id'] if a['segmento_id'] else ''}] {a['mensagem']}" for a in avisos] or ["- Nenhum."]
    if plano["clipes_nao_usados"]:
        l += ["", "## Clipes não usados", ""] + [f"- {c['arquivo']}: {c['motivo']}" for c in plano["clipes_nao_usados"]]

    l += ["", "## Ajustes recomendados no CapCut", ""] + [f"{i}. {a}" for i, a in enumerate(oe["ajustes_no_capcut"], 1)]

    l += ["", "## Verificação automática dos arquivos", "", "| Arquivo | Resolução | Duração | Codecs | Resultado |", "|---|---|---|---|---|"]
    for v in resumo_render["verificacao"]:
        ok = v["resolucao_ok"] and v["duracao_ok"] and v["codecs_ok"]
        l.append(f"| {v['arquivo']} | {v['largura']}x{v['altura']} | {_fmt(v['duracao_s'])} s (plano: {_fmt(v['duracao_plano_s'])} s) | "
                 f"{v['codec_video']} + {v['codec_audio']} | {'ok' if ok else 'conferir'} |")
    l += ["", "A verificação confere formato técnico. Ela não avalia se o vídeo está bom: isso depende de você assistir.", "",
          "## Limitações da análise", ""] + [f"- {t}" for t in LIMITACOES]
    return "\n".join(l) + "\n"


def gerar_textos(plano):
    linhas = ["TEXTOS NA TELA (copie e cole no CapCut: Texto > Adicionar texto)", ""]
    for t in plano["textos_na_tela"]:
        linhas += [f"{t['id']} · de {_fmt(t['inicio_s'])} s a {_fmt(t['fim_s'])} s · posição: {t['posicao']}", t["texto"], ""]
    if not plano["textos_na_tela"]:
        linhas.append("(nenhum texto no plano)")
    return "\n".join(linhas) + "\n"


README_CAPCUT = """# Como finalizar este Reels no CapCut (iPad)

## O que tem nesta pasta

| Arquivo | Para que serve |
|---|---|
| `reels_preview.mp4` | Montagem preliminar com os textos na tela. Serve para assistir e decidir. |
| `reels_base_sem_textos.mp4` | A mesma montagem **sem** textos. Use esta no CapCut para escrever os textos por lá. |
| `clips/` | Cada trecho cortado separadamente, numerado na ordem do plano (01, 02, 03...). |
| `edit_plan.json` | O plano completo da edição (tempos em segundos). |
| `shot_report.md` | O relatório: cenas, cortes, decisões, avisos e ajustes recomendados. |
| `textos_na_tela.txt` | Os textos do plano, prontos para copiar e colar. |
| `captions.srt` | Legendas com tempos (só existe quando houve transcrição). |

## Importante: não existe "projeto do CapCut" aqui

O CapCut não oferece uma forma oficial de importar uma linha do tempo pronta criada por outro programa.
Existem ferramentas não oficiais que escrevem o arquivo interno de projeto do CapCut para computador,
mas elas só funcionam no CapCut para Windows/Mac, dependem da versão e podem quebrar a qualquer atualização.
Por isso este pacote entrega **vídeos e arquivos de apoio**, e a finalização é feita por você no CapCut.

## Passo a passo no iPad

1. **Baixe o pacote** pelo botão "Baixar pacote (.zip)" do estúdio. No app **Arquivos**, toque no .zip para descompactar.
2. **Leve os vídeos para o app Fotos:** abra a pasta, toque e segure um vídeo > **Compartilhar** > **Salvar Vídeo**.
   Faça isso com `reels_base_sem_textos.mp4` ou com os vídeos da pasta `clips/` (ou com os dois).
3. Abra o CapCut e toque em **Novo projeto (New project)**.
4. Escolha um caminho:
   - **Caminho rápido:** selecione só `reels_base_sem_textos.mp4`. A montagem já vem pronta e você ajusta por cima.
   - **Caminho flexível:** selecione os vídeos de `clips/` **na ordem dos números** (01, 02, 03...). Cada trecho vira um clipe
     separado na linha do tempo, e você pode encurtar, trocar a ordem ou apagar trechos com facilidade.
5. Confira o formato em **Proporção/Formato (Ratio/Format)** > **9:16**.
6. **Textos:** abra `textos_na_tela.txt` no app Arquivos, copie cada texto e cole em **Texto > Adicionar texto** no tempo indicado.
7. **Legendas:** use **Legendas automáticas (Auto captions)** no CapCut, em Português, e revise palavra por palavra.
   O CapCut do iPhone/iPad não importa arquivos `.srt` (segundo a central de ajuda do CapCut, em 2026). O `captions.srt` pode ser
   importado no CapCut para computador ou na versão web (Legendas > Importar arquivo), ou servir de referência para corrigir as legendas.
8. **Áudio:** siga o `shot_report.md`. O estúdio **nunca** adiciona música: escolha no CapCut (Áudio > Sons) ou um áudio do Instagram na publicação.
9. **Cor:** ajustes leves em **Ajustar (Adjust)**, iguais em todos os clipes do mesmo local.
10. **Revise** (uma vez sem som, uma vez só ouvindo) e **exporte** em 1080p e 30 fps. Apague o clipe final com o logo do CapCut, se aparecer.

Os nomes dos menus do CapCut mudam entre versões. Se não achar um botão com esse nome exato, procure pelo ícone ou pela função equivalente.
"""


def gerar_pacote(plano, analise, resumo_render, job, pasta_saida):
    pasta_saida = Path(pasta_saida)
    (pasta_saida / "edit_plan.json").write_text(json.dumps(plano, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pasta_saida / "shot_report.md").write_text(gerar_relatorio(plano, analise, resumo_render, job), encoding="utf-8")
    (pasta_saida / "textos_na_tela.txt").write_text(gerar_textos(plano), encoding="utf-8")
    (pasta_saida / "README.md").write_text(README_CAPCUT, encoding="utf-8")
    srt = pasta_saida / "captions.srt"
    if plano["legendas"]["itens"]:
        srt.write_text(gerar_srt(plano["legendas"]["itens"]), encoding="utf-8")
    elif srt.exists():
        srt.unlink()

    zip_destino = pasta_saida.parent / "pacote_capcut.zip"
    with zipfile.ZipFile(zip_destino, "w") as z:
        for arquivo in sorted(pasta_saida.rglob("*")):
            if arquivo.is_file():
                metodo = zipfile.ZIP_STORED if arquivo.suffix == ".mp4" else zipfile.ZIP_DEFLATED
                z.write(arquivo, Path("pacote_capcut") / arquivo.relative_to(pasta_saida), compress_type=metodo)
    return zip_destino
