"""Seções 3 e 5: reserva, alocação, limite da cozinha, conflito, cancelar, remarcar, chegada, listagem, ocupação.

Agora = ter 06/10/2026 10:00. Mesas: m1 m2 (1–2) m3 m4 (3–4) m5 (5–6) interno; v1 v2 (1–4) varanda; m3+m4 (7–8).
"""
import threading

D = "2026-10-07"


def test_reservar_e_listar(api):
    cid = api.cliente()
    st, r = api.reserva(cid, f"{D}T12:00", 4)
    assert st == 201, r
    for k, v in {"status": "reservada", "inicio": f"{D}T12:00", "fim": f"{D}T14:00", "pessoas": 4,
                 "turno": "almoco", "salao": "interno", "mesas": ["m3"], "cliente_id": cid}.items():
        assert r[k] == v, k
    [a] = api.reservas(D)
    assert (a["id"], a["nome"], a["telefone"], a["pessoas"], a["mesas"]) == (r["id"], "Maria Silva", "+5541999990001", 4, ["m3"])


def test_menor_mesa_que_serve_e_desempate_pela_ordem(api):
    cid = api.cliente()
    esperado = [(1, ["m1"]), (1, ["m2"]), (1, ["v1"]), (1, ["v2"]), (3, ["m3"]), (3, ["m4"]), (5, ["m5"])]
    for pessoas, mesas in esperado:          # soma = 15 ≤ limite 20
        st, r = api.reserva(cid, f"{D}T12:00", pessoas)
        assert (st, r["mesas"]) == (201, mesas), (pessoas, st, r)
    st, r = api.reserva(cid, f"{D}T12:00", 1)
    assert (st, r["erro"]) == (409, "sem_mesa")


def test_combinacao_so_quando_nenhuma_mesa_unica_serve(api):
    cid = api.cliente()
    st, r = api.reserva(cid, f"{D}T12:00", 7)
    assert st == 201 and r["mesas"] == ["m3", "m4"] and r["fim"] == f"{D}T15:00"
    assert api.reserva(cid, f"{D}T12:00", 3)[1]["mesas"] == ["v1"]       # m3/m4 ocupadas
    assert api.reserva(cid, f"{D}T19:00", 7)[0] == 201                   # 19:00–22:00
    st, r = api.reserva(cid, f"{D}T19:30", 7)
    assert (st, r["erro"]) == (409, "sem_mesa")                          # combinação ocupada
    assert api.reserva(cid, f"{D}T19:00", 5)[1]["mesas"] == ["m5"]
    st, r = api.reserva(cid, f"{D}T19:00", 6)                            # m5 ocupada; combinação tem min 7
    assert (st, r["erro"]) == (409, "sem_mesa")


def test_mesa_e_salao_explicitos(api):
    cid = api.cliente()
    assert api.reserva(cid, f"{D}T12:00", 2, mesa="m5")[0] == 422      # min 5
    assert api.reserva(cid, f"{D}T12:00", 3, mesa="m1")[0] == 422      # max 2
    assert api.reserva(cid, f"{D}T12:00", 2, mesa="xyz")[0] == 404
    st, r = api.reserva(cid, f"{D}T12:00", 2, mesa="m1")
    assert st == 201 and r["mesas"] == ["m1"]
    st, r = api.reserva(cid, f"{D}T12:00", 2, mesa="m1")
    assert (st, r["erro"]) == (409, "sem_mesa")
    st, r = api.reserva(cid, f"{D}T12:00", 7, mesa="m3m4")
    assert st == 201 and r["mesas"] == ["m3", "m4"]
    st, r = api.reserva(cid, f"{D}T12:00", 2, salao="varanda")
    assert st == 201 and r["mesas"] == ["v1"] and r["salao"] == "varanda"
    assert api.reserva(cid, f"{D}T12:00", 2, salao="xyz")[0] == 404


def test_limite_da_cozinha_por_horario(api):
    cid = api.cliente()
    for pessoas in (6, 4, 4, 4):               # m5, m3, m4, v1 → 18 pessoas às 12:00
        assert api.reserva(cid, f"{D}T12:00", pessoas)[0] == 201
    st, r = api.reserva(cid, f"{D}T12:00", 4)  # v2 livre, mas 22 > 20
    assert (st, r["erro"]) == (409, "limite_cozinha")
    assert api.reserva(cid, f"{D}T12:00", 2)[0] == 201                  # m1 → 20
    st, r = api.reserva(cid, f"{D}T12:00", 1)
    assert (st, r["erro"]) == (409, "limite_cozinha")                    # m2 livre, 21 > 20
    h = api.horarios(D, 1)
    assert f"{D}T12:00" not in h and f"{D}T12:30" in h                  # 12:30 soma 0


