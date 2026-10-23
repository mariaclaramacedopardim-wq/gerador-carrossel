"""Estado do publicador: fila e horários do dia.

O arquivo vai para uma branch PÚBLICA. Por isso guarda só IDs do Drive, checksums, datas e status:
nunca legendas, nomes de arquivo, tokens ou chaves.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

PENDENTE = "pendente"
ENVIANDO = "enviando"
PUBLICADO = "publicado"
FALHOU = "falhou"


def _agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Estado:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.dados = {"versao": 1, "videos": {}, "dias": {}}
        if self.caminho.exists():
            self.dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.dados.setdefault("videos", {})
        self.dados.setdefault("dias", {})

    def salvar(self):
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(".tmp")
        temporario.write_text(
            json.dumps(self.dados, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(temporario, self.caminho)

    # --- vídeos -------------------------------------------------------------------------------
    def video(self, id_drive):
        return self.dados["videos"].get(id_drive)

    def registrar(self, id_drive, md5, **campos):
        registro = self.dados["videos"].setdefault(
            id_drive, {"md5": md5, "status": PENDENTE, "publish_id": None, "tentativas": 0, "erro": None}
        )
        registro["md5"] = md5
        registro.update(campos)
        registro["atualizado_em"] = _agora_iso()
        return registro

    def pode_publicar(self, id_drive, md5):
        """Falso se o arquivo (ou outro com o mesmo conteúdo) já foi publicado, está em envio ou falhou de vez."""
        registro = self.video(id_drive)
        if registro and registro["status"] in (PUBLICADO, ENVIANDO, FALHOU):
            return False
        if md5:
            for outro_id, outro in self.dados["videos"].items():
                if outro_id != id_drive and outro.get("md5") == md5 and outro["status"] in (PUBLICADO, ENVIANDO):
                    return False
        return True

    def em_envio(self):
        return {i: v for i, v in self.dados["videos"].items() if v["status"] == ENVIANDO}

    # --- dias ---------------------------------------------------------------------------------
    def dia(self, data_iso):
        return self.dados["dias"].setdefault(
            data_iso, {"horarios": [], "usados": [], "perdidos": [], "publicados": 0}
        )

    def podar_dias(self, hoje):
        corte = (hoje - timedelta(days=config.DIAS_DE_HISTORICO)).isoformat()
        for data_iso in [d for d in self.dados["dias"] if d < corte]:
            del self.dados["dias"][data_iso]

    def resumo(self):
        contagem = {}
        for v in self.dados["videos"].values():
            contagem[v["status"]] = contagem.get(v["status"], 0) + 1
        return contagem
