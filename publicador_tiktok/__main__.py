"""Comandos: python -m publicador_tiktok publicar | status | autorizar"""

import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, tiktok
from .drive import ErroDrive, PastaDrive
from .estado import Estado
from .publicar import executar
from .segredos import ErroSegredo, atualizar_secret


def _exigir(nome):
    valor = os.environ.get(nome)
    if not valor:
        sys.exit(f"Falta a variável de ambiente {nome} (cadastre como Secret no GitHub).")
    return valor


def _drive():
    return PastaDrive(_exigir("GDRIVE_SA_KEY"), _exigir("GDRIVE_FOLDER_ID"), os.environ.get("GDRIVE_PUBLICADOS_FOLDER_ID") or None)


def _cliente_tiktok():
    chave, segredo = _exigir("TIKTOK_CLIENT_KEY"), _exigir("TIKTOK_CLIENT_SECRET")
    antigo = _exigir("TIKTOK_REFRESH_TOKEN")
    token = tiktok.renovar_token(chave, segredo, antigo)
    novo = token.get("refresh_token")
    if novo and novo != antigo:
        _guardar_refresh_token(novo)
    return tiktok.ClienteTikTok(token["access_token"])


def _guardar_refresh_token(novo):
    """O TikTok pode trocar o refresh_token a cada renovação; o novo precisa substituir o secret."""
    pat, repositorio = os.environ.get("GH_SECRETS_PAT"), os.environ.get("GITHUB_REPOSITORY")
    if pat and repositorio:
        try:
            atualizar_secret(repositorio, "TIKTOK_REFRESH_TOKEN", novo, pat)
            print("Refresh token renovado e gravado no secret TIKTOK_REFRESH_TOKEN.")
            return
        except ErroSegredo as erro:
            print(f"::error::Não consegui gravar o novo refresh token: {erro}")
    else:
        print("::error::O TikTok trocou o refresh token e não há GH_SECRETS_PAT para gravar o novo. "
              "Refaça a autorização (python -m publicador_tiktok autorizar) antes que o antigo deixe de valer.")


def cmd_publicar(args):
    simulacao = os.environ.get("TIKTOK_MODO", "simulacao") != "real"
    publico = os.environ.get("TIKTOK_PUBLICO", "0") == "1"
    forcar = os.environ.get("TIKTOK_AGORA", "0") == "1"
    estado = Estado(args.estado)
    cliente = None if simulacao else _cliente_tiktok()
    agora = datetime.now(ZoneInfo(config.FUSO))
    print(f"Modo: {'SIMULAÇÃO (nada é enviado)' if simulacao else 'REAL'} | publicação pública: {'sim' if publico else 'não (tudo privado)'}{' | PUBLICAR AGORA' if forcar else ''}")
    try:
        with tempfile.TemporaryDirectory() as pasta:
            resultado = executar(
                estado=estado, drive=_drive(), tiktok=cliente, agora=agora,
                simulacao=simulacao, publico=publico, pasta_tmp=Path(pasta), forcar=forcar,
            )
    except (tiktok.ErroTikTok, ErroDrive) as erro:
        estado.salvar()
        sys.exit(f"::error::{erro}")
    estado.salvar()
    print(f"Resultado: {resultado}")


def cmd_status(args):
    estado = Estado(args.estado)
    print("Fila por status:", estado.resumo() or "vazia")
    for data_iso in sorted(estado.dados["dias"])[-3:]:
        print(data_iso, estado.dados["dias"][data_iso])


def cmd_autorizar(_args):
    """Autorização inicial (uma vez). Rode no seu computador; o token nunca é impresso."""
    from urllib.parse import parse_qs, urlencode, urlparse

    import requests

    chave, segredo, redirecionamento = _exigir("TIKTOK_CLIENT_KEY"), _exigir("TIKTOK_CLIENT_SECRET"), _exigir("TIKTOK_REDIRECT_URI")
    link = "https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
        "client_key": chave, "scope": "user.info.basic,video.publish", "response_type": "code",
        "redirect_uri": redirecionamento, "state": "publicador",
    })
    print("1) Abra este link, entre na conta que vai publicar e autorize:\n\n" + link + "\n")
    retorno = input("2) Cole aqui a URL completa para onde o TikTok te redirecionou: ").strip()
    codigo = parse_qs(urlparse(retorno).query).get("code", [""])[0]
    if not codigo:
        sys.exit("Não encontrei o parâmetro code nessa URL.")
    resposta = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
        "client_key": chave, "client_secret": segredo, "code": codigo,
        "grant_type": "authorization_code", "redirect_uri": redirecionamento,
    }, timeout=60).json()
    if "refresh_token" not in resposta:
        sys.exit(f"O TikTok recusou a autorização: {resposta.get('error', 'erro')} - {resposta.get('error_description', '')}")
    pat, repositorio = os.environ.get("GH_SECRETS_PAT"), os.environ.get("GITHUB_REPOSITORY")
    if pat and repositorio:
        atualizar_secret(repositorio, "TIKTOK_REFRESH_TOKEN", resposta["refresh_token"], pat)
        print("Pronto: o secret TIKTOK_REFRESH_TOKEN foi gravado.")
        return
    destino = Path(".tiktok_refresh_token")
    destino.write_text(resposta["refresh_token"], encoding="utf-8")
    destino.chmod(0o600)
    print(f"Gravei o token em {destino} (fora do git). Cole o conteúdo no secret TIKTOK_REFRESH_TOKEN e apague o arquivo.")


def main():
    parser = argparse.ArgumentParser(prog="publicador_tiktok")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome, funcao in (("publicar", cmd_publicar), ("status", cmd_status)):
        p = sub.add_parser(nome)
        p.add_argument("--estado", default="_estado/estado.json")
        p.set_defaults(func=funcao)
    sub.add_parser("autorizar").set_defaults(func=cmd_autorizar)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
