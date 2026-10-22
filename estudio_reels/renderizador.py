"""Transforma o plano de edição em vídeo com o FFmpeg.

Etapas:
1. Cada segmento vira um MP4 já cortado e enquadrado (clips/01_gancho.mp4...).
   Os originais nunca são alterados.
2. Os segmentos são unidos em reels_base_sem_textos.mp4 (cortes secos ou as
   transições pedidas no plano).
3. Os textos na tela (e, se pedido, as legendas) são desenhados por cima em
   reels_preview.mp4.
"""

import json
import math
import shutil
import textwrap
from pathlib import Path

from . import analise
from .ferramentas import ErroEstudio, garantir_espaco, rodar_ffmpeg, tem_filtro, encontrar_fonte, ffprobe_json
from .plano import duracao_transicao, linha_do_tempo, validar

CODIFICACAO_VIDEO = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
CODIFICACAO_AUDIO = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
BYTES_POR_SEGUNDO = 1_500_000  # estimativa folgada para 1080x1920 em CRF 20


def _par(n):
    return max(2, int(math.ceil(n / 2.0)) * 2)


def filtro_enquadramento(meta, enq, largura, altura, converter_hdr):
    """Ajusta o clipe à proporção de saída sem distorcer (sempre mantém a proporção original)."""
    partes = []
    if converter_hdr:
        partes.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    sw, sh, zoom = meta["largura"], meta["altura"], enq["zoom"]
    if enq["modo"] == "preencher":
        escala = max(largura / sw, altura / sh) * zoom
        nw, nh = _par(sw * escala), _par(sh * escala)
        x, y = round((nw - largura) * enq["foco_x"]), round((nh - altura) * enq["foco_y"])
        partes.append(f"scale={nw}:{nh}:flags=lanczos,crop={largura}:{altura}:{x}:{y}")
        return "[0:v]" + ",".join(partes + ["setsar=1"]) + "[v0]"

    escala = min(largura / sw, altura / sh) * zoom
    escala = min(escala, max(largura / sw, altura / sh))
    fw, fh = min(_par(sw * escala), largura), min(_par(sh * escala), altura)
    base = ",".join(partes) + "," if partes else ""
    if enq["modo"] == "encaixar_barras":
        return (f"[0:v]{base}scale={fw}:{fh}:flags=lanczos,pad={largura}:{altura}:(ow-iw)/2:(oh-ih)/2:black,setsar=1[v0]")
    # encaixar_desfocado: o próprio clipe, ampliado e desfocado, preenche o fundo.
    cobre = max(largura / sw, altura / sh)
    bw, bh = _par(sw * cobre / 4), _par(sh * cobre / 4)
    return (
        f"[0:v]{base}split=2[fundo][frente];"
        f"[fundo]scale={bw}:{bh},crop={_par(largura / 4)}:{_par(altura / 4)},boxblur=10:2,scale={largura}:{altura},eq=brightness=-0.08[fundo2];"
        f"[frente]scale={fw}:{fh}:flags=lanczos[frente2];"
        f"[fundo2][frente2]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]"
    )


def _cadeia_atempo(velocidade):
    filtros, v = [], velocidade
    while v > 2.0:
        filtros.append("atempo=2.0")
        v /= 2.0
    while v < 0.5:
        filtros.append("atempo=0.5")
        v /= 0.5
    filtros.append(f"atempo={v:.4f}")
    return ",".join(filtros)


