"""Análise técnica dos clipes brutos.

O que esta etapa faz (e o que NÃO faz):
- Lê metadados com o FFprobe (duração, resolução, rotação, fps, áudio, HDR).
- Extrai quadros amostrados e monta uma folha de contato por clipe.
- Detecta cortes de cena pela diferença entre quadros (filtro "scene" do FFmpeg).
- Detecta trechos com som e trechos silenciosos (filtro "silencedetect").
- Transcreve a fala SOMENTE se o pacote opcional faster-whisper estiver instalado.

Ela NÃO entende o conteúdo do vídeo. Os quadros são amostras; o que acontece
entre eles não é visto. "Som" não significa "fala": pode ser música ou ruído.
"""

import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat

from . import transcricao
from .ferramentas import ErroEstudio, ffprobe_json, rodar_ffmpeg

LIMITACOES = [
    "A análise visual usa quadros amostrados (até 12 por clipe, mais os pontos de corte de cena). "
    "O que acontece entre esses quadros não é visto por ninguém: nem pelo planejador demonstrativo, nem por um modelo de IA.",
    "A detecção de cena compara quadros vizinhos. Movimentos rápidos de câmera podem gerar cortes falsos, "
    "e mudanças lentas de luz podem passar despercebidas.",
    "\"Trecho com som\" significa apenas que o volume passou de um limite. Pode ser fala, música, vento ou ruído.",
    "Sem transcrição, ninguém sabe o que é dito nos clipes. Marque os clipes e descreva-os na interface para orientar o plano.",
]


def _numero(valor, padrao=None):
    try:
        if valor in (None, "N/A", ""):
            return padrao
        if isinstance(valor, str) and "/" in valor:
            num, den = valor.split("/")
            den = float(den)
            return float(num) / den if den else padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _rotacao(stream):
    for dado in stream.get("side_data_list", []) or []:
        if "rotation" in dado:
            return int(round(_numero(dado["rotation"], 0))) % 360
    tags = stream.get("tags", {}) or {}
    if "rotate" in tags:
        return int(round(_numero(tags["rotate"], 0))) % 360
    return 0


