"""Seção 6: conversa — FAQ, não entendi, humano, reserva pelo chat, consulta/cancelamento, lista de espera, parar.

Agora = ter 06/10/2026 10:00; "amanhã" = qua 07/10.
"""
from conftest import norm

TEL = "41988887777"
TEL_N = "+5541988887777"
ESTAC = "Temos estacionamento próprio na lateral, grátis para clientes."


def fila(api):
    st, r = api.get("/api/atendimento-humano")
    assert st == 200
    return r["fila"]


def test_faq_responde_exatamente(api):
    assert api.msg(TEL, "Oi, tem estacionamento aí?") == ESTAC
    assert api.msg(TEL, "posso levar meu cachorro?") == "Sim, pets são bem-vindos na varanda."
    assert api.msg(TEL, "vocês têm acesso para cadeirante?") == "Entrada com rampa e banheiro acessível no salão interno."


def test_nao_entendi_e_depois_passa_para_humano(api):
    r = norm(api.msg(TEL, "qual o preço do rodízio?"))
    assert "nao entendi" in r and "atendente" in r
    assert fila(api) == []
    api.msg(TEL, "e tem desconto pra grupo?")
    f = fila(api)
    assert len(f) == 1 and f[0]["telefone"] == TEL_N and f[0]["status"] == "aberto"


def test_pedido_de_atendente(api):
    assert "atendente" in norm(api.msg(TEL, "quero falar com um atendente"))
    assert len(fila(api)) == 1


def test_reserva_pelo_chat_cliente_novo(api):
    assert "nome" in norm(api.msg(TEL, "quero fazer uma reserva"))
    assert "pessoas" in norm(api.msg(TEL, "João Souza"))
    assert "dia" in norm(api.msg(TEL, "4"))
    r = api.msg(TEL, "amanhã")
    # 4 pessoas = 120 min: almoço 11:30, 12:00, 12:30, 13:00; jantar 19:00..21:00 → mostra 8
    for linha in ("1) 11:30 (Almoço)", "4) 13:00 (Almoço)", "5) 19:00 (Jantar)", "8) 20:30 (Jantar)"):
        assert linha in r, linha
    assert "21:00" not in r
    r = norm(api.msg(TEL, "5"))
    assert "reservad" in r and "07/10" in r and "19:00" in r and "4 pessoas" in r
    [a] = api.reservas("2026-10-07")
    assert (a["telefone"], a["pessoas"], a["mesas"], a["inicio"], a["status"]) == \
        (TEL_N, 4, ["m3"], "2026-10-07T19:00", "reservada")
    st, d = api.get(f"/api/clientes/{a['cliente_id']}/dados")
    assert d["cliente"]["nome"] == "João Souza" and d["cliente"]["origem"] == "chat"
    assert d["cliente"]["consentimento_marketing"] is False


def test_reserva_cliente_conhecido_hoje_e_opcao_invalida(api):
    api.cliente("Maria", TEL)
    r = norm(api.msg(TEL, "reservar"))
    assert "pessoas" in r and "nome" not in r
    assert "dia" in norm(api.msg(TEL, "2"))
    r = api.msg(TEL, "hoje")
    assert "1) 11:30 (Almoço)" in r
    r = api.msg(TEL, "9")
    assert "1) 11:30 (Almoço)" in r          # repete as opções
    r = norm(api.msg(TEL, "1"))
    assert "reservad" in r and "06/10" in r and "11:30" in r and "2 pessoas" in r
    [a] = api.reservas("2026-10-06")
    assert (a["mesas"], a["inicio"]) == (["m1"], "2026-10-06T11:30")


def test_dia_invalido_repete_a_pergunta(api):
    api.cliente("Maria", TEL)
    api.msg(TEL, "reservar")
    api.msg(TEL, "2")
    for dia in ("12/10", "15/10", "31/02", "06/11", "ontem"):   # segunda, feriado, inexistente, fora da janela, lixo
        r = norm(api.msg(TEL, dia))
        assert "nao" in r and "dia" in r, dia
        assert "1)" not in r
    assert "1) 11:30 (Almoço)" in api.msg(TEL, "07/10")
    assert api.reservas("2026-10-07") == []


