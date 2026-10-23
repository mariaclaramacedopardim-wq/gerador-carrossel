import base64

from nacl import encoding, public

from publicador_tiktok import segredos


class Resp:
    def __init__(self, status, corpo=None):
        self.status_code, self._c = status, corpo

    def json(self):
        return self._c


def test_secret_e_cifrado_com_a_chave_publica_do_repositorio():
    par = public.PrivateKey.generate()
    chave = base64.b64encode(bytes(par.public_key)).decode()
    enviado = {}

    class S:
        @staticmethod
        def get(url, headers, timeout):
            assert url.endswith("/actions/secrets/public-key")
            return Resp(200, {"key": chave, "key_id": "k1"})

        @staticmethod
        def put(url, headers, json, timeout):
            enviado.update(json, url=url)
            return Resp(204)

    segredos.atualizar_secret("dono/repo", "TIKTOK_REFRESH_TOKEN", "novo-valor", "pat", S)
    assert enviado["key_id"] == "k1" and enviado["url"].endswith("/TIKTOK_REFRESH_TOKEN")
    assert "novo-valor" not in enviado["encrypted_value"]
    aberto = public.SealedBox(par).decrypt(base64.b64decode(enviado["encrypted_value"]))
    assert aberto == b"novo-valor"
