import pytest

from publicador_tiktok import metadados


def test_legenda_e_hashtags_do_video():
    meta = metadados.ler('{"legenda": "Creatina funciona", "hashtags": ["fitness", "#creatina"]}', {})
    assert meta["titulo"] == "Creatina funciona\n#fitness #creatina"
    assert meta["comentarios"] is True and meta["ia"] is False


def test_sem_arquivo_usa_os_padroes():
    meta = metadados.ler(None, {"legenda_padrao": "Oi", "hashtags_padrao": ["reels"]})
    assert meta["titulo"] == "Oi\n#reels"


def test_hashtags_como_texto():
    assert metadados.ler('{"hashtags": "a b"}', {})["titulo"] == "#a #b"


def test_json_invalido_e_legenda_longa_dao_erro():
    with pytest.raises(metadados.ErroMetadados):
        metadados.ler("{quebrado", {})
    with pytest.raises(metadados.ErroMetadados):
        metadados.ler('{"legenda": "' + "a" * 2300 + '"}', {})


def test_emoji_conta_duas_unidades_utf16():
    with pytest.raises(metadados.ErroMetadados):
        metadados.ler('{"legenda": "' + "😀" * 1101 + '"}', {})
    metadados.ler('{"legenda": "' + "😀" * 1100 + '"}', {})


def test_publicar_em_aceita_formatos_e_usa_o_fuso_de_brasilia():
    from datetime import timedelta

    for texto in ("2026-10-30 19:30", "2026-10-30T19:30", "30/10/2026 19:30"):
        quando = metadados.ler('{"publicar_em": "%s"}' % texto, {})["publicar_em"]
        assert (quando.year, quando.month, quando.day, quando.hour, quando.minute) == (2026, 10, 30, 19, 30)
        assert quando.utcoffset() == timedelta(hours=-3)
    assert metadados.ler(None, {})["publicar_em"] is None


def test_publicar_em_invalido_da_erro():
    with pytest.raises(metadados.ErroMetadados):
        metadados.ler('{"publicar_em": "amanhã de noite"}', {})
