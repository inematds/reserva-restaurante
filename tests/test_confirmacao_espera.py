"""Seções 7 e 8: confirmação automática (24 h), resposta 1/2, lista de espera, remarcação.

Agora = ter 06/10/2026 10:00; 06/10 19:00 está a 9 h (pede confirmação); 07/10 12:00 a 26 h (ainda não).
"""
from conftest import Servidor, norm

T1, T2, T3, T4 = "41999990001", "41999990002", "41999990003", "41999990004"


def rodar(api, agora=None):
    st, r = api.post("/api/tarefas/rodar", {"agora": agora} if agora else {})
    assert st == 200, (st, r)
    return r["enviadas"]


def test_confirmacao_dentro_de_24h_uma_vez(api):
    p1 = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    _, a = api.reserva(p1, "2026-10-06T19:00", 2)
    _, b = api.reserva(p2, "2026-10-07T12:00", 2)
    assert rodar(api) == 1
    [m] = api.saida("confirmacao")
    assert m["reserva_id"] == a["id"] and m["telefone"] == "+5541999990001" and m["cliente_id"] == p1
    t = norm(m["texto"])
    for trecho in ("06/10", "19:00", "2 pessoas", "1", "2"):
        assert trecho in t, trecho
    assert "r$" not in t
    assert rodar(api) == 0
    assert rodar(api, "2026-10-06T12:30") == 1                 # 07/10 12:00 passa a estar a 23,5 h
    assert [x["reserva_id"] for x in api.saida("confirmacao")] == [a["id"], b["id"]]


def test_responder_1_confirma(api):
    p = api.cliente("Maria", T1)
    _, a = api.reserva(p, "2026-10-06T19:00", 2)
    rodar(api)
    assert "confirmad" in norm(api.msg(T1, "1"))
    assert api.por_id("2026-10-06", a["id"])["status"] == "confirmada"
    assert rodar(api) == 0


def test_responder_2_cancela(api):
    p = api.cliente("Maria", T1)
    _, a = api.reserva(p, "2026-10-06T19:00", 2)
    rodar(api)
    assert "cancelad" in norm(api.msg(T1, "2"))
    assert api.por_id("2026-10-06", a["id"])["status"] == "cancelada"


def test_pendente_nao_recebe_confirmacao(api):
    p = api.cliente("Maria", T1)
    st, a = api.reserva(p, "2026-10-06T19:00", 8)
    assert st == 201 and a["status"] == "pendente"
    assert rodar(api) == 0
    api.post(f"/api/reservas/{a['id']}/aprovar")
    assert rodar(api) == 1                                       # aprovada → reservada → confirmação devida


def test_remarcar_pede_confirmacao_de_novo(api):
    p = api.cliente("Maria", T1)
    _, a = api.reserva(p, "2026-10-06T19:00", 2)
    assert rodar(api) == 1
    api.msg(T1, "1")                                             # confirmada
    st, r = api.post(f"/api/reservas/{a['id']}/remarcar", {"inicio": "2026-10-06T20:00"})
    assert st == 200 and r["status"] == "reservada"
    assert rodar(api) == 1
    assert "20:00" in api.saida("confirmacao")[1]["texto"]


def test_lista_de_espera_oferece_e_reserva(api):
    p1 = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    p3 = api.cliente("Rita", T3)
    _, a = api.reserva(p1, "2026-10-07T19:00", 7)                # m3+m4 19:00–22:00: jantar lotado para 7
    assert api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-07", "turno": "jantar", "pessoas": 7})[0] == 201
    assert api.post("/api/espera", {"cliente_id": p3, "data": "2026-10-07", "turno": "jantar", "pessoas": 7})[0] == 201
    assert api.post("/api/espera", {"cliente_id": p3, "data": "2026-10-07", "turno": "xyz", "pessoas": 7})[0] == 404
    st, r = api.post(f"/api/reservas/{a['id']}/cancelar")
    assert st == 200
    ofertas = api.saida("espera")
    assert [m["telefone"] for m in ofertas] == ["+5541999990002"]
    assert "19:00" in ofertas[0]["texto"] and "1" in ofertas[0]["texto"]
    fila = api.get("/api/espera?data=2026-10-07")[1]["espera"]
    assert [(e["cliente_id"], e["status"]) for e in fila] == [(p2, "ofertada"), (p3, "pendente")]
    assert "reservad" in norm(api.msg(T2, "1"))
    ativos = [x for x in api.reservas("2026-10-07") if x["status"] != "cancelada"]
    assert [(x["cliente_id"], x["inicio"], x["mesas"]) for x in ativos] == [(p2, "2026-10-07T19:00", ["m3", "m4"])]
    assert api.get("/api/espera?data=2026-10-07")[1]["espera"][0]["status"] == "atendida"


def test_espera_horario_ja_ocupado(api):
    p1 = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    p4 = api.cliente("Ana", T4)
    _, a = api.reserva(p1, "2026-10-07T19:00", 7)
    api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-07", "turno": "jantar", "pessoas": 7})
    api.post(f"/api/reservas/{a['id']}/cancelar")
    assert api.reserva(p4, "2026-10-07T19:00", 7)[0] == 201
    assert "ocupad" in norm(api.msg(T2, "1"))


def test_espera_de_outro_turno_dia_ou_grupo_que_nao_cabe_nao_recebe(api):
    p1 = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    p3 = api.cliente("Rita", T3)
    p4 = api.cliente("Ana", T4)
    _, a = api.reserva(p1, "2026-10-07T19:00", 7)
    api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-07", "turno": "almoco", "pessoas": 7})
    api.post("/api/espera", {"cliente_id": p3, "data": "2026-10-07", "turno": "jantar", "pessoas": 9})
    api.post("/api/espera", {"cliente_id": p4, "data": "2026-10-08", "turno": "jantar", "pessoas": 7})
    api.post(f"/api/reservas/{a['id']}/cancelar")
    assert api.saida("espera") == []


def test_cancelar_pela_conversa_dispara_espera(api):
    p1 = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    api.reserva(p1, "2026-10-06T19:00", 2)
    api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-06", "turno": "jantar", "pessoas": 2})
    rodar(api)
    assert "cancelad" in norm(api.msg(T1, "2"))
    [m] = api.saida("espera")
    assert m["telefone"] == "+5541999990002" and "19:00" in m["texto"]


def test_confirmacao_sobrevive_a_reinicio(dados):
    s = Servidor(dados)
    api = s.subir()
    p = api.cliente("Maria", T1)
    api.reserva(p, "2026-10-06T19:00", 2)
    assert rodar(api) == 1
    s.parar()
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        assert rodar(api2) == 0
        assert "confirmad" in norm(api2.msg(T1, "sim"))
    finally:
        s2.parar()
