import hashlib
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from publicador_tiktok import publicar
from publicador_tiktok.estado import Estado
from publicador_tiktok.tiktok import ErroTikTok

VALIDAR_REAL = publicar.validar_video
FUSO = ZoneInfo("America/Sao_Paulo")
CONTEUDO = b"video-falso"
MD5 = hashlib.md5(CONTEUDO).hexdigest()
AGORA = datetime(2026, 10, 24, 20, 0, tzinfo=FUSO)


class DriveFalso:
    def __init__(self, videos, legendas=None):
        self.videos, self.legendas, self.movidos = videos, legendas or {}, []

    def fila(self):
        return self.videos

    def baixar(self, id_arquivo, destino):
        destino.write_bytes(CONTEUDO)

    def ler_texto(self, id_arquivo):
        return self.legendas[id_arquivo]

    def mover_para_publicados(self, ids):
        self.movidos.extend(ids)


class TikTokFalso:
    def __init__(self, status="PUBLISH_COMPLETE", motivo="", erro=None):
        self.status_final, self.motivo, self.erro = status, motivo, erro
        self.posts, self.consultas = [], 0

    def creator_info(self):
        return {"privacy_level_options": ["PUBLIC_TO_EVERYONE", "SELF_ONLY"], "max_video_post_duration_sec": 600}

    def publicar_video(self, caminho, post_info, ao_iniciar=None):
        if self.erro:
            raise self.erro
        self.posts.append(post_info)
        ao_iniciar("pub-1")
        return "pub-1"

    def status(self, publish_id):
        self.consultas += 1
        return {"status": self.status_final, "fail_reason": self.motivo}


@pytest.fixture(autouse=True)
def sem_ffprobe(monkeypatch):
    """O conteúdo falso destes testes não é um vídeo de verdade; a validação tem teste próprio abaixo."""
    monkeypatch.setattr(publicar, "validar_video", lambda caminho, duracao_maxima_s=None: None)


def video(id_, nome="a.mp4", md5=MD5, legenda_id=None):
    return {"id": id_, "name": nome, "md5Checksum": md5, "legenda_id": legenda_id}


def rodar(tmp_path, drive, tiktok, estado=None, simulacao=False, publico=False, agora=AGORA):
    estado = estado or Estado(tmp_path / "e.json")
    estado.dia(agora.date().isoformat())["horarios"] = ["19:00"]
    resultado = publicar.executar(
        estado=estado, drive=drive, tiktok=tiktok, agora=agora, simulacao=simulacao, publico=publico,
        pasta_tmp=tmp_path, dormir=lambda s: None, log=lambda *_: None, rng=random.Random(1),
    )
    return resultado, estado


def test_publica_o_primeiro_da_fila_uma_unica_vez(tmp_path):
    drive, tiktok = DriveFalso([video("1"), video("2", "b.mp4", md5="outro")]), TikTokFalso()
    resultado, estado = rodar(tmp_path, drive, tiktok)
    assert resultado == "publicado"
    assert estado.video("1")["status"] == "publicado" and estado.video("1")["publish_id"] == "pub-1"
    assert drive.movidos == ["1"]
    # mesma hora de novo: o horário já foi usado, nada é publicado
    resultado, _ = rodar(tmp_path, drive, tiktok, estado)
    assert resultado == "sem_horario" and len(tiktok.posts) == 1


def test_nao_republica_o_mesmo_conteudo_com_outro_arquivo(tmp_path):
    estado = Estado(tmp_path / "e.json")
    estado.registrar("velho", MD5, status="publicado")
    resultado, _ = rodar(tmp_path, DriveFalso([video("novo")]), TikTokFalso(), estado)
    assert resultado == "fila_vazia"


def test_sem_auditoria_tudo_sai_privado_mesmo_pedindo_publico(tmp_path):
    legendas = {"l1": '{"legenda": "Oi", "hashtags": ["x"], "privacidade": "PUBLIC_TO_EVERYONE"}'}
    tiktok = TikTokFalso()
    rodar(tmp_path, DriveFalso([video("1", legenda_id="l1")], legendas), tiktok, publico=False)
    assert tiktok.posts[0]["privacy_level"] == "SELF_ONLY"
    assert tiktok.posts[0]["title"] == "Oi\n#x"


def test_com_auditoria_respeita_a_privacidade_do_video(tmp_path):
    legendas = {"l1": '{"privacidade": "PUBLIC_TO_EVERYONE"}'}
    tiktok = TikTokFalso()
    rodar(tmp_path, DriveFalso([video("1", legenda_id="l1")], legendas), tiktok, publico=True)
    assert tiktok.posts[0]["privacy_level"] == "PUBLIC_TO_EVERYONE"


