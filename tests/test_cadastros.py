"""Seções 14, 15 e 16: mesas, turnos, FAQ, bloqueios, semente e banco de dados."""
import subprocess

from conftest import RAIZ, Servidor

D = "2026-10-07"


def test_mesa_nova_validacoes_e_menor_max_vence(api):
    st, r = api.post("/api/mesas", {"id": "m6", "salao": "interno", "min": 1, "max": 3})
    assert st == 201, r
    m6 = next(m for m in api.get("/api/mesas")[1]["mesas"] if m["id"] == "m6")
    assert m6["ativa"] is True and m6["salao"] == "interno"
    assert api.post("/api/mesas", {"id": "m6", "salao": "interno", "min": 1, "max": 2})[0] == 409
    assert api.post("/api/mesas", {"id": "m7", "salao": "xyz", "min": 1, "max": 2})[0] == 404   # salão inexistente (regra geral, seção 5)
    assert api.post("/api/mesas", {"id": "m7", "salao": "interno", "min": 0, "max": 2})[0] == 422
    assert api.post("/api/mesas", {"id": "m7", "salao": "interno", "min": 3, "max": 2})[0] == 422
    assert api.put("/api/mesas/naoexiste", {"max": 4})[0] == 404
    cid = api.cliente()
    assert api.reserva(cid, f"{D}T12:00", 3)[1]["mesas"] == ["m6"]      # max 3 < 4 de m3
    assert api.put("/api/mesas/m6", {"max": 4})[1]["max"] == 4
    assert api.reserva(cid, f"{D}T19:00", 3)[1]["mesas"] == ["m3"]      # empate em max 4 → ordem do cadastro


def test_desativar_mesa(api):
    cid = api.cliente()
    _, a = api.reserva(cid, f"{D}T12:00", 5)                            # m5
    st, r = api.delete("/api/mesas/m5")
    assert st == 200 and r["ativa"] is False
    st, r = api.reserva(cid, f"{D}T19:00", 5)
    assert (st, r["erro"]) == (409, "sem_mesa")                          # combinação tem min 7
    assert api.reserva(cid, f"{D}T19:00", 7)[1]["mesas"] == ["m3", "m4"]
    assert api.reserva(cid, f"{D}T12:00", 2, mesa="m5")[0] == 422
    assert [x["id"] for x in api.reservas(D) if x["status"] == "reservada"] and api.por_id(D, a["id"])["mesas"] == ["m5"]
    assert api.get(f"/api/ocupacao?data={D}")[1]["horarios"][0]["mesas_total"] == 6
    assert next(m for m in api.get("/api/mesas")[1]["mesas"] if m["id"] == "m5")["ativa"] is False


def test_turno_novo_e_validacoes(api):
    st, r = api.post("/api/turnos", {"id": "seg_almoco", "nome": "Almoço de segunda", "dias": ["seg"],
                                      "inicio": "11:30", "fim": "14:00"})
    assert st == 201, r
    st, r = api.get("/api/horarios?data=2026-10-12&pessoas=2", token=None)   # segunda 12/10
    assert [(h["inicio"][11:], h["turno"]) for h in r["horarios"]] == \
        [("11:30", "seg_almoco"), ("12:00", "seg_almoco"), ("12:30", "seg_almoco")]   # 12:30 + 90 = 14:00
    assert api.post("/api/turnos", {"id": "seg_almoco", "nome": "X", "dias": ["seg"], "inicio": "16:00", "fim": "17:00"})[0] == 409
    assert api.post("/api/turnos", {"id": "t1", "nome": "X", "dias": ["xyz"], "inicio": "16:00", "fim": "17:00"})[0] == 422
    assert api.post("/api/turnos", {"id": "t2", "nome": "X", "dias": ["seg"], "inicio": "17:00", "fim": "17:00"})[0] == 422
    assert api.post("/api/turnos", {"id": "t3", "nome": "X", "dias": ["ter"], "inicio": "14:00", "fim": "16:00"})[0] == 422  # sobrepõe almoço
    st, r = api.post("/api/turnos", {"id": "tarde", "nome": "Tarde", "dias": ["ter"], "inicio": "15:00", "fim": "17:00"})
    assert st == 201                                                         # encosta, não sobrepõe
    h = api.horarios("2026-10-13", 2)                                        # terça 13/10
    assert "2026-10-13T15:00" in h and "2026-10-13T15:30" in h and "2026-10-13T16:00" not in h


def test_desativar_turno(api):
    cid = api.cliente()
    _, a = api.reserva(cid, f"{D}T19:00", 2)
    st, r = api.delete("/api/turnos/jantar")
    assert st == 200 and r["ativo"] is False
    assert [x[11:] for x in api.horarios(D, 2)] == ["11:30", "12:00", "12:30", "13:00", "13:30"]
    assert [t["id"] for t in api.get("/api/turnos", token=None)[1]["turnos"]] == ["almoco"]
    assert api.por_id(D, a["id"])["status"] == "reservada"
    assert api.reserva(cid, f"{D}T20:00", 2)[0] == 422
    assert api.post("/api/espera", {"cliente_id": cid, "data": D, "turno": "jantar", "pessoas": 2})[0] == 404