def test_invalidos_422(api):
    cid = api.cliente()
    for inicio, pessoas in [
        (f"{D}T12:15", 2),          # fora da grade
        (f"{D}T14:00", 2),          # 14:00 + 90 > 15:00, não cabe no turno
        (f"{D}T16:00", 2),          # fora de turno
        (f"{D}T12:30", 7),          # 12:30 + 180 > 15:00
        ("2026-10-15T12:00", 2),    # feriado
        ("2026-10-12T12:00", 2),    # segunda, sem turno
        ("2026-10-11T19:00", 2),    # domingo não tem jantar
        ("2026-11-06T12:00", 2),    # fora da janela (06/10 + 30 = 05/11)
        ("2026-10-05T12:00", 2),    # passado
        (f"{D}T12:00", 0),          # pessoas < 1
    ]:
        assert api.reserva(cid, inicio, pessoas)[0] == 422, (inicio, pessoas)


def test_antecedencia_e_janela_nas_pontas(dados):
    from conftest import Servidor
    s = Servidor(dados, agora="2026-10-06T11:00")    # agora + 1 h = 12:00
    try:
        api = s.subir()
        cid = api.cliente()
        assert api.reserva(cid, "2026-10-06T11:30", 2)[0] == 422
        assert api.reserva(cid, "2026-10-06T12:00", 2)[0] == 201
        assert api.reserva(cid, "2026-11-05T12:00", 2)[0] == 201   # 06/10 + 30 dias, inclusivo
        assert api.reserva(cid, "2026-11-06T12:00", 2)[0] == 422
    finally:
        s.parar()


def test_inexistentes_404(api):
    cid = api.cliente()
    assert api.reserva(9999, f"{D}T12:00", 2)[0] == 404
    assert api.post(f"/api/reservas/9999/cancelar")[0] == 404
    assert api.get("/api/clientes/9999/dados")[0] == 404
    assert cid


def test_concorrencia_um_so_vence(api):
    cid = api.cliente()
    codigos = []

    def tenta():
        codigos.append(api.reserva(cid, "2026-10-08T12:00", 2, mesa="m1")[0])

    ts = [threading.Thread(target=tenta) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codigos) == [201] + [409] * 9


def test_cancelar_libera_e_so_de_ativa(api):
    cid = api.cliente()
    _, a = api.reserva(cid, f"{D}T12:00", 2, mesa="m1")
    st, r = api.post(f"/api/reservas/{a['id']}/cancelar")
    assert st == 200 and r["status"] == "cancelada"
    assert api.reserva(cid, f"{D}T12:00", 2, mesa="m1")[0] == 201
    st, r = api.post(f"/api/reservas/{a['id']}/cancelar")
    assert (st, r["erro"]) == (409, "status")
    assert api.por_id(D, a["id"])["status"] == "cancelada"   # listagem inclui canceladas


def test_remarcar(api):
    cid = api.cliente()
    _, a = api.reserva(cid, f"{D}T12:00", 4)       # m3
    _, b = api.reserva(cid, f"{D}T12:00", 4)       # m4
    st, r = api.post(f"/api/reservas/{a['id']}/remarcar", {"inicio": f"{D}T12:00"})
    assert st == 200 and r["mesas"] == ["m3"]                     # as próprias mesas contam como livres
    assert api.post(f"/api/reservas/{a['id']}/remarcar", {"inicio": f"{D}T12:15"})[0] == 422
    assert api.post(f"/api/reservas/{a['id']}/remarcar", {})[0] == 422
    st, r = api.post(f"/api/reservas/{a['id']}/remarcar", {"pessoas": 7})
    assert (st, r["erro"]) == (409, "sem_mesa")                   # precisaria de m4, que é de b
    st, r = api.post(f"/api/reservas/{a['id']}/remarcar", {"inicio": "2026-10-08T19:00", "pessoas": 7})
    assert st == 200 and r["id"] == a["id"] and r["mesas"] == ["m3", "m4"] and r["fim"] == "2026-10-08T22:00"
    assert r["status"] == "reservada" and r["pessoas"] == 7
    assert api.reserva(cid, f"{D}T12:00", 4)[1]["mesas"] == ["m3"]   # 07/10 12:00 liberou
    st, r = api.post(f"/api/reservas/{a['id']}/remarcar", {"pessoas": 8})
    assert st == 200 and r["status"] == "pendente"
    api.post(f"/api/reservas/{b['id']}/cancelar")
    assert api.post(f"/api/reservas/{b['id']}/remarcar", {"inicio": f"{D}T13:00"})[0] == 409


