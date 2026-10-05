"""Seção 9: grupo grande (aprovar/recusar), base própria (origem, aniversário, reativação), campanhas, cadastro de clientes."""
from conftest import Servidor, norm

T1, T2, T3 = "41999990001", "41999990002", "41999990003"


def rodar(api, agora=None):
    st, r = api.post("/api/tarefas/rodar", {"agora": agora} if agora else {})
    assert st == 200, (st, r)
    return r["enviadas"]


def test_grupo_grande_pendente_ocupa_e_aprovar(api):
    p = api.cliente("Maria", T1)
    st, a = api.reserva(p, "2026-10-07T12:00", 8)
    assert st == 201 and a["status"] == "pendente" and a["mesas"] == ["m3", "m4"]
    assert api.reserva(p, "2026-10-07T12:00", 7)[0] == 409                      # pendente ocupa
    assert api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": True})[0] == 409
    st, r = api.post(f"/api/reservas/{a['id']}/aprovar")
    assert st == 200 and r["status"] == "reservada"
    [m] = api.saida("aprovacao")
    t = norm(m["texto"])
    assert m["reserva_id"] == a["id"] and "confirmad" in t and "07/10" in t and "12:00" in t
    assert api.post(f"/api/reservas/{a['id']}/aprovar")[0] == 409
    assert api.por_id("2026-10-07", a["id"])["status"] == "reservada"


def test_grupo_grande_recusar_libera_sem_disparar_espera(api):
    p = api.cliente("Maria", T1)
    p2 = api.cliente("José", T2)
    _, a = api.reserva(p, "2026-10-07T12:00", 8)
    api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-07", "turno": "almoco", "pessoas": 7})
    st, r = api.post(f"/api/reservas/{a['id']}/recusar")
    assert st == 200 and r["status"] == "recusada"
    [m] = api.saida("recusa")
    assert "nao foi possivel" in norm(m["texto"]) and m["telefone"] == "+5541999990001"
    assert api.saida("espera") == []
    assert api.reserva(p2, "2026-10-07T12:00", 7)[0] == 201
    assert api.post(f"/api/reservas/{a['id']}/recusar")[0] == 409


def test_origem_de_marketplace_nao_entra_na_base(api):
    for origem in ("ifood", "marketplace", "rappi", "99food", "keeta"):
        st, r = api.post("/api/clientes", {"nome": "X", "telefone": T1, "origem": origem})
        assert (st, r["erro"]) == (422, "origem_invalida"), origem
    assert api.get("/api/clientes")[1]["clientes"] == []
    st, r = api.post("/api/clientes", {"nome": "Maria", "telefone": T1, "origem": "salao"})
    assert st == 201
    st, r = api.post("/api/clientes", {"nome": "José", "telefone": T2})
    assert st == 201
    origens = {c["telefone"]: c["origem"] for c in api.get("/api/clientes")[1]["clientes"]}
    assert origens == {"+5541999990001": "salao", "+5541999990002": "equipe"}
    assert api.put(f"/api/clientes/{r['id']}", {"origem": "ifood"})[0] == 422
    assert api.put(f"/api/clientes/{r['id']}", {"origem": "indicacao"})[1]["origem"] == "indicacao"


def test_aniversario_so_com_consentimento_uma_vez_por_ano(api):
    api.cliente("Maria Lima", T1, marketing=True, aniversario="10-07")
    api.cliente("José", T2, marketing=False, aniversario="10-07")
    assert api.post("/api/clientes", {"nome": "Z", "telefone": T3, "aniversario": "2026-10-07"})[0] == 400
    assert api.post("/api/clientes", {"nome": "Z", "telefone": T3, "aniversario": "7/10"})[0] == 400
    assert rodar(api) == 0                                     # 06/10
    assert rodar(api, "2026-10-07T09:00") == 1
    [m] = api.saida("aniversario")
    assert m["telefone"] == "+5541999990001" and "Maria" in m["texto"]
    assert rodar(api, "2026-10-07T18:00") == 0
    assert rodar(api, "2027-10-07T09:00") == 1


def test_reativacao_apos_60_dias_uma_por_visita(dados):
    s = Servidor(dados)
    api = s.subir()
    p1 = api.cliente("Maria", T1, marketing=True)
    p2 = api.cliente("José", T2, marketing=False)
    for p in (p1, p2):
        _, a = api.reserva(p, "2026-10-07T12:00", 2)
        api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": True})
    # última visita 07/10 + 60 dias = 06/12
    assert rodar(api, "2026-12-05T10:00") == 0
    assert rodar(api, "2026-12-06T10:00") == 1
    [m] = api.saida("reativacao")
    assert m["telefone"] == "+5541999990001" and "Cantina Teste" in m["texto"]
    assert rodar(api, "2026-12-07T10:00") == 0
    assert rodar(api, "2027-03-01T10:00") == 0                 # não repete sem nova visita
    s.parar()
    s2 = Servidor(dados, agora="2026-12-01T10:00")             # terça
    try:
        api2 = s2.subir()
        _, b = api2.reserva(p1, "2026-12-08T12:00", 2)
        api2.post(f"/api/reservas/{b['id']}/chegada", {"compareceu": True})
        assert api2.get(f"/api/clientes/{p1}/dados")[1]["cliente"]["ultima_visita"] == "2026-12-08"
        # 08/12 + 60 dias = 06/02/2027
        assert rodar(api2, "2027-02-05T10:00") == 0
        assert rodar(api2, "2027-02-06T10:00") == 1
    finally:
        s2.parar()


def test_campanha_so_com_consentimento_e_sem_parar(api):
    api.cliente("Com", T1, marketing=True)
    api.cliente("Sem", T2, marketing=False)
    api.cliente("Parou", T3, marketing=True)
    api.msg(T3, "parar")
    assert api.post("/api/campanhas", {"texto": "   "})[0] == 422
    st, r = api.post("/api/campanhas", {"texto": "Hoje tem feijoada no clube do bairro."})
    assert st == 200 and r["enviadas"] == 1
    [m] = api.saida("campanha")
    assert m["telefone"] == "+5541999990001" and m["texto"] == "Hoje tem feijoada no clube do bairro."


def test_clientes_busca_e_edicao(api):
    p1 = api.cliente("José Antônio Souza", T1)
    p2 = api.cliente("Maria Lima", T2)
    st, r = api.get("/api/clientes?busca=antonio")
    assert st == 200 and [c["id"] for c in r["clientes"]] == [p1]
    assert [c["id"] for c in api.get("/api/clientes?busca=990002")[1]["clientes"]] == [p2]
    assert [c["id"] for c in api.get("/api/clientes")[1]["clientes"]] == [p1, p2]
    st, r = api.put(f"/api/clientes/{p2}", {"aniversario": "05-02", "consentimento_marketing": True})
    assert st == 200 and r["aniversario"] == "05-02" and r["consentimento_marketing"] is True
    assert r["ultima_visita"] is None and r["visitas"] == 0
    assert api.put(f"/api/clientes/{p2}", {"telefone": T1})[0] == 409
    assert api.put(f"/api/clientes/{p2}", {"telefone": "12"})[0] == 400
    assert api.put(f"/api/clientes/{p2}", {"aniversario": "13-01"})[0] == 400
    assert api.put("/api/clientes/9999", {"nome": "Q"})[0] == 404
