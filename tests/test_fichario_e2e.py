"""Teste ponta a ponta do Fichário (PWA) num Chromium de verdade, com dados fictícios.

Roda só se o Playwright e o Chromium estiverem instalados; senão, é pulado.
"""

import functools
import http.server
import json
import re
import shutil
import threading
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")

SITE = Path(__file__).resolve().parent.parent / "fichario"
CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
if not CHROMIUM:
    for candidate in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux*/chrome")):
        CHROMIUM = str(candidate)
if not CHROMIUM:
    pytest.skip("Chromium não encontrado", allow_module_level=True)

ROTINA = {"items": [
    {"id": "run-tq", "days": [2, 4], "time": "05:00", "end": "06:00", "kind": "task", "tag": "treino", "text": "corrida"},
    {"id": "med", "days": [0, 1, 2, 3, 4, 5, 6], "time": "07:40", "kind": "task", "tag": "", "text": "medicação"},
    {"id": "forca", "days": [1, 2, 3, 4], "time": "12:00", "end": "13:00", "kind": "task", "tag": "treino", "text": "almoço + força"},
    {"id": "rev", "days": [0, 1, 2, 3, 4, 5, 6], "time": "21:00", "end": "21:15", "kind": "event", "tag": "", "text": "revisão do dia"},
]}
BACKUP = {"app": "fichario", "versao": 1, "exportado": "2026-01-01T00:00:00Z", "fotos": {},
          "dados": {"settings/routine": ROTINA, "days/2026-10-13": {"date": "2026-10-13", "review": {"free": "dia de teste"}}}}


@pytest.fixture(scope="module")
def servidor():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()


def test_fluxo_completo(servidor, tmp_path):
    arquivo = tmp_path / "backup.json"
    arquivo.write_text(json.dumps(BACKUP), encoding="utf-8")
    with playwright.sync_playwright() as p:
        nav = p.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        ctx = nav.new_context(viewport={"width": 430, "height": 900}, accept_downloads=True, locale="pt-BR", timezone_id="America/Belem")
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/fonts.g*/**", lambda r: r.abort())
        pg.goto(servidor)
        pg.wait_for_selector(".logo")

        # restaurar backup
        pg.click("#dataBtn")
        with pg.expect_file_chooser() as fc:
            pg.click("text=restaurar backup")
        fc.value.set_files(str(arquivo))
        pg.wait_for_load_state("load")
        pg.wait_for_selector(".logo")
        pg.wait_for_function("localStorage.getItem('fichario:days/2026-10-13')")
        pg.wait_for_function("document.querySelector('#L').innerText.includes('medicação')")

        # medicação no Hoje
        assert "medicação de hoje" in pg.inner_text("#L")
        pg.click("button[data-act=medTake]")
        assert re.search(r"medicação tomada às \d\d:\d\d", pg.inner_text("#L"))
        pg.click("button[data-act=medUndo]")
        assert "medicação de hoje" in pg.inner_text("#L")

        # corpo sem prova, marcar e remover
        pg.click("button.tab.t-corpo")
        assert "sem prova marcada" in pg.inner_text("#L")
        pg.fill("#race-name", "10 km"); pg.fill("#race-date", "2099-12-06"); pg.fill("#race-dist", "10 km")
        pg.click("form[data-add=race] button")
        assert "dias" in pg.inner_text("#L")
        pg.click("button[data-act=raceClear]")
        assert "sem prova marcada" in pg.inner_text("#L")

        # ritual semanal
        pg.click("button.tab.t-planner")
        pg.click("[data-act=ritual]")
        pg.fill("#rt-text", "compromisso teste"); pg.fill("#rt-time", "08:00")
        pg.press("#rt-text", "Enter")
        assert "compromisso teste" in pg.inner_text("#panel")
        pg.click("[data-act=ritualStep][data-n='1']")
        assert "corrida" in pg.inner_text("#panel") and "descanso" in pg.inner_text("#panel")
        for _ in range(2):
            pg.click("[data-act=ritualStep][data-n='1']")
        pg.fill("form[data-add=li] input[name=t] >> nth=0", "marmita teste")
        pg.press("form[data-add=li] input[name=t] >> nth=0", "Enter")
        assert "marmita teste" in pg.inner_text("#panel")
        pg.click("[data-act=ritualStep][data-n='1']")
        pg.fill("#rp0", "prioridade teste")
        pg.wait_for_function("JSON.stringify(localStorage).includes('prioridade teste')")
        pg.click("[data-act=ritualDone]")
        assert pg.input_value("#wp0") == "prioridade teste"

        # lembretes .ics: no máximo 5 alarmes por dia
        pg.click("#dataBtn")
        with pg.expect_download() as dl:
            pg.click("[data-act=icsExport]")
        ics = Path(dl.value.path()).read_bytes().decode("utf-8")
        assert ics.startswith("BEGIN:VCALENDAR") and "tomar a medicação" in ics
        assert all(len(l.encode()) <= 75 for l in ics.split("\r\n"))
        por_dia = {}
        for ev in re.sub(r"\r\n ", "", ics).split("BEGIN:VEVENT")[1:]:
            dia = re.search(r"DTSTART:(\d{8})", ev).group(1)
            por_dia[dia] = por_dia.get(dia, 0) + ev.count("BEGIN:VALARM")
        assert max(por_dia.values()) <= 5

        # backup exportado
        with pg.expect_download() as dl2:
            pg.click("[data-act=backupExport]")
        saida = json.loads(Path(dl2.value.path()).read_text(encoding="utf-8"))
        assert saida["app"] == "fichario" and "settings/routine" in saida["dados"]

        # offline
        pg.evaluate("navigator.serviceWorker.ready")
        pg.reload()
        ctx.set_offline(True)
        pg.reload()
        pg.wait_for_selector(".logo", timeout=8000)
        assert pg.inner_text(".logo") == "Fichário"
        nav.close()
    assert not erros, erros