def test_faq_crud_vale_na_hora(api):
    st, r = api.post("/api/faq", {"perguntas": ["tem rodízio", "fazem rodizio"], "resposta": "Rodízio só aos domingos."})
    assert st == 201
    assert api.msg("41988887777", "vocês fazem rodízio?") == "Rodízio só aos domingos."
    assert api.delete(f"/api/faq/{r['id']}")[0] == 204
    assert api.msg("41988887777", "vocês fazem rodízio?") != "Rodízio só aos domingos."
    ids = [f["id"] for f in api.get("/api/faq")[1]["faq"]]
    assert "pet" in ids and r["id"] not in ids


def test_bloqueio_do_restaurante_inteiro(api):
    cid = api.cliente()
    _, a = api.reserva(cid, "2026-10-08T12:00", 2)
    st, r = api.post("/api/bloqueios", {"inicio": "2026-10-08T00:00", "fim": "2026-10-09T00:00", "motivo": "evento fechado"})
    assert st == 201 and r["conflitos"] == [a["id"]]
    assert api.horarios("2026-10-08", 2) == []
    assert api.reserva(cid, "2026-10-08T19:00", 2)[0] == 422
    assert api.reserva(cid, "2026-10-09T12:00", 2)[0] == 201
    st, lista = api.get("/api/bloqueios")
    assert [(b["motivo"], b["salao"], b["mesa"]) for b in lista["bloqueios"]] == [("evento fechado", None, None)]
    assert api.delete(f"/api/bloqueios/{r['id']}")[0] == 204
    assert len(api.horarios("2026-10-08", 2)) == 11                       # m2 serve mesmo com a em m1


def test_bloqueio_de_mesa_e_de_salao(api):
    cid = api.cliente()
    st, r = api.post("/api/bloqueios", {"inicio": "2026-10-08T00:00", "fim": "2026-10-09T00:00", "motivo": "conserto", "mesa": "m5"})
    assert st == 201 and r["conflitos"] == []
    st, r = api.reserva(cid, "2026-10-08T12:00", 5)
    assert (st, r["erro"]) == (409, "sem_mesa")
    assert api.reserva(cid, "2026-10-09T12:00", 5)[1]["mesas"] == ["m5"]
    assert api.horarios("2026-10-08", 5) == []
    st, r = api.post("/api/bloqueios", {"inicio": "2026-10-08T00:00", "fim": "2026-10-09T00:00", "motivo": "chuva", "salao": "varanda"})
    assert st == 201
    assert api.horarios("2026-10-08", 2, salao="varanda") == []
    assert api.reserva(cid, "2026-10-08T12:00", 2)[1]["mesas"] == ["m1"]
    assert api.post("/api/bloqueios", {"inicio": "2026-10-08T00:00", "fim": "2026-10-09T00:00", "motivo": "x", "salao": "xyz"})[0] == 404
    assert api.post("/api/bloqueios", {"inicio": "2026-10-08T00:00", "fim": "2026-10-09T00:00", "motivo": "x", "mesa": "xyz"})[0] == 404


def test_semente_so_na_primeira_vez(dados):
    s = Servidor(dados)
    api = s.subir()
    api.post("/api/mesas", {"id": "m6", "salao": "varanda", "min": 1, "max": 2})
    api.delete("/api/faq/pet")
    s.parar()
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        assert [m["id"] for m in api2.get("/api/mesas")[1]["mesas"]] == ["m1", "m2", "m3", "m4", "m5", "v1", "v2", "m6"]
        assert "pet" not in [f["id"] for f in api2.get("/api/faq")[1]["faq"]]
    finally:
        s2.parar()


def test_backup_e_restaurar(dados, tmp_path):
    s = Servidor(dados)
    api = s.subir()
    cid = api.cliente("Guardada", "41999990009")
    api.reserva(cid, f"{D}T12:00", 2)
    arq = tmp_path / "copia.bak"
    r = subprocess.run([str(RAIZ / "reserva"), "backup", "--dados", str(dados), "--saida", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0 and arq.exists() and arq.stat().st_size > 0
    api.delete(f"/api/clientes/{cid}")
    api.cliente("Depois do backup", "41999990010")
    s.parar()
    r = subprocess.run([str(RAIZ / "reserva"), "restaurar", "--dados", str(dados), "--entrada", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        assert [c["nome"] for c in api2.get("/api/clientes")[1]["clientes"]] == ["Guardada"]
        assert [x["status"] for x in api2.reservas(D)] == ["reservada"]
    finally:
        s2.parar()
