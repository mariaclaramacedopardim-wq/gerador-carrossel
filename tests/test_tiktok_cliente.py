import pytest
import requests

from publicador_tiktok import tiktok
from publicador_tiktok.tiktok import MB, ClienteTikTok, ErroTikTok, plano_de_chunks


def test_plano_de_chunks_arquivo_pequeno_vai_inteiro():
    assert plano_de_chunks(3 * MB) == (3 * MB, 1, [(0, 3 * MB - 1)])
    assert plano_de_chunks(7 * MB)[1] == 1


def test_plano_de_chunks_ultimo_absorve_a_sobra():
    tamanho = 50_000_123
    chunk, quantidade, faixas = plano_de_chunks(tamanho)
    assert (chunk, quantidade) == (10 * MB, 4)  # 50.000.123 // 10 MiB
    assert faixas[0] == (0, chunk - 1)
    assert faixas[-1][1] == tamanho - 1
    assert all(a[1] + 1 == b[0] for a, b in zip(faixas, faixas[1:]))


def test_plano_de_chunks_arquivo_gigante_respeita_1000_pedacos():
    _, quantidade, _ = plano_de_chunks(20 * 1024 * MB)
    assert 1 <= quantidade <= 1000


class Resposta:
    def __init__(self, status=200, corpo=None):
        self.status_code, self._corpo = status, corpo if corpo is not None else {}

    def json(self):
        return self._corpo


class Sessao:
    def __init__(self, respostas):
        self.respostas, self.chamadas = list(respostas), []

    def request(self, metodo, url, **kwargs):
        self.chamadas.append((metodo, url, kwargs))
        item = self.respostas.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _cliente(respostas):
    sessao = Sessao(respostas)
    return ClienteTikTok("TOKEN", sessao, dormir=lambda s: None), sessao


def test_publicar_video_envia_chunks_com_content_range(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * (25 * MB))
    cliente, sessao = _cliente([
        Resposta(200, {"data": {"publish_id": "p1", "upload_url": "https://up"}, "error": {"code": "ok"}}),
        Resposta(206), Resposta(201),
    ])
    ids = []
    assert cliente.publicar_video(video, {"title": "t"}, ids.append) == "p1"
    assert ids == ["p1"]
    inicio = sessao.chamadas[0][2]["json"]["source_info"]
    assert inicio == {"source": "FILE_UPLOAD", "video_size": 25 * MB, "chunk_size": 10 * MB, "total_chunk_count": 2}
    assert sessao.chamadas[1][2]["headers"]["Content-Range"] == f"bytes 0-{10 * MB - 1}/{25 * MB}"
    assert sessao.chamadas[2][2]["headers"]["Content-Range"] == f"bytes {10 * MB}-{25 * MB - 1}/{25 * MB}"
    assert sessao.chamadas[0][2]["headers"]["Authorization"] == "Bearer TOKEN"


def test_erro_do_tiktok_e_classificado():
    cliente, _ = _cliente([Resposta(403, {"error": {"code": "unaudited_client_can_only_post_to_private_accounts", "message": "m"}})])
    with pytest.raises(ErroTikTok) as erro:
        cliente.creator_info()
    assert erro.value.fatal and not erro.value.transitorio


def test_repete_em_5xx_e_em_erro_de_rede():
    cliente, sessao = _cliente([
        requests.ConnectionError(), Resposta(503), Resposta(200, {"data": {"status": "PUBLISH_COMPLETE"}, "error": {"code": "ok"}}),
    ])
    assert cliente.status("p")["status"] == "PUBLISH_COMPLETE"
    assert len(sessao.chamadas) == 3


def test_desiste_depois_das_tentativas():
    cliente, _ = _cliente([Resposta(503)] * 4)
    with pytest.raises(ErroTikTok) as erro:
        cliente.creator_info()
    assert erro.value.transitorio


def test_renovar_token_nao_vaza_credenciais_no_erro():
    class S:
        @staticmethod
        def post(url, data, timeout):
            return Resposta(400, {"error": "invalid_grant", "error_description": "expirou"})

    with pytest.raises(ErroTikTok) as erro:
        tiktok.renovar_token("chave", "SEGREDO", "REFRESH", S)
    assert erro.value.fatal
    assert "SEGREDO" not in str(erro.value) and "REFRESH" not in str(erro.value)
