"""Uma execução do publicador: decide se é hora, escolhe o próximo vídeo aprovado e publica."""

import hashlib
import json
import shutil
import subprocess
import time

from . import agenda, config, estado as est, metadados
from .tiktok import ErroTikTok

REPETIVEIS = {"internal"}  # motivos de FAILED que valem nova tentativa


class ErroVideo(Exception):
    """Problema no arquivo que repetir não resolve (duração, formato)."""


def _md5(caminho):
    resumo = hashlib.md5()
    with open(caminho, "rb") as arquivo:
        for pedaco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(pedaco)
    return resumo.hexdigest()


def validar_video(caminho, duracao_maxima_s=None):
    """Confere duração e codec com o ffprobe (se instalado)."""
    if not shutil.which("ffprobe"):
        return
    saida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,codec_type",
         "-of", "json", str(caminho)],
        capture_output=True, text=True,
    )
    if saida.returncode != 0:
        raise ErroVideo("O arquivo não é um vídeo válido.")
    dados = json.loads(saida.stdout or "{}")
    duracao = float(dados.get("format", {}).get("duration") or 0)
    if duracao_maxima_s and duracao > duracao_maxima_s:
        raise ErroVideo(f"O vídeo tem {duracao:.0f}s e a conta aceita até {duracao_maxima_s}s.")
    codecs = {s.get("codec_name") for s in dados.get("streams", []) if s.get("codec_type") == "video"}
    if codecs and not codecs & {"h264", "hevc", "vp8", "vp9", "av1"}:
        raise ErroVideo(f"Codec de vídeo não aceito: {', '.join(sorted(map(str, codecs)))}.")


def escolher_privacidade(pedida, permitidas, publico_liberado):
    """Sem auditoria (TIKTOK_PUBLICO != 1) tudo sai privado, mesmo que o vídeo peça público."""
    if not publico_liberado:
        return config.PRIVACIDADE_SEGURA
    if pedida in permitidas:
        return pedida
    print(f"::warning::Privacidade {pedida} indisponível para a conta; usando {config.PRIVACIDADE_SEGURA}.")
    return config.PRIVACIDADE_SEGURA


def montar_post_info(meta, info_criador, privacidade):
    return {
        "title": meta["titulo"],
        "privacy_level": privacidade,
        "disable_comment": info_criador.get("comment_disabled", False) or not meta["comentarios"],
        "disable_duet": info_criador.get("duet_disabled", False) or not meta["duet"],
        "disable_stitch": info_criador.get("stitch_disabled", False) or not meta["stitch"],
        "video_cover_timestamp_ms": meta["capa_ms"],
        "brand_content_toggle": meta["conteudo_de_marca"] and privacidade != config.PRIVACIDADE_SEGURA,
        "brand_organic_toggle": meta["promocao_propria"],
        "is_aigc": meta["ia"],
    }


def aguardar_resultado(tiktok, publish_id, dormir=time.sleep):
    """Consulta o status até terminar. Devolve (status, motivo); o status fica PROCESSING_* se estourar o tempo."""
    limite = time.monotonic() + config.TEMPO_MAXIMO_STATUS_S
    while True:
        dados = tiktok.status(publish_id)
        status = dados.get("status", "")
        if status in ("PUBLISH_COMPLETE", "FAILED", "SEND_TO_USER_INBOX") or time.monotonic() >= limite:
            return status, dados.get("fail_reason", "")
        dormir(config.ESPERA_STATUS_S)


def _concluir(estado, id_drive, status, motivo):
    """Aplica o resultado final do TikTok ao estado. Devolve True se o vídeo saiu da fila (publicado ou falha definitiva)."""
    registro = estado.video(id_drive)
    if status == "PUBLISH_COMPLETE":
        estado.registrar(id_drive, registro["md5"], status=est.PUBLICADO, erro=None)
        return True
    if status == "SEND_TO_USER_INBOX":  # não esperado no Direct Post; exige olhar o app do TikTok
        estado.registrar(id_drive, registro["md5"], status=est.FALHOU, erro="send_to_inbox")
        return True
    if status == "FAILED":
        tentativas = registro["tentativas"] + 1
        if motivo in REPETIVEIS and tentativas < config.MAX_TENTATIVAS:
            estado.registrar(id_drive, registro["md5"], status=est.PENDENTE, publish_id=None, tentativas=tentativas, erro=motivo)
            return False
        estado.registrar(id_drive, registro["md5"], status=est.FALHOU, tentativas=tentativas, erro=motivo or "FAILED")
        return True
    return False  # ainda processando


def resolver_pendencias(estado, tiktok, log):
    """Confere vídeos que ficaram "enviando". Devolve True se algum ainda está sendo processado pelo TikTok."""
    ainda_processando = False
    for id_drive, registro in list(estado.em_envio().items()):
        if not registro.get("publish_id"):
            # A execução caiu antes do TikTok aceitar o envio: volta para a fila.
            estado.registrar(id_drive, registro["md5"], status=est.PENDENTE, tentativas=registro["tentativas"] + 1)
            continue
        dados = tiktok.status(registro["publish_id"])
        status, motivo = dados.get("status", ""), dados.get("fail_reason", "")
        if not _concluir(estado, id_drive, status, motivo) and status != "FAILED":
            ainda_processando = True
        log(f"Pendência resolvida: status {status or 'desconhecido'}.")
    return ainda_processando