def test_chegada_no_show_e_visitas(api):
    cid = api.cliente()
    _, a = api.reserva(cid, f"{D}T12:00", 2, mesa="m1")
    _, b = api.reserva(cid, "2026-10-08T12:00", 2, mesa="m1")
    assert api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": True})[1]["status"] == "chegou"
    st, c = api.get(f"/api/clientes/{cid}/dados")
    assert c["cliente"]["ultima_visita"] == D and c["cliente"]["visitas"] == 1
    assert api.post(f"/api/reservas/{b['id']}/chegada", {"compareceu": False})[1]["status"] == "no_show"
    assert api.get(f"/api/clientes/{cid}/dados")[1]["cliente"]["visitas"] == 1
    assert api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": True})[0] == 409
    assert api.post(f"/api/reservas/{b['id']}/cancelar")[0] == 409
    # no_show continua ocupando a mesa
    assert api.reserva(cid, "2026-10-08T12:00", 2, mesa="m1")[0] == 409


def test_listar_por_periodo_turno_e_salao(api):
    cid = api.cliente()
    api.reserva(cid, "2026-10-09T12:00", 2)
    api.reserva(cid, f"{D}T19:00", 2)
    api.reserva(cid, "2026-10-08T12:00", 2, salao="varanda")
    api.reserva(cid, f"{D}T12:00", 2)
    st, r = api.get("/api/reservas?de=2026-10-07&ate=2026-10-08")
    assert [x["inicio"] for x in r["reservas"]] == [f"{D}T12:00", f"{D}T19:00", "2026-10-08T12:00"]
    assert [x["inicio"] for x in api.reservas(D, turno="jantar")] == [f"{D}T19:00"]
    lista = api.reservas("2026-10-08", salao="varanda")
    assert len(lista) == 1 and lista[0]["mesas"] == ["v1"]
    st, r = api.get("/api/reservas?de=2026-10-07&ate=2026-10-09&salao=interno")
    assert [x["inicio"][:10] for x in r["reservas"]] == [D, D, "2026-10-09"]


def test_ocupacao_por_horario(api):
    cid = api.cliente()
    api.reserva(cid, f"{D}T12:00", 2, mesa="m1")   # 12:00–13:30
    api.reserva(cid, f"{D}T12:30", 4)              # m3, 12:30–14:30
    api.reserva(cid, f"{D}T19:00", 7)              # m3+m4, 19:00–22:00
    st, r = api.get(f"/api/ocupacao?data={D}")
    assert st == 200 and r["data"] == D
    por = {h["inicio"][11:]: h for h in r["horarios"]}
    # grade: almoço 11:30..14:30 (7 instantes < 15:00) + jantar 19:00..22:30 (8)
    assert list(por) == ["11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
                         "19:00", "19:30", "20:00", "20:30", "21:00", "21:30", "22:00", "22:30"]
    assert all(h["mesas_total"] == 7 for h in r["horarios"])
    assert (por["11:30"]["mesas_ocupadas"], por["11:30"]["pessoas"]) == (0, 0)
    assert (por["12:00"]["mesas_ocupadas"], por["12:00"]["pessoas"]) == (1, 2)
    assert (por["12:30"]["mesas_ocupadas"], por["12:30"]["pessoas"]) == (2, 6)
    assert (por["13:30"]["mesas_ocupadas"], por["13:30"]["pessoas"]) == (1, 4)   # m1 acaba às 13:30 (semiaberto)
    assert (por["14:30"]["mesas_ocupadas"], por["14:30"]["pessoas"]) == (0, 0)
    assert (por["19:00"]["mesas_ocupadas"], por["19:00"]["pessoas"], por["19:00"]["turno"]) == (2, 7, "jantar")
    assert (por["22:00"]["mesas_ocupadas"], por["22:00"]["pessoas"]) == (0, 0)
    st, r = api.get(f"/api/ocupacao?data={D}&salao=varanda")
    assert r["horarios"][1]["mesas_total"] == 2 and r["horarios"][1]["mesas_ocupadas"] == 0
    assert api.get("/api/ocupacao?data=2026-10-12")[1]["horarios"] == []


def test_telefone_normalizado_e_duplicado(api):
    st, r = api.post("/api/clientes", {"nome": "A", "telefone": "(41) 99999-0001"})
    assert st == 201
    st2, r2 = api.post("/api/clientes", {"nome": "A", "telefone": "+55 41 99999 0001"})
    assert st2 == 200 and r2["id"] == r["id"]
    st3, r3 = api.post("/api/clientes", {"nome": "B", "telefone": "41 3333-4444"})
    assert st3 == 201 and r3["id"] != r["id"]
    st, d = api.get(f"/api/clientes/{r3['id']}/dados")
    assert d["cliente"]["telefone"] == "+554133334444"
    for ruim in ("123", "abc", "+55 41 9999"):
        assert api.post("/api/clientes", {"nome": "C", "telefone": ruim})[0] == 400, ruim