def ler_metadados(caminho):
    """Lê os metadados técnicos de um vídeo. Lança ErroEstudio se não for vídeo."""
    dados = ffprobe_json(caminho)
    streams = dados.get("streams", [])
    video = next(
        (s for s in streams if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")),
        None,
    )
    if video is None:
        raise ErroEstudio(f"'{Path(caminho).name}' não tem trilha de vídeo.")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duracao = _numero((dados.get("format") or {}).get("duration")) or _numero(video.get("duration"))
    if not duracao or duracao <= 0:
        raise ErroEstudio(f"Não consegui descobrir a duração de '{Path(caminho).name}'. O arquivo pode estar incompleto.")

    largura, altura = int(video.get("width") or 0), int(video.get("height") or 0)
    rotacao = _rotacao(video)
    if rotacao in (90, 270):
        largura, altura = altura, largura
    if largura <= 0 or altura <= 0:
        raise ErroEstudio(f"Não consegui ler a resolução de '{Path(caminho).name}'.")

    fps_real = _numero(video.get("r_frame_rate"), 0) or 0
    fps_medio = _numero(video.get("avg_frame_rate"), 0) or fps_real
    transferencia = video.get("color_transfer") or ""

    if altura > largura * 1.05:
        orientacao = "vertical"
    elif largura > altura * 1.05:
        orientacao = "horizontal"
    else:
        orientacao = "quadrado"

    return {
        "duracao_s": round(duracao, 3),
        "largura": largura,
        "altura": altura,
        "rotacao": rotacao,
        "orientacao": orientacao,
        "fps": round(fps_medio, 3),
        "fps_variavel": bool(fps_real and fps_medio and abs(fps_real - fps_medio) > 0.5),
        "codec_video": video.get("codec_name"),
        "pix_fmt": video.get("pix_fmt"),
        "hdr": transferencia in ("arib-std-b67", "smpte2084"),
        "transferencia_cor": transferencia or None,
        "tem_audio": audio is not None,
        "codec_audio": audio.get("codec_name") if audio else None,
        "tamanho_mb": round(_numero((dados.get("format") or {}).get("size"), 0) / (1024 * 1024), 1),
    }


def detectar_cenas(caminho, limiar=0.30):
    """Retorna os instantes (s) em que o quadro muda bastante."""
    log = rodar_ffmpeg(
        ["-i", caminho, "-an", "-vf", f"fps=6,scale=320:-2,select='gt(scene,{limiar})',showinfo", "-f", "null", "-"]
    )
    tempos = [round(float(t), 2) for t in re.findall(r"pts_time:([0-9.]+)", log)]
    filtrados = []
    for t in tempos:
        if not filtrados or t - filtrados[-1] > 0.5:
            filtrados.append(t)
    return filtrados


def detectar_som(caminho, duracao, ruido_db=-35, minimo_silencio=0.4):
    """Retorna (trechos_com_som, volume_medio_db, volume_max_db)."""
    log = rodar_ffmpeg(
        ["-i", caminho, "-vn", "-af", f"silencedetect=noise={ruido_db}dB:d={minimo_silencio},volumedetect", "-f", "null", "-"]
    )
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", log)]
    fins = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    silencios = []
    for i, ini in enumerate(inicios):
        fim = fins[i] if i < len(fins) else duracao
        silencios.append((max(0.0, ini), min(duracao, fim)))

    trechos, cursor = [], 0.0
    for ini, fim in silencios:
        if ini - cursor > 0.25:
            trechos.append([round(cursor, 2), round(ini, 2)])
        cursor = fim
    if duracao - cursor > 0.25:
        trechos.append([round(cursor, 2), round(duracao, 2)])

    medio = re.search(r"mean_volume: (-?[0-9.]+) dB", log)
    maximo = re.search(r"max_volume: (-?[0-9.]+) dB", log)
    return trechos, (float(medio.group(1)) if medio else None), (float(maximo.group(1)) if maximo else None)


def _instantes_amostra(duracao, cenas, maximo=12):
    n = max(1, min(maximo, math.ceil(duracao / 1.5)))
    passo = duracao / n
    tempos = [round(passo * (i + 0.5), 2) for i in range(n)]
    for c in cenas:
        alvo = min(duracao - 0.05, c + 0.2)
        if all(abs(alvo - t) > 0.6 for t in tempos):
            tempos.append(round(alvo, 2))
    return sorted(tempos)[: maximo + 4]


def extrair_quadros(caminho, duracao, cenas, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    quadros = []
    for i, t in enumerate(_instantes_amostra(duracao, cenas)):
        destino = pasta / f"q{i:02d}_{t:07.2f}s.jpg"
        rodar_ffmpeg(["-ss", f"{t:.2f}", "-i", caminho, "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", destino])
        if destino.exists():
            with Image.open(destino) as img:
                brilho = ImageStat.Stat(img.convert("L")).mean[0]
            quadros.append({"tempo_s": t, "arquivo": destino.name, "brilho": round(brilho, 1)})
    return quadros


def _fonte(tamanho):
    from .ferramentas import encontrar_fonte

    caminho = encontrar_fonte()
    try:
        return ImageFont.truetype(caminho, tamanho) if caminho else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def montar_folha_contato(nome_clipe, quadros, pasta_quadros, destino, colunas=4, largura_celula=240):
    """Monta uma imagem com os quadros amostrados e o tempo de cada um."""
    if not quadros:
        return None
    imagens = [Image.open(pasta_quadros / q["arquivo"]).convert("RGB") for q in quadros]
    proporcao = imagens[0].height / imagens[0].width
    altura_celula = int(largura_celula * proporcao)
    linhas = math.ceil(len(imagens) / colunas)
    topo, rotulo = 44, 26
    folha = Image.new("RGB", (colunas * largura_celula, topo + linhas * (altura_celula + rotulo)), "white")
    desenho = ImageDraw.Draw(folha)
    desenho.text((10, 10), nome_clipe, fill="black", font=_fonte(22))
    fonte = _fonte(18)
    for i, (img, q) in enumerate(zip(imagens, quadros)):
        x = (i % colunas) * largura_celula
        y = topo + (i // colunas) * (altura_celula + rotulo)
        folha.paste(img.resize((largura_celula, altura_celula)), (x, y))
        desenho.text((x + 6, y + altura_celula + 3), f"t = {q['tempo_s']:.1f} s", fill="black", font=fonte)
        img.close()
    folha.thumbnail((1568, 1568))
    folha.save(destino, quality=85)
    return destino.name


def trechos_candidatos(duracao, cenas, trechos_som, transcricao_segmentos=None):
    """Divide o clipe em trechos que respeitam cortes de cena e pausas.

    Os trechos são apenas pontos de partida: começam e terminam em cortes de
    cena, pausas de som ou frases da transcrição, para não cortar no meio de
    uma ação ou de uma fala quando isso pode ser evitado.
    """
    limites = [0.0, *[c for c in cenas if 0.3 < c < duracao - 0.3], duracao]
    planos = [(limites[i], limites[i + 1]) for i in range(len(limites) - 1)]
    candidatos = []
    for ini_plano, fim_plano in planos:
        antes = len(candidatos)
        if transcricao_segmentos:
            falas = [
                (max(ini_plano, s["inicio_s"]), min(fim_plano, s["fim_s"]), s["texto"])
                for s in transcricao_segmentos
                if s["fim_s"] > ini_plano and s["inicio_s"] < fim_plano
            ]
            for ini, fim, texto in falas:
                candidatos.append(_candidato(ini - 0.15, fim + 0.2, duracao, "fala transcrita", True, texto))
        else:
            sons = [(max(ini_plano, a), min(fim_plano, b)) for a, b in trechos_som if b > ini_plano and a < fim_plano]
            for ini, fim in sons:
                candidatos.append(_candidato(ini - 0.15, fim + 0.2, duracao, "trecho com som entre pausas", True))
        if len(candidatos) == antes:
            candidatos.append(_candidato(ini_plano, fim_plano, duracao, "plano sem som relevante (bom para B-roll)", False))
    candidatos = [c for c in candidatos if c["duracao_s"] >= 0.8]
    for i, c in enumerate(candidatos, 1):
        c["id"] = f"C{i:02d}"
    return candidatos


def _candidato(ini, fim, duracao, motivo, tem_som, texto=None):
    ini, fim = max(0.0, round(ini, 2)), min(duracao, round(fim, 2))
    c = {"inicio_s": ini, "fim_s": fim, "duracao_s": round(fim - ini, 2), "tem_som": tem_som, "motivo": motivo}
    if texto:
        c["fala"] = texto
    return c


def avisos_do_clipe(meta, quadros, volume_medio):
    avisos = []
    if meta["largura"] * meta["altura"] < 1280 * 720:
        avisos.append("Resolução baixa: pode ficar sem nitidez em 1080x1920.")
    if meta["orientacao"] == "horizontal":
        avisos.append("Clipe horizontal: para 9:16 será cortado nas laterais ou mostrado inteiro com fundo desfocado.")
    if meta["fps_variavel"]:
        avisos.append("Taxa de quadros variável (comum no iPhone): a montagem converte para 30 fps.")
    if meta["hdr"]:
        avisos.append("Vídeo em HDR: as cores podem mudar na conversão para SDR. Confira a cor no CapCut.")
    if not meta["tem_audio"]:
        avisos.append("Clipe sem áudio.")
    elif volume_medio is not None and volume_medio < -40:
        avisos.append("Áudio muito baixo: a fala pode não ser compreendida.")
    escuros = [q for q in quadros if q["brilho"] < 35]
    if quadros and len(escuros) > len(quadros) / 2:
        avisos.append("Imagem escura na maior parte dos quadros amostrados.")
    return avisos


def analisar_clipe(caminho, pasta_saida, transcrever=True):
    caminho = Path(caminho)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    meta = ler_metadados(caminho)
    cenas = detectar_cenas(caminho)
    if meta["tem_audio"]:
        trechos_som, vol_medio, vol_max = detectar_som(caminho, meta["duracao_s"])
    else:
        trechos_som, vol_medio, vol_max = [], None, None

    transc = None
    if transcrever and meta["tem_audio"] and trechos_som:
        transc = transcricao.transcrever(caminho, pasta_saida / "transcricao.json")

    quadros = extrair_quadros(caminho, meta["duracao_s"], cenas, pasta_saida / "quadros")
    folha = montar_folha_contato(caminho.name, quadros, pasta_saida / "quadros", pasta_saida / "folha_contato.jpg")
    candidatos = trechos_candidatos(meta["duracao_s"], cenas, trechos_som, transc["segmentos"] if transc else None)

    return {
        "arquivo": caminho.name,
        "metadados": meta,
        "cortes_de_cena_s": cenas,
        "trechos_com_som_s": trechos_som,
        "volume_medio_db": vol_medio,
        "volume_max_db": vol_max,
        "quadros": quadros,
        "folha_contato": folha,
        "transcricao": transc,
        "candidatos": candidatos,
        "avisos": avisos_do_clipe(meta, quadros, vol_medio),
    }


def escrever_contexto_para_ia(job, analise, destino):
    """Resumo em Markdown para um modelo de IA (ou para o Claude Code) planejar a edição."""
    b = job["briefing"]
    linhas = [
        f"# Contexto para planejar o Reels — projeto {job['id']}",
        "",
        "## Briefing da criadora",
        f"- Objetivo: {b.get('objetivo') or '(não informado)'}",
        f"- Estilo: {b.get('estilo') or '(não informado)'}",
        f"- História: {b.get('historia') or '(não informada)'}",
        f"- Duração desejada: {b.get('duracao_alvo_s')} s",
        f"- Proporção: {b.get('proporcao')} | clipes de outra orientação: {b.get('tratamento_orientacao')}",
        f"- Ritmo: {b.get('ritmo')} | narração: {b.get('narracao')}",
        "",
        "## Limitações desta análise (leia antes de planejar)",
        *[f"- {t}" for t in LIMITACOES],
        "",
        "## Clipes (na ordem escolhida pela criadora)",
    ]
    por_nome = {c["arquivo"]: c for c in analise["clipes"]}
    for clipe in job["clipes"]:
        a = por_nome.get(clipe["arquivo"])
        if not a:
            continue
        m = a["metadados"]
        linhas += [
            "",
            f"### {clipe['arquivo']} — {'INDISPENSÁVEL' if clipe.get('indispensavel') else 'opcional'}",
            f"- Descrição da criadora: {clipe.get('descricao') or '(sem descrição)'}",
            f"- {m['duracao_s']} s, {m['largura']}x{m['altura']} ({m['orientacao']}), {m['fps']} fps, "
            f"áudio: {'sim' if m['tem_audio'] else 'não'}, volume médio: {a['volume_medio_db']} dB",
            f"- Folha de contato: analise/{Path(clipe['arquivo']).stem}/{a['folha_contato']}",
            f"- Cortes de cena (s): {a['cortes_de_cena_s'] or 'nenhum detectado'}",
            f"- Trechos com som (s): {a['trechos_com_som_s'] or 'nenhum'}",
        ]
        if a["avisos"]:
            linhas.append(f"- Avisos: {'; '.join(a['avisos'])}")
        if a["transcricao"]:
            linhas.append("- Transcrição automática (NÃO revisada):")
            linhas += [f"  - [{s['inicio_s']:.1f}–{s['fim_s']:.1f}] {s['texto']}" for s in a["transcricao"]["segmentos"]]
        else:
            linhas.append("- Transcrição: indisponível (o conteúdo falado é desconhecido).")
        linhas.append("- Trechos candidatos:")
        linhas += [
            f"  - {c['id']}: {c['inicio_s']:.2f}–{c['fim_s']:.2f} s ({c['duracao_s']:.1f} s) — {c['motivo']}"
            for c in a["candidatos"]
        ]
    Path(destino).write_text("\n".join(linhas) + "\n", encoding="utf-8")


def analisar_job(job, pasta_job, ao_progredir=lambda texto: None):
    clipes = []
    for i, clipe in enumerate(job["clipes"], 1):
        ao_progredir(f"Analisando clipe {i} de {len(job['clipes'])}: {clipe['arquivo']}")
        origem = pasta_job / "originais" / clipe["arquivo"]
        clipes.append(analisar_clipe(origem, pasta_job / "analise" / Path(clipe["arquivo"]).stem))
    analise = {"limitacoes": LIMITACOES, "transcricao_disponivel": transcricao.disponivel(), "clipes": clipes}
    (pasta_job / "analise" / "analise.json").write_text(json.dumps(analise, ensure_ascii=False, indent=2), encoding="utf-8")
    escrever_contexto_para_ia(job, analise, pasta_job / "analise" / "contexto_para_ia.md")
    return analise