def test_simulacao_nao_envia_nem_altera_a_fila(tmp_path):
    tiktok = TikTokFalso()
    resultado, estado = rodar(tmp_path, DriveFalso([video("1")]), tiktok, simulacao=True)
    assert resultado == "simulado" and not tiktok.posts and estado.video("1") is None


def test_legenda_invalida_pula_para_o_proximo_video(tmp_path):
    legendas = {"l1": "{quebrado"}
    drive = DriveFalso([video("1", legenda_id="l1"), video("2", "b.mp4", md5=None)], legendas)
    resultado, estado = rodar(tmp_path, drive, TikTokFalso())
    assert resultado == "publicado" and estado.video("2")["status"] == "publicado"


def test_falha_transitoria_volta_para_a_fila_e_mantem_o_horario(tmp_path):
    tiktok = TikTokFalso(erro=ErroTikTok("rede"))
    resultado, estado = rodar(tmp_path, DriveFalso([video("1")]), tiktok)
    assert resultado == "tentar_depois"
    assert estado.video("1")["status"] == "pendente" and estado.video("1")["tentativas"] == 1
    assert estado.dia(AGORA.date().isoformat())["usados"] == []


def test_apos_tres_falhas_transitorias_o_video_falha_de_vez(tmp_path):
    estado = Estado(tmp_path / "e.json")
    for _ in range(3):
        resultado, estado = rodar(tmp_path, DriveFalso([video("1")]), TikTokFalso(erro=ErroTikTok("rede")), estado)
    assert resultado == "falhou" and estado.video("1")["status"] == "falhou"


def test_erro_fatal_interrompe_sem_queimar_o_video(tmp_path):
    erro = ErroTikTok("unaudited_client_can_only_post_to_private_accounts", http=403)
    estado = Estado(tmp_path / "e.json")
    with pytest.raises(ErroTikTok):
        rodar(tmp_path, DriveFalso([video("1")]), TikTokFalso(erro=erro), estado)
    assert estado.video("1")["status"] == "pendente" and estado.video("1")["tentativas"] == 0


def test_recusa_definitiva_do_tiktok_consome_o_horario(tmp_path):
    tiktok = TikTokFalso(status="FAILED", motivo="file_format_check_failed")
    resultado, estado = rodar(tmp_path, DriveFalso([video("1")]), tiktok)
    assert resultado == "falhou" and estado.video("1")["status"] == "falhou"
    assert estado.dia(AGORA.date().isoformat())["usados"] == ["19:00"]


def test_pendencia_ainda_processando_bloqueia_novo_envio(tmp_path):
    estado = Estado(tmp_path / "e.json")
    estado.registrar("1", MD5, status="enviando", publish_id="pub-0")
    tiktok = TikTokFalso(status="PROCESSING_UPLOAD")
    resultado, _ = rodar(tmp_path, DriveFalso([video("2", md5="outro")]), tiktok, estado)
    assert resultado == "aguardando" and not tiktok.posts


def test_pendencia_concluida_e_registrada(tmp_path):
    estado = Estado(tmp_path / "e.json")
    estado.registrar("1", MD5, status="enviando", publish_id="pub-0")
    resultado, estado = rodar(tmp_path, DriveFalso([]), TikTokFalso(), estado)
    assert estado.video("1")["status"] == "publicado" and resultado == "fila_vazia"


def test_envio_interrompido_antes_do_tiktok_aceitar_volta_para_a_fila(tmp_path):
    estado = Estado(tmp_path / "e.json")
    estado.registrar("1", MD5, status="enviando", publish_id=None)
    publicar.resolver_pendencias(estado, TikTokFalso(), lambda *_: None)
    assert estado.video("1")["status"] == "pendente"


def test_estado_salvo_nao_contem_legenda_nem_nome(tmp_path):
    legendas = {"l1": '{"legenda": "TEXTO SECRETO", "hashtags": ["tag"]}'}
    rodar(tmp_path, DriveFalso([video("1", "NOME_PRIVADO.mp4", legenda_id="l1")], legendas), TikTokFalso())
    estado = Estado(tmp_path / "e.json")
    estado.salvar()
    texto = (tmp_path / "e.json").read_text()
    assert "TEXTO SECRETO" not in texto and "NOME_PRIVADO" not in texto


def test_validar_video_recusa_arquivo_que_nao_e_video(tmp_path):
    import shutil

    if not shutil.which("ffprobe"):
        pytest.skip("FFmpeg não instalado")
    falso = tmp_path / "x.mp4"
    falso.write_bytes(b"nao sou video")
    with pytest.raises(publicar.ErroVideo):
        VALIDAR_REAL(falso)


def test_validar_video_recusa_duracao_acima_do_limite(videos_teste):
    arquivo = next(iter(videos_teste.values()))
    with pytest.raises(publicar.ErroVideo):
        VALIDAR_REAL(arquivo, duracao_maxima_s=0.1)
    VALIDAR_REAL(arquivo, duracao_maxima_s=600)


