import random
from datetime import datetime
from zoneinfo import ZoneInfo

from publicador_tiktok import agenda, config
from publicador_tiktok.estado import Estado

FUSO = ZoneInfo("America/Sao_Paulo")


def _min(horario):
    h, m = map(int, horario.split(":"))
    return h * 60 + m


def test_horarios_ficam_dentro_das_janelas_e_em_janelas_diferentes():
    for semente in range(200):
        horarios = agenda.sortear_horarios(3, rng=random.Random(semente))
        assert len(horarios) == 3
        for horario in horarios:
            assert any(_min(i) <= _min(horario) < _min(f) for i, f, _ in config.JANELAS)
        assert all(_min(b) - _min(a) >= 3 * 60 for a, b in zip(horarios, horarios[1:]))


def test_horarios_nao_sao_fixos():
    todos = {tuple(agenda.sortear_horarios(1, rng=random.Random(s))) for s in range(50)}
    assert len(todos) > 10


def test_quantidade_nunca_passa_do_numero_de_janelas():
    assert len(agenda.sortear_horarios(10)) == len(config.JANELAS)


def test_plano_do_dia_e_estavel(tmp_path):
    estado = Estado(tmp_path / "e.json")
    agora = datetime(2026, 10, 24, 6, 0, tzinfo=FUSO)
    primeiro = list(agenda.garantir_plano_do_dia(estado, agora, 2)["horarios"])
    assert agenda.garantir_plano_do_dia(estado, agora, 2)["horarios"] == primeiro


def test_horario_devido_respeita_tolerancia_e_marca_perdidos():
    dia = {"horarios": ["08:00", "13:00"], "usados": [], "perdidos": [], "publicados": 0}
    assert agenda.horario_devido(dia, datetime(2026, 10, 24, 7, 59, tzinfo=FUSO)) is None
    assert agenda.horario_devido(dia, datetime(2026, 10, 24, 8, 40, tzinfo=FUSO)) == "08:00"
    dia["usados"].append("08:00")
    assert agenda.horario_devido(dia, datetime(2026, 10, 24, 12, 0, tzinfo=FUSO)) is None
    # 13:00 passou há mais de 2 h: vira perdido
    assert agenda.horario_devido(dia, datetime(2026, 10, 24, 15, 30, tzinfo=FUSO)) is None
    assert dia["perdidos"] == ["13:00"]
