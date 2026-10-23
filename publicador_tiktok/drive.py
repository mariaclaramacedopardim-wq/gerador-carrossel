"""Pasta do Google Drive com os vídeos aprovados (acesso por service account)."""

import json

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

API = "https://www.googleapis.com/drive/v3"
ESCOPO_LEITURA = "https://www.googleapis.com/auth/drive.readonly"
ESCOPO_TOTAL = "https://www.googleapis.com/auth/drive"


class ErroDrive(Exception):
    pass


class PastaDrive:
    """`pasta_id` é a pasta "Aprovados". Se `publicados_id` existir, os vídeos publicados são movidos para lá."""

    def __init__(self, chave_json, pasta_id, publicados_id=None, sessao=None):
        self.pasta_id = pasta_id
        self.publicados_id = publicados_id
        if sessao is None:
            escopo = ESCOPO_TOTAL if publicados_id else ESCOPO_LEITURA
            credenciais = service_account.Credentials.from_service_account_info(
                json.loads(chave_json), scopes=[escopo]
            )
            sessao = AuthorizedSession(credenciais)
        self.sessao = sessao

    def _pedir(self, metodo, url, **kwargs):
        resposta = self.sessao.request(metodo, url, timeout=120, **kwargs)
        if resposta.status_code >= 400:
            raise ErroDrive(f"Drive respondeu {resposta.status_code} em {metodo} {url.rsplit('/', 1)[-1].split('?')[0]}.")
        return resposta

    def _listar(self):
        arquivos, pagina = [], None
        while True:
            parametros = {
                "q": f"'{self.pasta_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, md5Checksum, size)",
                "pageSize": 1000,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if pagina:
                parametros["pageToken"] = pagina
            corpo = self._pedir("GET", f"{API}/files", params=parametros).json()
            arquivos.extend(corpo.get("files", []))
            pagina = corpo.get("nextPageToken")
            if not pagina:
                return arquivos

    def fila(self):
        """Vídeos MP4 da pasta, em ordem alfabética, cada um com o id do .json de legenda (se houver)."""
        arquivos = self._listar()
        legendas = {a["name"][:-5].lower(): a["id"] for a in arquivos if a["name"].lower().endswith(".json")}
        videos = []
        for a in sorted(arquivos, key=lambda x: x["name"].lower()):
            if a["name"].lower().endswith(".mp4"):
                a["legenda_id"] = legendas.get(a["name"][:-4].lower())
                videos.append(a)
        return videos

    def baixar(self, id_arquivo, destino):
        resposta = self._pedir(
            "GET", f"{API}/files/{id_arquivo}", params={"alt": "media", "supportsAllDrives": "true"}, stream=True
        )
        with open(destino, "wb") as saida:
            for pedaco in resposta.iter_content(chunk_size=1024 * 1024):
                saida.write(pedaco)

    def ler_texto(self, id_arquivo):
        resposta = self._pedir("GET", f"{API}/files/{id_arquivo}", params={"alt": "media", "supportsAllDrives": "true"})
        return resposta.content.decode("utf-8")

    def mover_para_publicados(self, ids):
        """Melhor esforço: se falhar, o estado continua sendo a fonte da verdade."""
        if not self.publicados_id:
            return
        for id_arquivo in ids:
            try:
                self._pedir(
                    "PATCH",
                    f"{API}/files/{id_arquivo}",
                    params={"addParents": self.publicados_id, "removeParents": self.pasta_id, "supportsAllDrives": "true"},
                    json={},
                )
            except ErroDrive as erro:
                print(f"::warning::Não consegui mover um arquivo para Publicados ({erro}).")