def test_dia_lotado_entra_na_lista_de_espera_escolhendo_turno(api):
    cid = api.cliente("Ocupa", "41900000001")
    for inicio in ("2026-10-07T11:30", "2026-10-07T19:00"):   # 7 pessoas × 180 min bloqueiam m3+m4 nos dois turnos
        assert api.reserva(cid, inicio, 7)[0] == 201
    q = api.cliente("Quero", TEL)
    api.msg(TEL, "reservar")
    api.msg(TEL, "7")
    r = norm(api.msg(TEL, "07/10"))
    assert "lista de espera" in r and "1" in r and "2" in r
    r = api.msg(TEL, "1")
    assert "1) Almoço" in r and "2) Jantar" in r
    assert "lista de espera" in norm(api.msg(TEL, "2"))
    st, r = api.get("/api/espera?data=2026-10-07")
    [e] = r["espera"]
    assert (e["cliente_id"], e["turno"], e["pessoas"], e["status"]) == (q, "jantar", 7, "pendente")


def test_dia_lotado_com_um_turno_so_nao_pergunta_turno(api):
    cid = api.cliente("Ocupa", "41900000001")
    assert api.reserva(cid, "2026-10-11T11:30", 7)[0] == 201   # domingo: só almoço; 11:30–14:30 cobre o 12:00
    api.cliente("Quero", TEL)
    api.msg(TEL, "reservar")
    api.msg(TEL, "7")
    assert "lista de espera" in norm(api.msg(TEL, "11/10"))
    r = norm(api.msg(TEL, "1"))
    assert "lista de espera" in r and "1) almoco" not in r
    [e] = api.get("/api/espera?data=2026-10-11")[1]["espera"]
    assert (e["turno"], e["pessoas"]) == ("almoco", 7)
    # "2" na oferta sai sem criar pedido
    api.msg(TEL, "reservar")
    api.msg(TEL, "7")
    api.msg(TEL, "11/10")
    api.msg(TEL, "2")
    assert len(api.get("/api/espera?data=2026-10-11")[1]["espera"]) == 1
    assert api.msg(TEL, "tem estacionamento") == ESTAC


def test_cancelar_dentro_do_fluxo_sai_sem_cancelar_reserva(api):
    cid = api.cliente("Maria", TEL)
    _, a = api.reserva(cid, "2026-10-07T12:00", 2)
    api.msg(TEL, "reservar")
    assert "cancelad" in norm(api.msg(TEL, "cancelar"))
    assert api.por_id("2026-10-07", a["id"])["status"] == "reservada"
    assert api.msg(TEL, "tem estacionamento") == ESTAC


def test_minha_reserva_e_cancelar_pelo_chat(api):
    cid = api.cliente("Maria", TEL)
    _, a = api.reserva(cid, "2026-10-07T12:00", 2)
    _, b = api.reserva(cid, "2026-10-08T19:00", 2)
    r = api.msg(TEL, "quero ver minha reserva")
    assert "1) 07/10 12:00 — 2 pessoas" in r and "2) 08/10 19:00 — 2 pessoas" in r
    r = api.msg(TEL, "quero cancelar")
    assert "1) 07/10 12:00" in r and "2) 08/10 19:00" in r   # várias: lista e espera o número
    r = norm(api.msg(TEL, "2"))
    assert "cancelad" in r and "08/10" in r
    assert api.por_id("2026-10-08", b["id"])["status"] == "cancelada"
    assert api.por_id("2026-10-07", a["id"])["status"] == "reservada"
    r = norm(api.msg(TEL, "cancelar"))                       # uma só: cancela na hora
    assert "cancelad" in r and "07/10" in r
    assert api.por_id("2026-10-07", a["id"])["status"] == "cancelada"
    assert "nao encontrei" in norm(api.msg(TEL, "minha reserva"))


def test_parar_bloqueia_contato(api):
    cid = api.cliente("Maria", TEL, marketing=True)
    api.reserva(cid, "2026-10-06T19:00", 2)                  # dentro das 24 h de confirmação
    assert "nao vai mais receber" in norm(api.msg(TEL, "PARAR"))
    st, r = api.post("/api/tarefas/rodar", {})
    assert st == 200 and r["enviadas"] == 0
    assert api.saida() == []
    st, d = api.get(f"/api/clientes/{cid}/dados")
    assert d["cliente"]["nao_contatar"] is True


def test_grupo_grande_pelo_chat_fica_aguardando(api):
    api.cliente("Maria", TEL)
    api.msg(TEL, "reservar")
    api.msg(TEL, "8")
    r = api.msg(TEL, "07/10")
    assert "1) 11:30 (Almoço)" in r and "2) 12:00 (Almoço)" in r and "3) 19:00 (Jantar)" in r
    r = norm(api.msg(TEL, "1"))
    assert "aguardando" in r and "equipe" in r
    [a] = api.reservas("2026-10-07")
    assert (a["status"], a["mesas"], a["pessoas"]) == ("pendente", ["m3", "m4"], 8)
