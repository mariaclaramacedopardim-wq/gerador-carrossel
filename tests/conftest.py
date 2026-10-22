import os
import shutil
from pathlib import Path

import pytest

PASTA_TESTE = Path(__file__).resolve().parent / "_dados_teste"
os.environ["ESTUDIO_REELS_DADOS"] = str(PASTA_TESTE / "dados")

from estudio_reels import amostras, projetos  # noqa: E402

precisa_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg não instalado")


@pytest.fixture(scope="session")
def videos_teste():
    """Vídeos sintéticos (padrões de teste do FFmpeg), criados uma vez por sessão."""
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg não instalado")
    return {p.name: p for p in amostras.criar_amostras(PASTA_TESTE / "amostras")}


@pytest.fixture(autouse=True)
def sem_segundo_plano():
    projetos.EXECUTAR_EM_SEGUNDO_PLANO = False
    yield


@pytest.fixture
def projeto_analisado(videos_teste):
    projeto = amostras.criar_projeto_exemplo()
    projetos.analisar(projeto["id"])
    estado = projetos.carregar(projeto["id"])["estado"]
    assert estado["erro"] is None, estado
    return projetos.carregar(projeto["id"])


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(PASTA_TESTE / "dados", ignore_errors=True)
