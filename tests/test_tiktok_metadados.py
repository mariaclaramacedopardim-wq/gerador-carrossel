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
