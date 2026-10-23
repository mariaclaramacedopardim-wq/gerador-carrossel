"""Cliente da TikTok Content Posting API (Direct Post, envio por FILE_UPLOAD)."""

import time

import requests

from . import config

API = "https://open.tiktokapis.com"
MB = 1024 * 1024

# Erros que não adianta repetir: exigem ação de uma pessoa (autorização, auditoria, limites da conta).
CODIGOS_FATAIS = {
    "access_token_invalid",
    "scope_not_authorized",
    "invalid_grant",
    "invalid_client",
    "unaudited_client_can_only_post_to_private_accounts",
    "reached_active_user_cap",
    "spam_risk_too_many_posts",
    "spam_risk_user_banned_from_posting",
    "url_ownership_unverified",
}


class ErroTikTok(Exception):
    def __init__(self, codigo, mensagem="", http=None):
        super().__init__(f"{codigo}: {mensagem}" if mensagem else codigo)
        self.codigo = codigo
        self.mensagem = mensagem
        self.http = http

    @property
    def fatal(self):
        return self.codigo in CODIGOS_FATAIS

    @property
    def transitorio(self):
        return self.codigo in ("rede", "internal", "rate_limit_exceeded", "internal_error") or bool(
            self.http and (self.http >= 500 or self.http == 429)
        )


def plano_de_chunks(tamanho):
    """Regras da API: chunks de 5 a 64 MB (arquivos pequenos vão inteiros) e o último absorve a sobra."""
    if tamanho <= 0:
        raise ErroTikTok("invalid_param", "o vídeo está vazio")
    tamanho_chunk = min(config.TAMANHO_CHUNK, tamanho)
    quantidade = tamanho // tamanho_chunk
    if quantidade > 1000:
        tamanho_chunk = min(-(-tamanho // 1000), 64 * MB)
        quantidade = tamanho // tamanho_chunk
    faixas = []
    for indice in range(quantidade):
        inicio = indice * tamanho_chunk
        fim = tamanho - 1 if indice == quantidade - 1 else inicio + tamanho_chunk - 1
        faixas.append((inicio, fim))
    return tamanho_chunk, quantidade, faixas


def renovar_token(client_key, client_secret, refresh_token, sessao=None):
    """Troca o refresh_token por um access_token (24 h). O refresh_token devolvido pode ser outro."""
    sessao = sessao or requests
    try:
        resposta = sessao.post(
            f"{API}/v2/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=60,
        )
        corpo = resposta.json()
    except (requests.RequestException, ValueError) as erro:
        raise ErroTikTok("rede", type(erro).__name__) from erro
    if resposta.status_code != 200 or "access_token" not in corpo:
        raise ErroTikTok(str(corpo.get("error", "token")), str(corpo.get("error_description", "")), resposta.status_code)
    return corpo


class ClienteTikTok:
    def __init__(self, access_token, sessao=None, dormir=time.sleep):
        self._cabecalho = {"Authorization": f"Bearer {access_token}"}
        self.sessao = sessao or requests.Session()
        self.dormir = dormir

    def _enviar(self, metodo, url, tentativas=4, **kwargs):
        """Faz a chamada repetindo em erro de rede, 429 e 5xx."""
        for numero in range(tentativas):
            ultima = numero == tentativas - 1
            try:
                resposta = self.sessao.request(metodo, url, timeout=300, **kwargs)
            except requests.RequestException as erro:
                if ultima:
                    raise ErroTikTok("rede", type(erro).__name__) from erro
            else:
                if resposta.status_code not in (429,) and resposta.status_code < 500 or ultima:
                    return resposta
            self.dormir(2 ** (numero + 1))

    def _api_json(self, caminho, corpo=None):
        resposta = self._enviar(
            "POST",
            f"{API}{caminho}",
            headers={**self._cabecalho, "Content-Type": "application/json; charset=UTF-8"},
            json=corpo if corpo is not None else {},
        )
        try:
            dados = resposta.json()
        except ValueError as erro:
            raise ErroTikTok("resposta_invalida", http=resposta.status_code) from erro
        erro = dados.get("error") or {}
        codigo = erro.get("code", "ok")
        if resposta.status_code >= 400 or codigo != "ok":
            raise ErroTikTok(codigo if codigo != "ok" else "http_erro", erro.get("message", ""), resposta.status_code)
        return dados.get("data") or {}

    def creator_info(self):
        return self._api_json("/v2/post/publish/creator_info/query/")

    def status(self, publish_id):
        return self._api_json("/v2/post/publish/status/fetch/", {"publish_id": publish_id})

    def publicar_video(self, caminho, post_info, ao_iniciar=None):
        """Inicia o Direct Post e envia o arquivo. Devolve o publish_id (também entregue a `ao_iniciar`)."""
        with open(caminho, "rb") as arquivo:
            arquivo.seek(0, 2)
            tamanho = arquivo.tell()
            tamanho_chunk, quantidade, faixas = plano_de_chunks(tamanho)
            dados = self._api_json(
                "/v2/post/publish/video/init/",
                {
                    "post_info": post_info,
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": tamanho,
                        "chunk_size": tamanho_chunk,
                        "total_chunk_count": quantidade,
                    },
                },
            )
            publish_id, url = dados["publish_id"], dados["upload_url"]
            if ao_iniciar:
                ao_iniciar(publish_id)
            for numero, (inicio, fim) in enumerate(faixas):
                arquivo.seek(inicio)
                pedaco = arquivo.read(fim - inicio + 1)
                resposta = self._enviar(
                    "PUT",
                    url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(pedaco)),
                        "Content-Range": f"bytes {inicio}-{fim}/{tamanho}",
                    },
                    data=pedaco,
                )
                esperado = 201 if numero == len(faixas) - 1 else 206
                if resposta.status_code != esperado:
                    raise ErroTikTok("upload_falhou", f"pedaço {numero + 1}/{len(faixas)}", resposta.status_code)
        return publish_id
