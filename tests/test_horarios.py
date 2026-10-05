"""Seção 3 e `GET /api/horarios`: grade por duração, turnos, feriado, antecedência, janela, salão.

Fixture: almoço 11:30–15:00 (ter–dom), jantar 19:00–23:00 (ter–sab); passo 30; duração 90 (≤2), 120 (≤6), 180 (7+).
Agora = ter 06/10/2026 10:00. 07/10 é quarta; 11/10 domingo; 12/10 segunda (fechado); 15/10 feriado (quinta).
"""
from conftest import Servidor

D = "2026-10-07"


def com_turno(api, data, pessoas):
    st, r = api.get(f"/api/horarios?data={data}&pessoas={pessoas}", token=None)
    assert st == 200, (st, r)
    return [(h["inicio"][11:], h["turno"]) for h in r["horarios"]]


def test_grade_2_pessoas_90_min(api):
    # almoço: 11:30 + k·30 com inicio + 90 ≤ 15:00 → 11:30..13:30 (5); jantar: 19:00..21:30 (6)
    assert com_turno(api, D, 2) == [(h, "almoco") for h in ("11:30", "12:00", "12:30", "13:00", "13:30")] + \
        [(h, "jantar") for h in ("19:00", "19:30", "20:00", "20:30", "21:00", "21:30")]


def test_grade_4_pessoas_120_min(api):
    h = api.horarios(D, 4)
    # 13:00 + 120 = 15:00 cabe; 13:30 não; jantar até 21:00 (21:00 + 120 = 23:00)
    assert h == [f"{D}T{x}" for x in ("11:30", "12:00", "12:30", "13:00", "19:00", "19:30", "20:00", "20:30", "21:00")]


def test_grade_7_pessoas_180_min_so_pela_combinacao(api):
    # só m3+m4 (min 7, max 8) serve 7; 180 min: almoço 11:30 e 12:00 (12:00 + 180 = 15:00); jantar 19:00..20:00
    assert api.horarios(D, 7) == [f"{D}T{x}" for x in ("11:30", "12:00", "19:00", "19:30", "20:00")]
    assert api.horarios(D, 8) == api.horarios(D, 7)   # 8 cabe na combinação (grupo grande, mas lista)
    assert api.horarios(D, 9) == []                   # nada serve 9


def test_domingo_so_almoco_segunda_fechado_feriado(api):
    assert com_turno(api, "2026-10-11", 2) == [(h, "almoco") for h in ("11:30", "12:00", "12:30", "13:00", "13:30")]
    assert api.horarios("2026-10-12", 2) == []   # segunda: nenhum turno
    assert api.horarios("2026-10-15", 2) == []   # feriado (quinta)
    assert len(api.horarios("2026-10-16", 2)) == 11


def test_antecedencia_minima_corta_o_primeiro_horario(dados):
    s = Servidor(dados, agora="2026-10-06T11:00")   # agora + 1 h = 12:00 → 11:30 cai, 12:00 fica
    try:
        api = s.subir()
        h = api.horarios("2026-10-06", 2)
        assert h[0] == "2026-10-06T12:00" and "2026-10-06T11:30" not in h
    finally:
        s.parar()


def test_janela_maxima_inclusiva(api):
    # 06/10 + 30 dias = 05/11 (quinta) ainda vale; 06/11 não
    assert len(api.horarios("2026-11-05", 2)) == 11
    assert api.horarios("2026-11-06", 2) == []
    assert api.horarios("2026-10-05", 2) == []   # passado


def test_parametros_invalidos(api):
    assert api.get(f"/api/horarios?data={D}", token=None)[0] == 422
    assert api.get(f"/api/horarios?data={D}&pessoas=0", token=None)[0] == 422
    assert api.get(f"/api/horarios?data={D}&pessoas=abc", token=None)[0] == 422
    assert api.get(f"/api/horarios?data={D}&pessoas=2&salao=xyz", token=None)[0] == 404


def test_filtro_por_salao(api):
    assert len(api.horarios(D, 2, salao="varanda")) == 11   # v1/v2 servem 1–4
    assert api.horarios(D, 5, salao="varanda") == []         # nada na varanda serve 5
    assert len(api.horarios(D, 5, salao="interno")) == 9     # m5, 120 min


def test_horario_some_quando_as_mesas_que_servem_estao_ocupadas(api):
    cid = api.cliente()
    for mesa in ("m1", "m2", "v1", "v2"):          # todas as mesas que servem 2 pessoas, 12:00–13:30
        assert api.reserva(cid, f"{D}T12:00", 2, mesa=mesa)[0] == 201
    h = api.horarios(D, 2)
    # 11:30 (até 13:00), 12:00, 12:30 e 13:00 (até 14:30) sobrepõem [12:00, 13:30); 13:30 não
    assert [x[11:] for x in h if x < f"{D}T19:00"] == ["13:30"]
    assert len(api.horarios(D, 3)) == 9             # m3/m4 (min 3) continuam livres: grade cheia para 3
