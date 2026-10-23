"""Atualiza um GitHub Secret (usado quando o TikTok devolve um refresh_token novo).

Exige um token fino do GitHub (`GH_SECRETS_PAT`) limitado a este repositório, com a permissão
"Secrets: Read and write". O GITHUB_TOKEN padrão do workflow não pode escrever em Secrets.
"""

import base64

import requests


class ErroSegredo(Exception):
    pass


def atualizar_secret(repositorio, nome, valor, token_github, sessao=None):
    from nacl import encoding, public  # importado aqui: só é preciso quando o token muda

    sessao = sessao or requests
    cabecalho = {"Authorization": f"Bearer {token_github}", "Accept": "application/vnd.github+json"}
    base = f"https://api.github.com/repos/{repositorio}/actions/secrets"
    chave = sessao.get(f"{base}/public-key", headers=cabecalho, timeout=30)
    if chave.status_code != 200:
        raise ErroSegredo(f"GitHub respondeu {chave.status_code} ao buscar a chave pública.")
    dados = chave.json()
    caixa = public.SealedBox(public.PublicKey(dados["key"].encode(), encoding.Base64Encoder))
    cifrado = base64.b64encode(caixa.encrypt(valor.encode())).decode()
    resposta = sessao.put(
        f"{base}/{nome}", headers=cabecalho, json={"encrypted_value": cifrado, "key_id": dados["key_id"]}, timeout=30
    )
    if resposta.status_code not in (201, 204):
        raise ErroSegredo(f"GitHub respondeu {resposta.status_code} ao gravar o secret {nome}.")
