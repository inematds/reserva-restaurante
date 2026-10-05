"""Seções 17 e 18: WhatsApp pela Evolution API e equipe pelo Telegram (contra servidor falso local)."""
import json
import time
import urllib.error
import urllib.request

from conftest import CHAT_EQUIPE, SEGREDO_TG, SEGREDO_WH, esperar, norm

TEL = "41988887777"
NUM = "5541988887777"
ESTAC = "Temos estacionamento próprio na lateral, grátis para clientes."

_ids = iter(range(1, 10 ** 6))


def evo(api, texto=None, numero=NUM, msg_id=None, from_me=False, sufixo="@s.whatsapp.net",
        evento="messages.upsert", message=None):
    if message is None:
        message = {"conversation": texto}
    corpo = {"event": evento, "instance": "restaurante",
             "data": {"key": {"remoteJid": numero + sufixo, "fromMe": from_me, "id": msg_id or f"M{next(_ids)}"},
                      "pushName": "Cliente", "message": message, "messageType": "conversation"}}
    st, _ = api.post(f"/webhook/evolution/{SEGREDO_WH}", corpo, token=None)
    assert st == 200
    return corpo


def tg(api, texto, reply_to=None, chat=CHAT_EQUIPE, segredo=SEGREDO_TG):
    """Entrega um update do Telegram no webhook; devolve o status HTTP."""
    msg = {"message_id": next(_ids), "chat": {"id": chat}, "from": {"id": 7, "first_name": "Rita"}, "text": texto}
    if reply_to:
        msg["reply_to_message"] = {"message_id": reply_to}
    q = urllib.request.Request(api.base + "/webhook/telegram", method="POST",
                               data=json.dumps({"update_id": next(_ids), "message": msg}).encode(),
                               headers={"Content-Type": "application/json", "X-Telegram-Bot-Api-Secret-Token": segredo})
    try:
        with urllib.request.urlopen(q, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def textos_whats(externo):
    return [p["json"]["text"] for p in externo.whats()]


def textos_tg(externo):
    return [p["json"]["text"] for p in externo.telegram()]


def abre_atendimento(api, externo):
    api.msg(TEL, "quero falar com um atendente")
    assert esperar(lambda: len(externo.telegram()) >= 1)
    [at] = api.get("/api/atendimento-humano")[1]["fila"]
    abertura = next(p for p in externo.telegram() if f"#{at['id']}" in p["json"]["text"])
    return at, abertura


# --- WhatsApp (Evolution) ---------------------------------------------------------------

def test_webhook_evolution_segredo_errado(api_int):
    assert api_int.post("/webhook/evolution/errado", {"event": "messages.upsert"}, token=None)[0] == 404


def test_whatsapp_responde_pela_evolution(api_int, externo):
    evo(api_int, "tem estacionamento?")
    assert esperar(lambda: len(externo.whats()) == 1)
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and p["json"]["text"] == ESTAC
    assert p["headers"].get("apikey") == "chave-evo"


def test_whatsapp_ignora_o_que_nao_e_do_cliente(api_int, externo):
    evo(api_int, "tem estacionamento?", msg_id="DUP1")
    evo(api_int, "tem estacionamento?", msg_id="DUP1")            # reenvio da Evolution
    evo(api_int, "tem estacionamento?", from_me=True)              # mensagem do próprio restaurante
    evo(api_int, "tem estacionamento?", numero="1203630", sufixo="@g.us")  # grupo
    evo(api_int, "tem estacionamento?", evento="connection.update")
    time.sleep(0.8)
    assert textos_whats(externo) == [ESTAC]


def test_whatsapp_sem_texto(api_int, externo):
    evo(api_int, message={"audioMessage": {"seconds": 5}})
    assert esperar(lambda: textos_whats(externo) == ["Por enquanto só consigo ler mensagens de texto."])


def test_whatsapp_reserva_e_avisa_equipe(api_int, externo):
    def tem(trecho):
        return esperar(lambda: any(trecho in norm(t) for t in textos_whats(externo)))

    evo(api_int, "quero reservar uma mesa")
    assert tem("nome")
    evo(api_int, "João Souza")
    assert tem("pessoas")
    evo(api_int, "2")
    assert tem("dia")
    evo(api_int, "amanhã")
    assert tem("2) 12:00 (almoco)")
    evo(api_int, "2")
    assert tem("reservad")
    [a] = api_int.reservas("2026-10-07")
    assert (a["telefone"], a["mesas"], a["inicio"], a["status"]) == ("+" + NUM, ["m1"], "2026-10-07T12:00", "reservada")
    assert api_int.get(f"/api/clientes/{a['cliente_id']}/dados")[1]["cliente"]["origem"] == "whatsapp"
    assert esperar(lambda: "Nova reserva: 07/10 12:00 João Souza — 2 pessoas" in textos_tg(externo))
    assert all(p["json"]["chat_id"] in (CHAT_EQUIPE, str(CHAT_EQUIPE)) for p in externo.telegram())


def test_saida_pela_evolution_com_reenvio(api_int, externo):
    cid = api_int.cliente("Maria", TEL)
    api_int.reserva(cid, "2026-10-06T19:00", 2)
    externo.falhas = 1
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 1
    [m] = api_int.saida("confirmacao")
    assert m["status"] == "pendente"
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 0 and r["reenviadas"] == 1
    assert api_int.saida("confirmacao")[0]["status"] == "enviado"
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and "06/10" in p["json"]["text"]


def test_sem_evolution_status_simulado(api):
    cid = api.cliente("Maria", TEL)
    api.reserva(cid, "2026-10-06T19:00", 2)
    api.post("/api/tarefas/rodar", {})
    assert api.saida("confirmacao")[0]["status"] == "simulado"


# --- Telegram (equipe) ------------------------------------------------------------------

def test_abertura_vai_ao_grupo(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    t = abertura["json"]["text"]
    assert TEL in t.replace(" ", "").replace("-", "") and f"#{at['id']}" in t
    assert str(abertura["json"]["chat_id"]) == str(CHAT_EQUIPE)
    assert at["status"] == "aberto"


def test_atendimento_aberto_silencia_bot_e_repassa(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    st, r = api_int.post("/api/mensagens", {"telefone": TEL, "texto": "tem estacionamento?"}, token=None)
    assert r["respostas"] == []
    assert esperar(lambda: any(p["json"].get("reply_to_message_id") == abertura["message_id"]
                               and "tem estacionamento" in p["json"]["text"] for p in externo.telegram()))


def test_equipe_responde_em_cima_da_mensagem(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "Olá, aqui é a Rita. Como posso ajudar?", reply_to=abertura["message_id"]) == 200
    assert esperar(lambda: any(m["texto"] == "Olá, aqui é a Rita. Como posso ajudar?" for m in api_int.saida("humano")))
    assert api_int.saida("humano")[0]["telefone"] == "+" + NUM
    assert esperar(lambda: "Olá, aqui é a Rita. Como posso ajudar?" in textos_whats(externo))


def test_webhook_telegram_protegido(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "invasor", reply_to=abertura["message_id"], segredo="errado") == 401
    assert tg(api_int, "outro grupo", reply_to=abertura["message_id"], chat=-1009999) == 200
    time.sleep(0.5)
    assert api_int.saida("humano") == []


def test_comandos_responder_encerrar_fila(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    tg(api_int, f"/responder {at['id']} Já te ligo")
    assert esperar(lambda: [m["texto"] for m in api_int.saida("humano")] == ["Já te ligo"])
    n = len(externo.telegram())
    tg(api_int, "/fila")
    assert esperar(lambda: any(f"#{at['id']}" in p["json"]["text"] for p in externo.telegram()[n:]))
    tg(api_int, f"/encerrar {at['id']}")
    assert esperar(lambda: api_int.get("/api/atendimento-humano")[1]["fila"] == [])
    assert api_int.msg(TEL, "tem estacionamento?") == ESTAC


def test_comando_reservas(api_int, externo):
    cid = api_int.cliente("Maria Lima", "41999990001")
    api_int.reserva(cid, "2026-10-07T12:00", 2)
    api_int.reserva(cid, "2026-10-07T19:00", 7)
    _, c = api_int.reserva(cid, "2026-10-07T13:00", 2)
    api_int.post(f"/api/reservas/{c['id']}/cancelar")
    tg(api_int, "/reservas 2026-10-07")

    def achou():
        return any("12:00 Maria Lima — 2 pessoas — m1 (reservada)" in t
                   and "19:00 Maria Lima — 7 pessoas — m3+m4 (reservada)" in t and "13:00" not in t
                   for t in textos_tg(externo))
    assert esperar(achou)


def test_grupo_grande_avisa_e_aprova_pelo_telegram(api_int, externo):
    cid = api_int.cliente("Maria", TEL)
    _, a = api_int.reserva(cid, "2026-10-07T12:00", 8)
    assert esperar(lambda: any(t.startswith(f"Grupo grande #{a['id']}:") and "07/10 12:00 Maria — 8 pessoas" in t
                               for t in textos_tg(externo)))
    assert not any(t.startswith("Nova reserva") for t in textos_tg(externo))
    tg(api_int, f"/aprovar {a['id']}")
    assert esperar(lambda: api_int.por_id("2026-10-07", a["id"])["status"] == "reservada")
    assert esperar(lambda: any("confirmad" in norm(t) and "07/10" in t for t in textos_whats(externo)))
    assert esperar(lambda: [m["status"] for m in api_int.saida("aprovacao")] == ["enviado"])


def test_recusa_pelo_telegram(api_int, externo):
    cid = api_int.cliente("Maria", TEL)
    _, a = api_int.reserva(cid, "2026-10-07T12:00", 8)
    tg(api_int, f"/recusar {a['id']}")
    assert esperar(lambda: api_int.por_id("2026-10-07", a["id"])["status"] == "recusada")
    assert esperar(lambda: any("nao foi possivel" in norm(t) for t in textos_whats(externo)))


def test_pagina_da_equipe_responde_e_encerra(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/responder", {"texto": "Pode vir às 20h"})[0] == 200
    assert [m["texto"] for m in api_int.saida("humano")] == ["Pode vir às 20h"]
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/encerrar")[0] == 200
    assert api_int.get("/api/atendimento-humano")[1]["fila"] == []


def test_cancelamento_pelo_chat_avisa_equipe(api_int, externo):
    cid = api_int.cliente("Maria", TEL)
    api_int.reserva(cid, "2026-10-06T19:00", 2)
    api_int.post("/api/tarefas/rodar", {})
    assert "cancelad" in norm(api_int.msg(TEL, "2"))
    assert esperar(lambda: any(t.startswith("Cancelada:") and "06/10 19:00" in t for t in textos_tg(externo)))
