#!/usr/bin/env python3
"""Verificação independente (nível 4) — rodar DEPOIS que o loop disser concluído. O agente não vê este arquivo no prompt.

1. Procura valores da fixture copiados no código (atalho para passar nos testes).
2. Sobe o sistema com um restaurante NUNCA visto (passo de 15 min, um turno só, combinação de 3 mesas,
   sem limite de cozinha, outra duração, outro relógio) e confere regras que só passam se a lógica for geral.
   Todos os argumentos explícitos: nenhum atalho do conftest com padrão da fixture.
3. docker build + healthcheck do container.
Saída: INDEPENDENTE OK, ou a lista do que falhou.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tests"))
from conftest import Servidor  # noqa: E402

falhas = []


def confere(cond, msg):
    if not cond:
        falhas.append(msg)


# 1. valores fixos da fixture no código
alvo = [p for p in ("reserva", "src", "web") if (RAIZ / p).exists()]
for trecho in ("Cantina Teste", "segredo-teste", "41999990001", "2026-10-06", "estacionamento próprio",
               "Maria Silva", "m3m4", '"almoco"', '"varanda"'):
    r = subprocess.run(["grep", "-rnF", trecho, *alvo], cwd=RAIZ, capture_output=True, text=True)
    confere(r.stdout == "", f"valor da fixture no código: {trecho!r}")

# 2. restaurante nunca visto
TOKEN = "outro-token-xyz"
cfg = {
    "nome": "Bistrô da Praça", "token": TOKEN, "passo_min": 15, "antecedencia_min_horas": 2,
    "janela_dias": 10, "confirmacao_horas": 12, "grupo_grande_a_partir": 10, "limite_pessoas_por_horario": None,
    "reativacao_dias": 30, "feriados": ["2026-11-20"],
    "duracao": [{"ate": 4, "min": 60}, {"ate": None, "min": 120}],
    "saloes": [{"id": "unico", "nome": "Salão"}],
    "combinacoes": [{"id": "abc", "mesas": ["a", "b", "c"], "min": 5, "max": 8}],
    "turnos": [{"id": "noite", "nome": "Noite", "dias": ["seg", "ter", "qua", "qui", "sex"], "inicio": "18:00", "fim": "22:00"}],
    "mesas": [{"id": "a", "salao": "unico", "min": 1, "max": 2}, {"id": "b", "salao": "unico", "min": 1, "max": 2},
              {"id": "c", "salao": "unico", "min": 3, "max": 4}],
    "faq": [{"id": "cartao", "perguntas": ["aceitam cartão de crédito"], "resposta": "Sim, débito e crédito."}],
}
with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / "restaurante.json").write_text(json.dumps(cfg, ensure_ascii=False))
    s = Servidor(d, agora="2026-11-16T15:00")  # segunda; agora + 2 h = 17:00, antes do turno
    try:
        api = s.subir()

        def req(metodo, rota, corpo=None, token=TOKEN):
            return api.req(metodo, rota, corpo, token=token)

        def horarios(data, pessoas):
            st, r = req("GET", f"/api/horarios?data={data}&pessoas={pessoas}", token=None)
            return [x["inicio"][11:] for x in r.get("horarios", [])] if st == 200 else [f"HTTP {st}"]

        h = horarios("2026-11-16", 2)   # 60 min, passo 15: 18:00..21:00 = 13
        confere(h[:2] == ["18:00", "18:15"] and h[-1] == "21:00" and len(h) == 13, f"grade de 15 min errada: {h}")
        h5 = horarios("2026-11-16", 5)  # só a combinação a+b+c (min 5), 120 min: 18:00..20:00 = 9
        confere(h5[:1] == ["18:00"] and h5[-1] == "20:00" and len(h5) == 9, f"combinação de 3 mesas errada: {h5}")
        confere(horarios("2026-11-20", 2) == [], "feriado novo ignorado")
        confere(horarios("2026-11-21", 2) == [], "sábado sem turno listou horário")
        confere(len(horarios("2026-11-26", 2)) == 13 and horarios("2026-11-27", 2) == [], "janela de 10 dias errada (16/11 + 10 = 26/11)")
        confere(req("GET", "/api/saida", token="segredo-teste")[0] == 401, "token da fixture aceito")

        st, c = req("POST", "/api/clientes", {"nome": "Teste Nome", "telefone": "11987654321",
                                              "consentimento_marketing": True, "origem": "site"})
        confere(st == 201, f"cliente → {st} {c}")
        cid = c.get("id")

        def reserva(inicio, pessoas, **extra):
            return req("POST", "/api/reservas", {"cliente_id": cid, "inicio": inicio, "pessoas": pessoas, **extra})

        st, r1 = reserva("2026-11-16T18:00", 2)
        confere(st == 201 and r1.get("mesas") == ["a"] and r1.get("status") == "reservada", f"1ª reserva: {st} {r1}")
        st, r2 = reserva("2026-11-16T18:00", 2)
        confere(st == 201 and r2.get("mesas") == ["b"], f"2ª reserva (ordem do cadastro): {st} {r2}")
        st, r3 = reserva("2026-11-16T18:00", 2)
        confere(st == 409 and r3.get("erro") == "sem_mesa", f"mesa c (min 3) aceitou 2 pessoas: {st} {r3}")
        st, r4 = reserva("2026-11-16T18:00", 3)
        confere(st == 201 and r4.get("mesas") == ["c"], f"3 pessoas → c: {st} {r4}")
        st, r5 = reserva("2026-11-16T18:30", 5)
        confere(st == 409, f"combinação com mesa ocupada aceita: {st} {r5}")
        st, r6 = reserva("2026-11-16T20:00", 5)
        confere(st == 201 and r6.get("mesas") == ["a", "b", "c"] and r6.get("fim") == "2026-11-16T22:00"
                and r6.get("status") == "reservada", f"combinação de 3 mesas: {st} {r6}")
        st, r7 = req("POST", f"/api/reservas/{r1.get('id')}/remarcar", {"inicio": "2026-11-16T18:15"})
        confere(st == 200 and r7.get("mesas") == ["a"], f"remarcar com a própria mesa: {st} {r7}")
        st, r8 = reserva("2026-11-16T18:00", 1, mesa="a")
        confere(st == 409, f"mesa a deveria estar ocupada 18:15–19:15: {st} {r8}")

        st, m = req("POST", "/api/mensagens", {"telefone": "11987654321", "texto": "vocês aceitam cartão de crédito?"}, token=None)
        confere(st == 200 and m.get("respostas") == ["Sim, débito e crédito."], f"FAQ novo não respondido: {m}")

        st, ch = req("POST", f"/api/reservas/{r1.get('id')}/chegada", {"compareceu": True})
        confere(st == 200 and ch.get("status") == "chegou", f"chegada: {st} {ch}")
        # reativação: 16/11 + 30 dias = 16/12
        st, t = req("POST", "/api/tarefas/rodar", {"agora": "2026-12-15T10:00"})
        confere(t.get("enviadas") == 0, f"reativação cedo demais: {t}")
        st, t = req("POST", "/api/tarefas/rodar", {"agora": "2026-12-16T10:00"})
        confere(t.get("enviadas") == 1, f"reativação não enviada: {t}")
        st, rx = req("GET", "/api/raiox?mes=2026-11")
        v = rx.get("valores", {})
        confere(rx.get("pacote") == "restaurante" and v.get("clientes_novos_mes") == 1 and v.get("reservas_atendidas_mes") == 1,
                f"raiox: {rx}")
    finally:
        s.parar()

# 3. container de verdade (precisa de docker; baixa a imagem python na 1ª vez)
b = subprocess.run(["docker", "build", "-q", "-t", "reserva-restaurante-verif", "."], cwd=RAIZ, capture_output=True, text=True)
confere(b.returncode == 0, f"docker build falhou: {b.stderr[-300:]}")
if b.returncode == 0:
    c = subprocess.run(["docker", "run", "-d", "--rm", "-p", "127.0.0.1::8080", "reserva-restaurante-verif"],
                       capture_output=True, text=True)
    cid = c.stdout.strip()
    try:
        porta = subprocess.run(["docker", "port", cid, "8080"], capture_output=True, text=True).stdout.split(":")[-1].strip()
        ok = False
        for _ in range(40):
            try:
                ok = urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/saude", timeout=2).status == 200
                break
            except Exception:
                time.sleep(0.5)
        confere(ok, "container não respondeu /api/saude")
    finally:
        subprocess.run(["docker", "stop", cid], capture_output=True)

if falhas:
    print("INDEPENDENTE FALHOU:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
print("INDEPENDENTE OK")