def test_download_corrompido_nao_e_publicado(tmp_path):
    tiktok = TikTokFalso()
    resultado, estado = rodar(tmp_path, DriveFalso([video("1", md5="0" * 32)]), tiktok)
    assert resultado == "tentar_depois" and not tiktok.posts and estado.video("1")["status"] == "pendente"


# --- agendamento à mão (publicar_em) e "publicar agora" ---------------------------------------
def rodar_sem_horario(tmp_path, drive, tiktok, estado=None, forcar=False, agora=AGORA):
    """Como `rodar`, mas sem nenhum horário sorteado para o dia."""
    estado = estado or Estado(tmp_path / "e.json")
    estado.dia(agora.date().isoformat())["horarios"] = ["23:59"]  # ainda não chegou
    resultado = publicar.executar(
        estado=estado, drive=drive, tiktok=tiktok, agora=agora, simulacao=False, publico=False,
        pasta_tmp=tmp_path, dormir=lambda s: None, log=lambda *_: None, rng=random.Random(1), forcar=forcar,
    )
    return resultado, estado


def legenda_em(quando):
    return '{"publicar_em": "%s"}' % quando


def test_video_agendado_sai_na_hora_marcada_sem_gastar_horario_sorteado(tmp_path):
    drive = DriveFalso([video("1", legenda_id="l1", md5=None)], {"l1": legenda_em("2026-10-24 19:30")})
    tiktok = TikTokFalso()
    resultado, estado = rodar_sem_horario(tmp_path, drive, tiktok)
    assert resultado == "publicado" and estado.video("1")["status"] == "publicado"
    dia = estado.dia(AGORA.date().isoformat())
    assert dia["usados"] == [] and dia["publicados"] == 1


def test_video_agendado_para_o_futuro_espera_e_nao_e_pego_pelo_horario_sorteado(tmp_path):
    drive = DriveFalso([video("1", legenda_id="l1", md5=None)], {"l1": legenda_em("2026-10-30 19:30")})
    tiktok = TikTokFalso()
    resultado, _ = rodar(tmp_path, drive, tiktok)  # há horário sorteado, mas o único vídeo é do futuro
    assert resultado == "fila_vazia" and not tiktok.posts
    resultado, _ = rodar_sem_horario(tmp_path, drive, tiktok)
    assert resultado == "sem_horario" and not tiktok.posts


def test_horario_sorteado_pula_o_agendado_e_usa_o_proximo_sem_data(tmp_path):
    drive = DriveFalso(
        [video("1", "a.mp4", legenda_id="l1", md5=None), video("2", "b.mp4", md5=None)], {"l1": legenda_em("2026-10-30 19:30")}
    )
    resultado, estado = rodar(tmp_path, drive, TikTokFalso())
    assert resultado == "publicado" and estado.video("2")["status"] == "publicado" and estado.video("1") is None


def test_agendado_vencido_tem_prioridade_sobre_o_horario_sorteado(tmp_path):
    drive = DriveFalso(
        [video("1", "a.mp4", md5=None), video("2", "b.mp4", legenda_id="l2", md5=None)], {"l2": legenda_em("2026-10-24 10:00")}
    )
    resultado, estado = rodar(tmp_path, drive, TikTokFalso())
    assert resultado == "publicado" and estado.video("2")["status"] == "publicado"
    assert estado.dia(AGORA.date().isoformat())["usados"] == []  # o horário sorteado continua livre


def test_agendado_respeita_o_limite_diario(tmp_path):
    estado = Estado(tmp_path / "e.json")
    estado.dia(AGORA.date().isoformat())["publicados"] = 3
    drive = DriveFalso([video("1", legenda_id="l1", md5=None)], {"l1": legenda_em("2026-10-24 10:00")})
    resultado, _ = rodar_sem_horario(tmp_path, drive, TikTokFalso(), estado)
    assert resultado == "limite"


def test_publicar_agora_ignora_horario_e_data(tmp_path):
    drive = DriveFalso([video("1", legenda_id="l1", md5=None)], {"l1": legenda_em("2026-12-31 10:00")})
    tiktok = TikTokFalso()
    resultado, estado = rodar_sem_horario(tmp_path, drive, tiktok, forcar=True)
    assert resultado == "publicado" and len(tiktok.posts) == 1 and estado.video("1")["status"] == "publicado"


def test_agendado_continua_privado_sem_auditoria(tmp_path):
    legendas = {"l1": '{"publicar_em": "2026-10-24 10:00", "privacidade": "PUBLIC_TO_EVERYONE"}'}
    tiktok = TikTokFalso()
    rodar_sem_horario(tmp_path, DriveFalso([video("1", legenda_id="l1", md5=None)], legendas), tiktok)
    assert tiktok.posts[0]["privacy_level"] == "SELF_ONLY"