def renderizar_segmento(seg, meta, caminho_origem, destino, formato):
    largura, altura, fps = formato["largura"], formato["altura"], formato["fps"]
    duracao_origem = seg["fim_s"] - seg["inicio_s"]
    duracao_saida = seg["duracao_s"]
    hdr = meta.get("hdr") and tem_filtro("zscale") and tem_filtro("tonemap")

    def montar(converter_hdr):
        video = filtro_enquadramento(meta, seg["enquadramento"], largura, altura, converter_hdr)
        video += f";[v0]setpts=(PTS-STARTPTS)/{seg['velocidade']},fps={fps},format=yuv420p[v]"
        argumentos = ["-ss", f"{seg['inicio_s']:.3f}", "-t", f"{duracao_origem:.3f}", "-i", caminho_origem]
        usar_original = seg["audio"]["modo"] == "original" and meta["tem_audio"] and seg["audio"]["volume"] > 0
        if usar_original:
            audio = f"[0:a]asetpts=PTS-STARTPTS,volume={seg['audio']['volume']}"
            if seg["velocidade"] != 1:
                audio += "," + _cadeia_atempo(seg["velocidade"])
            # Microfades de 20 ms evitam estalos nos cortes (não são efeito audível).
            audio += (f",aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{duracao_saida:.3f},"
                      f"afade=t=in:d=0.02,afade=t=out:st={max(0, duracao_saida - 0.02):.3f}:d=0.02[a]")
        else:
            argumentos += ["-f", "lavfi", "-t", f"{duracao_saida:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            audio = "[1:a]anull[a]"
        return argumentos + [
            "-filter_complex", video + ";" + audio,
            "-map", "[v]", "-map", "[a]", "-t", f"{duracao_saida:.3f}",
            *CODIFICACAO_VIDEO, "-r", str(fps), *CODIFICACAO_AUDIO, "-movflags", "+faststart", destino,
        ]

    try:
        rodar_ffmpeg(montar(hdr))
        return None
    except ErroEstudio:
        if not hdr:
            raise
        rodar_ffmpeg(montar(False))
        return "A conversão de HDR para SDR falhou; o trecho foi gerado sem conversão de cor. Confira a cor no CapCut."


def unir_segmentos(arquivos, plano, destino, pasta_temp):
    segmentos = sorted(plano["segmentos"], key=lambda s: s["ordem"])
    tem_transicao = any(duracao_transicao(s, i) > 0 for i, s in enumerate(segmentos))
    if not tem_transicao:
        lista = Path(pasta_temp) / "lista_concat.txt"
        lista.write_text("".join(f"file '{Path(a).resolve()}'\n" for a in arquivos), encoding="utf-8")
        rodar_ffmpeg(["-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", "-movflags", "+faststart", destino])
        return
    if not tem_filtro("xfade"):
        raise ErroEstudio("Este FFmpeg não tem o filtro de transições (xfade). Troque as transições do plano por 'corte'.")
    entradas, partes = [], []
    for a in arquivos:
        entradas += ["-i", a]
    v_atual, a_atual, cursor = "[0:v]", "[0:a]", segmentos[0]["duracao_s"]
    for i in range(1, len(segmentos)):
        s, d = segmentos[i], duracao_transicao(segmentos[i], i)
        v_saida, a_saida = f"[vx{i}]", f"[ax{i}]"
        if d > 0:
            tipo = "fade" if s["transicao_entrada"]["tipo"] == "dissolver" else "fadeblack"
            partes.append(f"{v_atual}[{i}:v]xfade=transition={tipo}:duration={d:.3f}:offset={cursor - d:.3f}{v_saida}")
            partes.append(f"{a_atual}[{i}:a]acrossfade=d={d:.3f}{a_saida}")
        else:
            partes.append(f"{v_atual}{a_atual}[{i}:v][{i}:a]concat=n=2:v=1:a=1{v_saida}{a_saida}")
        v_atual, a_atual = v_saida, a_saida
        cursor += s["duracao_s"] - d
    roteiro = Path(pasta_temp) / "filtro_uniao.txt"
    roteiro.write_text(";\n".join(partes), encoding="utf-8")
    rodar_ffmpeg([*entradas, "-filter_complex_script", roteiro, "-map", v_atual, "-map", a_atual,
                  *CODIFICACAO_VIDEO, "-r", str(plano["formato_saida"]["fps"]), *CODIFICACAO_AUDIO, "-movflags", "+faststart", destino])


def _escapar_caminho(caminho):
    return str(caminho).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


# Estilo dos textos na tela. O padrão é o de sempre (branco, caixa escura); um projeto pode trocar
# com o arquivo estilo_textos.json na pasta dele (ex.: fonte da identidade, sem caixa, sem sombra).
ESTILO_PADRAO = {"fonte": None, "cor": "white", "caixa": True, "contorno": True, "tamanho": 0.058, "entrelinha": 12, "maiusculas": False,
                 "centralizar_linhas": False, "escurecer_fundo": 0.0}


def ler_estilo(caminho):
    """Junta o estilo_textos.json do projeto (se existir) ao padrão. Fontes podem ser o nome de um arquivo em estudio_reels/fontes/."""
    estilo = dict(ESTILO_PADRAO)
    if caminho and Path(caminho).exists():
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        desconhecidos = set(dados) - set(ESTILO_PADRAO)
        if desconhecidos:
            raise ErroEstudio(f"estilo_textos.json tem campos desconhecidos: {', '.join(sorted(desconhecidos))}")
        estilo.update(dados)
    if estilo["fonte"]:
        fonte = Path(estilo["fonte"])
        if not fonte.is_absolute():
            fonte = Path(__file__).resolve().parent / "fontes" / fonte
        if not fonte.exists():
            raise ErroEstudio(f"A fonte do estilo de texto não existe: {fonte}")
        estilo["fonte"] = str(fonte)
    return estilo


def _drawtext(arquivo_texto, inicio, fim, posicao, formato, fonte, tamanho, caixa=True, cor="white", contorno=True, entrelinha=12,
              centralizar_linhas=False):
    altura = formato["altura"]
    y = {"topo": f"{int(altura * 0.12)}", "centro": "(h-text_h)/2", "inferior": f"{int(altura * 0.70)}-text_h"}[posicao]
    opcoes = [
        f"textfile='{_escapar_caminho(arquivo_texto)}'",
        f"fontsize={tamanho}", f"fontcolor={cor}", f"line_spacing={entrelinha}", "x=(w-text_w)/2", f"y={y}",
        f"enable='between(t,{inicio:.3f},{fim:.3f})'",
    ]
    if fonte:
        opcoes.insert(0, f"fontfile='{_escapar_caminho(fonte)}'")
    if centralizar_linhas and tem_filtro_opcao("drawtext", "text_align"):
        opcoes.append("text_align=C")
    if caixa:
        opcoes += ["box=1", "boxcolor=black@0.55", f"boxborderw={int(tamanho * 0.4)}"]
    elif contorno:
        opcoes += ["borderw=4", "bordercolor=black"]
    return "drawtext=" + ":".join(opcoes)


def tem_filtro_opcao(filtro, opcao):
    """Confere se o FFmpeg instalado aceita uma opção do filtro (ex.: text_align do drawtext, FFmpeg 6.1+)."""
    import subprocess

    r = subprocess.run(["ffmpeg", "-hide_banner", "-h", f"filter={filtro}"], capture_output=True, text=True)
    return f" {opcao} " in r.stdout


def desenhar_textos(base, plano, destino, pasta_temp, estilo=None):
    textos = plano["textos_na_tela"]
    legendas = plano["legendas"]["itens"] if plano["legendas"]["queimar_no_preview"] else []
    if not textos and not legendas:
        shutil.copy2(base, destino)
        return []
    if not tem_filtro("drawtext"):
        shutil.copy2(base, destino)
        return ["Este FFmpeg não desenha textos (falta o filtro drawtext). O preview saiu sem textos; adicione-os no CapCut."]
    estilo = estilo or ESTILO_PADRAO
    formato, fonte = plano["formato_saida"], estilo["fonte"] or encontrar_fonte()
    tamanho = max(24, int(formato["largura"] * estilo["tamanho"]))
    estilo_texto = {k: estilo[k] for k in ("cor", "contorno", "entrelinha", "centralizar_linhas")}
    caracteres = max(12, int(formato["largura"] * 0.9 / (tamanho * 0.55)))
    filtros = []
    pasta = Path(pasta_temp) / "textos"
    pasta.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(textos):
        arquivo = pasta / f"texto_{i:02d}.txt"
        texto = t["texto"].upper() if estilo["maiusculas"] else t["texto"]
        arquivo.write_text("\n".join(textwrap.wrap(texto, caracteres)), encoding="utf-8")
        filtros.append(_drawtext(arquivo, t["inicio_s"], t["fim_s"], t["posicao"], formato, fonte, tamanho, estilo["caixa"], **estilo_texto))
    for i, leg in enumerate(legendas):
        arquivo = pasta / f"legenda_{i:03d}.txt"
        arquivo.write_text("\n".join(textwrap.wrap(leg["texto"], int(caracteres * 1.2))), encoding="utf-8")
        filtros.append(_drawtext(arquivo, leg["inicio_s"], leg["fim_s"], "inferior", formato, fonte, int(tamanho * 0.75), False, **estilo_texto))
    roteiro = Path(pasta_temp) / "filtro_textos.txt"
    if estilo["escurecer_fundo"]:
        # Escurece o vídeo inteiro antes de desenhar os textos (só no preview com textos).
        filtros.insert(0, f"eq=brightness={-abs(float(estilo['escurecer_fundo'])):.3f}")
    roteiro.write_text(",\n".join(filtros), encoding="utf-8")
    rodar_ffmpeg(["-i", base, "-filter_script:v", roteiro, *CODIFICACAO_VIDEO, "-c:a", "copy", "-movflags", "+faststart", destino])
    return []


def verificar_saida(caminho, plano):
    """Confere resolução, codecs e duração do vídeo gerado."""
    dados = ffprobe_json(caminho)
    video = next(s for s in dados["streams"] if s["codec_type"] == "video")
    audio = next((s for s in dados["streams"] if s["codec_type"] == "audio"), None)
    _, esperado = linha_do_tempo(plano)
    duracao = float(dados["format"]["duration"])
    formato = plano["formato_saida"]
    return {
        "arquivo": Path(caminho).name,
        "largura": video["width"],
        "altura": video["height"],
        "codec_video": video["codec_name"],
        "codec_audio": audio["codec_name"] if audio else None,
        "duracao_s": round(duracao, 2),
        "duracao_plano_s": esperado,
        "resolucao_ok": video["width"] == formato["largura"] and video["height"] == formato["altura"],
        "duracao_ok": abs(duracao - esperado) <= 0.25,
        "codecs_ok": video["codec_name"] == "h264" and (audio or {}).get("codec_name") == "aac",
    }


def renderizar(plano, pasta_originais, pasta_saida, pasta_temp, ao_progredir=lambda texto: None, estilo=None):
    """Gera clips/, reels_base_sem_textos.mp4 e reels_preview.mp4. Retorna um resumo."""
    pasta_originais, pasta_saida, pasta_temp = Path(pasta_originais), Path(pasta_saida), Path(pasta_temp)
    metas = {}
    for s in plano["segmentos"]:
        origem = pasta_originais / s["arquivo_origem"]
        if s["arquivo_origem"] not in metas:
            if not origem.exists():
                raise ErroEstudio(f"O plano usa '{s['arquivo_origem']}', mas esse arquivo não está no projeto.")
            metas[s["arquivo_origem"]] = analise.ler_metadados(origem)
    erros = validar(plano, {nome: m["duracao_s"] for nome, m in metas.items()})
    if erros:
        raise ErroEstudio("O plano de edição tem problemas e não foi renderizado:\n- " + "\n- ".join(erros))

    _, total = linha_do_tempo(plano)
    garantir_espaco(pasta_saida, int(total * BYTES_POR_SEGUNDO * 4))
    if pasta_saida.exists():
        shutil.rmtree(pasta_saida)
    (pasta_saida / "clips").mkdir(parents=True)
    pasta_temp.mkdir(parents=True, exist_ok=True)

    avisos, arquivos = [], []
    segmentos = sorted(plano["segmentos"], key=lambda s: s["ordem"])
    for n, s in enumerate(segmentos, 1):
        ao_progredir(f"Cortando trecho {n} de {len(segmentos)} ({s['arquivo_origem']})")
        destino = pasta_saida / "clips" / f"{s['ordem']:02d}_{s['papel']}.mp4"
        aviso = renderizar_segmento(s, metas[s["arquivo_origem"]], pasta_originais / s["arquivo_origem"], destino, plano["formato_saida"])
        if aviso:
            avisos.append(f"{s['id']}: {aviso}")
        arquivos.append(destino)

    ao_progredir("Unindo os trechos")
    base = pasta_saida / "reels_base_sem_textos.mp4"
    unir_segmentos(arquivos, plano, base, pasta_temp)
    ao_progredir("Desenhando textos na tela")
    preview = pasta_saida / "reels_preview.mp4"
    avisos += desenhar_textos(base, plano, preview, pasta_temp, estilo)

    verificacao = [verificar_saida(preview, plano), verificar_saida(base, plano)]
    resumo = {"avisos_renderizacao": avisos, "verificacao": verificacao}
    (pasta_temp / "resumo_renderizacao.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumo
