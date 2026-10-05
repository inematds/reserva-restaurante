"""Seções 1, 4, 5 (saúde/salões/turnos), 13 e persistência."""
from conftest import RAIZ, Servidor


def test_saude_traz_versao_do_arquivo(api):
    st, r = api.get("/api/saude", token=None)
    assert st == 200
    assert r["ok"] is True
    assert r["versao"] == (RAIZ / "VERSION").read_text().strip()


def test_saloes_e_turnos_publicos_na_ordem_da_config(api):
    st, r = api.get("/api/saloes", token=None)
    assert st == 200 and [s["id"] for s in r["saloes"]] == ["interno", "varanda"]
    st, r = api.get("/api/turnos", token=None)
    assert st == 200 and [t["id"] for t in r["turnos"]] == ["almoco", "jantar"]
    assert r["turnos"][1]["fim"] == "23:00" and r["turnos"][1]["ativo"] is True
    assert r["turnos"][0]["dias"] == ["ter", "qua", "qui", "sex", "sab", "dom"]


def test_rotas_da_equipe_exigem_token(api):
    for metodo, rota in [("GET", "/api/saida"), ("GET", "/api/reservas?data=2026-10-07"),
                         ("POST", "/api/clientes"), ("GET", "/api/atendimento-humano"),
                         ("GET", "/api/raiox?mes=2026-10"), ("POST", "/api/campanhas"),
                         ("GET", "/api/ocupacao?data=2026-10-07"), ("GET", "/api/mesas"),
                         ("POST", "/api/reservas"), ("GET", "/api/espera?data=2026-10-07")]:
        corpo = {} if metodo == "POST" else None
        assert api.req(metodo, rota, corpo, token=None)[0] == 401, rota
        assert api.req(metodo, rota, corpo, token="errado")[0] == 401, rota


def test_rotas_publicas_sem_token(api):
    assert api.get("/api/horarios?data=2026-10-07&pessoas=2", token=None)[0] == 200
    assert api.post("/api/mensagens", {"telefone": "41911112222", "texto": "oi"}, token=None)[0] == 200
    assert api.get("/api/turnos", token=None)[0] == 200


def test_paginas(api):
    st, html = api.get("/", token=None)
    assert st == 200 and 'id="chat"' in html
    st, html = api.get("/equipe", token=None)
    assert st == 200
    for el in ('id="reservas"', 'id="ocupacao"', 'id="fila-humano"', 'id="espera"', 'id="mesas"'):
        assert el in html, el


def test_estado_persiste_ao_reiniciar(dados):
    s = Servidor(dados)
    api = s.subir()
    cid = api.cliente()
    st, r = api.reserva(cid, "2026-10-07T12:00", 2, mesa="m1")
    assert st == 201, r
    s.parar()
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        lista = api2.reservas("2026-10-07")
        assert [x["id"] for x in lista] == [r["id"]] and lista[0]["mesas"] == ["m1"]
        assert api2.reserva(cid, "2026-10-07T12:00", 2, mesa="m1")[0] == 409
    finally:
        s2.parar()


def test_cria_restaurante_json_do_exemplo_se_faltar(tmp_path):
    d = tmp_path / "vazio"
    d.mkdir()
    s = Servidor(d)
    try:
        api = s.subir()
        assert api.get("/api/saude", token=None)[0] == 200
        assert (d / "restaurante.json").exists()
    finally:
        s.parar()
