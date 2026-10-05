"""Seções 10 e 11: direitos do titular (LGPD) e exportação para o Painel de Recuperação do Raio-X (pacote restaurante)."""
import json
import subprocess

from conftest import RAIZ, Servidor, norm

# Mesa-minutos disponíveis em out/2026: 7 mesas × [dias ter–sab com almoço (210) + jantar (240) = 450 min
# → ter 4 + qua 4 + qui 4 (5 menos o feriado 15/10) + sex 5 + sab 5 = 22 dias × 450 = 9.900;
# domingos: 4 × 210 = 840] = 7 × 10.740 = 75.180
DISPONIVEL_OUT = 75180


def test_dados_e_exclusao(api):
    tel = "41999990001"
    cid = api.cliente("Maria Silva", tel, marketing=True, aniversario="05-02")
    p2 = api.cliente("José", "41999990002")
    _, a = api.reserva(cid, "2026-10-07T12:00", 2)
    _, b = api.reserva(cid, "2026-10-08T12:00", 2)
    api.post(f"/api/reservas/{b['id']}/chegada", {"compareceu": True})
    api.post("/api/espera", {"cliente_id": p2, "data": "2026-10-07", "turno": "almoco", "pessoas": 2})
    api.msg(tel, "tem estacionamento")
    st, d = api.get(f"/api/clientes/{cid}/dados")
    assert st == 200
    assert d["cliente"]["nome"] == "Maria Silva" and d["cliente"]["telefone"] == "+5541999990001"
    assert d["cliente"]["aniversario"] == "05-02" and d["cliente"]["visitas"] == 1
    assert {x["id"] for x in d["reservas"]} == {a["id"], b["id"]}
    assert {"entrada", "saida"} <= {m["direcao"] for m in d["mensagens"]}
    assert any("estacionamento" in m["texto"] for m in d["mensagens"])

    assert api.delete(f"/api/clientes/{cid}")[0] == 204
    st, d = api.get(f"/api/clientes/{cid}/dados")
    assert d["cliente"]["nome"] == "removido" and d["cliente"]["telefone"] is None and d["cliente"]["aniversario"] is None
    assert {x["id"]: x["status"] for x in d["reservas"]} == {a["id"]: "cancelada", b["id"]: "chegou"}
    assert d["mensagens"] and all(m["texto"] == "" for m in d["mensagens"])
    assert [m["telefone"] for m in api.saida("espera")] == ["+5541999990002"]   # o cancelamento disparou a espera
    st, r = api.get("/api/raiox?mes=2026-10")
    assert r["valores"]["reservas_atendidas_mes"] == 1
    assert api.post("/api/campanhas", {"texto": "oi"})[1]["enviadas"] == 0
    assert "nome" in norm(api.msg(tel, "quero reservar"))   # telefone virou desconhecido


def montar_mes(dados):
    """Setembro: uma visita (coorte de set). Outubro: o cenário medido."""
    s = Servidor(dados, agora="2026-09-01T10:00")   # terça
    api = s.subir()
    p9 = api.cliente("Nove", "41900000009")
    st, a = api.reserva(p9, "2026-09-08T12:00", 2)   # terça 08/09
    assert st == 201, a
    api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": True})
    s.parar()

    s = Servidor(dados)  # agora = 06/10/2026 10:00
    api = s.subir()
    p1, p2, p3, p4, p5 = (api.cliente(n, f"4190000000{i}") for i, n in enumerate(["Um", "Dois", "Tres", "Quatro", "Cinco"], 1))

    def marca(cid, inicio, pessoas, compareceu=None):
        st, a = api.reserva(cid, inicio, pessoas)
        assert st == 201, (inicio, a)
        if compareceu is not None:
            api.post(f"/api/reservas/{a['id']}/chegada", {"compareceu": compareceu})
        return a

    marca(p1, "2026-10-07T12:00", 2, True)      # m1, 90 min; novo
    marca(p1, "2026-10-20T12:00", 2, True)      # m1, 90 min; volta em 13 dias
    marca(p2, "2026-10-07T12:00", 4, True)      # m3, 120 min; novo, não volta
    marca(p3, "2026-10-07T12:00", 2, False)     # m2, 90 min; no-show (ativa, não é cliente novo)
    marca(p4, "2026-10-08T19:00", 7)            # m3+m4, 2 × 180 min; reservada (ativa)
    c = marca(p5, "2026-10-08T12:00", 2)        # cancelada: não conta
    api.post(f"/api/reservas/{c['id']}/cancelar")
    marca(p9, "2026-10-10T12:00", 2, True)      # sáb; m1, 90 min; 2ª visita (32 dias após 08/09)
    return s, api


def test_raiox_numeros_do_mes(dados):
    s, api = montar_mes(dados)
    try:
        st, r = api.get("/api/raiox?mes=2026-10")
        assert st == 200 and r["pacote"] == "restaurante" and r["mes"] == "2026-10"
        v = r["valores"]
        assert v["reservas_atendidas_mes"] == 4          # p1 ×2, p2, p9
        assert v["no_show_pct"] == 20.0                  # 1 ÷ (4 + 1)
        assert v["clientes_novos_mes"] == 2              # p1, p2 (p9 é de setembro; p3 nunca chegou)
        assert v["retorno_atual_pct"] == 50.0            # p1 voltou em 13 dias; p2 não
        # reservados: 90 + 90 + 120 + 90 + 2×180 + 90 = 840 mesa-minutos
        assert abs(v["ocupacao_pct"] - 840 / DISPONIVEL_OUT * 100) <= 0.06
        st, setembro = api.get("/api/raiox?mes=2026-09")
        assert setembro["valores"]["reservas_atendidas_mes"] == 1 and setembro["valores"]["clientes_novos_mes"] == 1
        assert setembro["valores"]["retorno_atual_pct"] == 100.0 and setembro["valores"]["no_show_pct"] == 0
        st, vazio = api.get("/api/raiox?mes=2026-08")
        assert {k: vazio["valores"][k] for k in ("reservas_atendidas_mes", "clientes_novos_mes", "retorno_atual_pct", "no_show_pct")} == \
            {"reservas_atendidas_mes": 0, "clientes_novos_mes": 0, "retorno_atual_pct": 0, "no_show_pct": 0}
    finally:
        s.parar()


def test_cli_grava_mes_no_acompanhamento_do_painel(dados, tmp_path):
    s, _ = montar_mes(dados)
    s.parar()
    arq = tmp_path / "acompanhamento.json"
    arq.write_text(json.dumps({
        "tipo": "acompanhamento", "pacote": "restaurante", "cliente": "Cantina Teste",
        "base": {"data": "2026-09-01", "valores": {"retorno_atual_pct": 20, "ticket_medio": 50, "clientes_novos_mes": 400}},
        "meses": [],
    }))
    cmd = [str(RAIZ / "reserva"), "raiox", "--dados", str(dados), "--mes", "2026-10", "--acompanhamento", str(arq)]
    for _ in range(2):  # rodar duas vezes substitui o mês, não duplica
        assert subprocess.run(cmd, cwd=RAIZ, capture_output=True, timeout=30).returncode == 0
    acomp = json.loads(arq.read_text())
    assert acomp["tipo"] == "acompanhamento" and acomp["base"]["valores"]["retorno_atual_pct"] == 20
    [m] = acomp["meses"]
    assert m["mes"] == "2026-10" and m["obs"] == "reserva-restaurante"
    assert m["valores"]["ticket_medio"] == 50            # mesclado da base
    assert m["valores"]["retorno_atual_pct"] == 50.0     # medido
    assert m["valores"]["clientes_novos_mes"] == 2