def executar(*, estado, drive, tiktok, agora, simulacao, publico, pasta_tmp, dormir=time.sleep, log=print, rng=None):
    """Roda uma vez. Devolve um código curto (usado nos logs e nos testes)."""
    estado.podar_dias(agora.date())
    dia = agenda.garantir_plano_do_dia(estado, agora, rng=rng)
    horario = agenda.horario_devido(dia, agora)
    log(f"Horários de hoje: {', '.join(dia['horarios'])} | usados: {len(dia['usados'])} | perdidos: {len(dia['perdidos'])}")

    if tiktok and not simulacao and resolver_pendencias(estado, tiktok, log):
        return "aguardando"
    if horario is None:
        return "sem_horario"
    if dia["publicados"] >= config.LIMITE_DIARIO:
        return "limite"

    fila = drive.fila()
    candidatos = [v for v in fila if estado.pode_publicar(v["id"], v.get("md5Checksum"))]
    if not candidatos:
        log("Fila vazia: não há vídeos aprovados novos na pasta.")
        return "fila_vazia"

    for video in candidatos:
        try:
            meta = metadados.ler(drive.ler_texto(video["legenda_id"]) if video.get("legenda_id") else None)
        except metadados.ErroMetadados as erro:
            log(f"::warning::Vídeo pulado por problema na legenda: {erro}")
            continue
        if simulacao:
            log(f"[simulação] Publicaria o vídeo {video['id']} no horário {horario}; privacidade pedida: {meta['privacidade']}.")
            return "simulado"
        return _publicar_video(estado, drive, tiktok, video, meta, dia, horario, publico, pasta_tmp, dormir, log)
    return "fila_vazia"


def _publicar_video(estado, drive, tiktok, video, meta, dia, horario, publico, pasta_tmp, dormir, log):
    id_drive, md5 = video["id"], video.get("md5Checksum") or ""
    tentativas = (estado.video(id_drive) or {}).get("tentativas", 0)
    estado.registrar(id_drive, md5, status=est.ENVIANDO, publish_id=None, tentativas=tentativas, erro=None)
    estado.salvar()
    caminho = pasta_tmp / f"{id_drive}.mp4"
    try:
        drive.baixar(id_drive, caminho)
        if md5 and _md5(caminho) != md5:
            raise ErroTikTok("rede", "download corrompido")
        info = tiktok.creator_info()
        validar_video(caminho, info.get("max_video_post_duration_sec"))
        privacidade = escolher_privacidade(meta["privacidade"], info.get("privacy_level_options", []), publico)

        def guardar_id(publish_id):
            estado.registrar(id_drive, md5, publish_id=publish_id)
            estado.salvar()

        publish_id = tiktok.publicar_video(caminho, montar_post_info(meta, info, privacidade), guardar_id)
        log(f"Vídeo enviado ao TikTok (privacidade {privacidade}). Aguardando o processamento...")
        status, motivo = aguardar_resultado(tiktok, publish_id, dormir)
    except ErroVideo as erro:
        estado.registrar(id_drive, md5, status=est.FALHOU, tentativas=tentativas + 1, erro="video_invalido")
        dia["usados"].append(horario)
        log(f"::error::Vídeo reprovado na validação: {erro}")
        return "falhou"
    except ErroTikTok as erro:
        if erro.fatal:
            estado.registrar(id_drive, md5, status=est.PENDENTE, publish_id=None, erro=erro.codigo)
            raise
        if erro.transitorio:
            tentativas += 1
            definitivo = tentativas >= config.MAX_TENTATIVAS
            estado.registrar(id_drive, md5, status=est.FALHOU if definitivo else est.PENDENTE,
                             publish_id=None, tentativas=tentativas, erro=erro.codigo)
            log(f"::warning::Falha transitória ({erro.codigo}); tentativa {tentativas}/{config.MAX_TENTATIVAS}.")
            return "falhou" if definitivo else "tentar_depois"
        estado.registrar(id_drive, md5, status=est.FALHOU, tentativas=tentativas + 1, erro=erro.codigo)
        dia["usados"].append(horario)
        log(f"::error::O TikTok recusou o vídeo ({erro.codigo}).")
        return "falhou"
    finally:
        caminho.unlink(missing_ok=True)

    saiu_da_fila = _concluir(estado, id_drive, status, motivo)
    if status == "PUBLISH_COMPLETE":
        dia["usados"].append(horario)
        dia["publicados"] += 1
        drive.mover_para_publicados([i for i in (id_drive, video.get("legenda_id")) if i])
        log("Publicado.")
        return "publicado"
    if saiu_da_fila:
        dia["usados"].append(horario)
        log(f"::error::O TikTok não publicou o vídeo ({motivo or status}).")
        return "falhou"
    log(f"Status {status or 'desconhecido'}: o TikTok ainda processa; confiro na próxima execução.")
    return "aguardando"
