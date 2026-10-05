# Validação adversarial do plano — 05/10/2026

Feita por um agente que **não viu** o planejamento, contra o briefing de validação (10 itens). Resultado: **3 problemas que bloqueariam a execução, 10 que atrapalhariam, 0 cosméticos — todos corrigidos**; 93 testes (contagem inalterada); checks 6, 7 e 10 reexecutados num clone temporário com saída abaixo. Cada correção tem uma linha em `FALHAS.md`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Teste × especificação, item a item | **Corrigido.** 1 contradição real (mesas/salão inexistente: §14 e teste diziam 422, regra geral da §5 manda 404 → unificado em 404) e 10 pontos em que o teste exigia algo que a spec não escrevia (401 antes de 422/404; ordem da lista "minha reserva"; "última mensagem de saída" = caixa de saída; `pessoas` da própria reserva fora do limite da cozinha no remarcar; sobreposição semiaberta de turnos; `.env.exemplo` sem a palavra `http`; `Content-Type: application/json`; `GET .../dados` 200 após `DELETE`; data do `chegou` = `inicio`; cliente conhecido não ouve `nome`). Todos agora estão na spec, sem mudar o que os testes exigem. |
| 2 | Valores esperados recalculados (python3) | **OK** — todas as contas batem (lista abaixo). |
| 3 | Contradições internas / estado entre testes / fixture | **OK.** Cada teste usa `tmp_path` próprio; nenhum depende de outro. Fixture comporta todos os cenários (ex.: 7–8 pessoas só por `m3m4`, 9 não cabe; domingo só almoço; segunda fechada; 15/10 feriado). Soma do `test_menor_mesa` = 15 ≤ 20 e do `test_limite` = 18 → 22/20/21, como os testes esperam. |
| 4 | Burlável? | **OK.** `verificar-independente.py` usa restaurante nunca visto (passo 15, 1 turno, combinação de 3 mesas, sem limite de cozinha, outra duração, outro relógio), argumentos todos explícitos (`api.req`, nenhum atalho do conftest), grep de 9 valores da fixture no código e `docker build` + healthcheck real. Rota que ignora entrada cai na grade de 15 min (13 e 9 horários) e na combinação a+b+c. |
| 5 | Raio-X | **OK.** `clientes_novos_mes` e `retorno_atual_pct` existem em `setores/restaurante.js` (vazamento `retencao`). Formato `{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}` é o do `app/painel-motor.js` (linhas 5–6 e `deDiagnostico`); `linhaDoTempo` ordena por `mes`, então inserir/substituir o mês funciona. |
| 6 | Travas (`loop.env`, `goal.md`, prompts, `congelar.sh`, `verificar-limites.sh`) | **OK.** `CODEX_ARGS="-c sandbox_workspace_write.network_access=true"`; `PERMITIDOS="."`; `PROTEGIDOS` = `tests/ pytest.ini docs/` + goal, hash, congelar, verificar-*, loop.env, prompt.md; goal = 93 = coletados; prompts proíbem API real e os protegidos. Clone: `congelar.sh` OK; stub honesto → `LIMITES OK`; `https://api.telegram.org` → violação; teste alterado (working tree e commitado) → hash; `0.0.0.0`, arquivo fora do escopo e `import requests` → violação. Saída abaixo. |
| 7 | Harness | **OK.** 93 coletados sem erro; sem implementação `14 failed, 79 errors`, **0 passed**; stub que imprime `PORTA=<n>` e responde `/api/saude` → `test_saude_traz_versao_do_arquivo` **1 passed** e processo encerrado; `Externo` grava pedidos, header `apikey`, `message_id`, e injeta 500 (`falhas=1` → 1º 500, 2º 201). |
| 8 | Tamanho e fechamento | **OK.** Mesmo porte do atende-clinica (93 testes, fechou em 7 de 20 ciclos). "Fora do v1" (§12) explícito. Nenhum teste usa rede real, Docker real (`test_docker` é estático; o build fica no nível 4 humano) nem relógio real (`RESERVA_AGORA` fixo; `tarefas/rodar {agora}`); únicas esperas são `esperar()` ≤ 5 s em servidor local e um `sleep(0.8)` no teste de duplicatas da Evolution. |
| 9 | README "Como rodar no seu ambiente" | **OK.** Pré-requisitos, congelar, loop headless / `/goal` Claude / `/goal` Codex, acompanhar, verificação final. Caminhos citados existem (`~/projetos/execucao-longa/tools/loop-longrun.sh`, `prompt-goal-*.md`, `verificar-*.{sh,py}`). Acrescentada a linha de `docs/VALIDACAO.md` na estrutura. |
| 10 | Vazamento de processo | **Corrigido.** 5 testes (e o helper `montar_mes`) subiam `Servidor` fora de `try/finally`. `conftest.py` ganhou `SERVIDORES` + fixture `autouse` que para todos no teardown. Prova com teste que falha de propósito: conftest novo → `pgrep` vazio; conftest antigo → órfão (PID encerrado por mim). |

## Contas conferidas (python3, independentes dos testes)

- **Dias da semana:** 05/10 seg · 06/10 ter (agora) · 07/10 qua · 08/10 qui · 09/10 sex · 10/10 sab · 11/10 dom · 12/10 seg · 13/10 ter · 15/10 qui (feriado) · 16/10 sex · 20/10 ter · 05/11 qui · 06/11 sex · 01/09 ter · 08/09 ter · 01/12 ter · 08/12 ter; verificador: 16/11 seg · 20/11 sex (feriado) · 21/11 sab · 26/11 qui · 27/11 sex.
- **Somas:** 06/10 + 30 = 05/11 (janela inclusiva) · 07/10 + 60 = 06/12 · 08/12 + 60 = 06/02/2027 · 16/11 + 30 = 16/12 · 16/11 + 10 = 26/11 · 08/09 → 10/10 = 32 dias (≤ 60) · 07/10 → 20/10 = 13 dias.
- **Confirmação (agora 06/10 10:00):** 06/10 19:00 = 9 h (pede) · 07/10 12:00 = 26 h (não) · às 12:30 passa a 23,5 h (pede).
- **Grades (passo 30):** 2 pessoas/90 min → almoço 11:30–13:30 (5) + jantar 19:00–21:30 (6) = 11 · 4/120 → 4 + 5 = 9 · 7/180 → 11:30, 12:00 + 19:00, 19:30, 20:00 = 5 · ocupação: 7 instantes no almoço + 8 no jantar = 15 · `seg_almoco` 11:30–14:00 → 11:30, 12:00, 12:30 · `tarde` 15:00–17:00 → 15:00, 15:30.
- **Verificador (passo 15):** 18:00–22:00 com 60 min → 13 horários (18:00 … 21:00); 120 min → 9 (… 20:00).
- **Raio-X out/2026:** sem o feriado, ter 4 + qua 4 + qui 4 + sex 5 + sab 5 = 22 dias × 450 min + dom 4 × 210 = 10.740 min/mesa × 7 mesas = **75.180**; reservados 90+90+120+90+2×180+90 = **840**; ocupação 1,1173 % → `round(…, 1)` = **1,1** (tolerância 0,06 do teste cobre); `no_show_pct` 1/(4+1) = **20,0**; `retorno_atual_pct` 1/2 = **50,0**; setembro: 1 cliente novo, voltou em 32 dias → 100,0.
- **Limite da cozinha:** 6+4+4+4 = 18 → +4 = 22 (409) → +2 = 20 (ok) → +1 = 21 (409). **Menor mesa:** 1+1+1+1+3+3+5 = 15 ≤ 20.

## O que fica para o dono decidir (não alterei)

- **`hash-congelado.txt` está dentro do escopo permitido** (`$D/`). No loop headless o `PROTEGIDOS` reverte qualquer edição; no `/goal` interativo só o prompt o protege — um agente que reescrevesse `HASH`/`BASE` junto com um teste passaria no `verificar-limites.sh`. Mesmo desenho do atende-clinica (que passou). Mitigação possível, se quiser: o `verificar-limites.sh` conferir que `BASE` é o commit cuja mensagem começa com `longrun reservas-v1: contrato congelado`, ou o humano olhar `git log` antes do `INDEPENDENTE OK`.
- `com_config()` no conftest não é usado por nenhum teste (ferramenta para testes futuros; inofensivo).
- `test_whatsapp_ignora_o_que_nao_e_do_cliente` usa `time.sleep(0.8)` em vez de `esperar()`: só ficaria instável numa máquina muito carregada.
- As perguntas de `docs/DECISOES-ABERTAS.md` continuam abertas (restaurante real, produto × curso, mapa gráfico, política de sinal, visual da `/equipe`).

## Saída dos checks (clone temporário, 05/10/2026)

```
$ python3 -m pytest -q --collect-only | tail -1
93 tests collected in 0.03s
$ python3 -m pytest -q | tail -1            # sem implementação
14 failed, 79 errors in 8.67s               # 0 passed

$ bash longrun/2026-10-05-reservas-v1/congelar.sh
congelado: HASH=54978bc62a246c62 TESTES=93

=== 7a: stub do CLI (PORTA=<n> + /api/saude) → teste de saúde ===
1 passed in 0.07s
=== 7b: Externo falso ===
1º sendText (falhas=1) → HTTP 500 | 2º → 201 | sendMessage → 200
whats() só ok: ['oi de novo'] | whats(ok=False): 2 | telegram(): ['#1 aviso'] | header apikey gravado: chave-evo
EXTERNO OK
=== item 10: teste temporário que falha antes do parar() (conftest NOVO) ===
1 failed in 0.07s
$ pgrep -af "[r]eserva serve"               → vazio
=== item 10 contraprova: conftest ANTIGO ===
1 failed in 0.05s
$ pgrep -af "[r]eserva serve"
3644340 python3 .../clone-reserva/reserva serve --porta 0 --dados /tmp/pytest-of-.../dados   ← órfão; encerrado por PID

=== 6a: sem implementação ===
LIMITE VIOLADO: não há implementação (reserva/src/web)
=== 6b: stub honesto (EVOLUTION_API_KEY, apikey, @s.whatsapp.net, http://127.0.0.1:8080, CLI, Dockerfile, compose, .env.exemplo) ===
LIMITES OK (hash 54978bc62a246c62, 93 testes, escopo ok, sem API/rede)
=== 6c: + https://api.telegram.org no código ===
LIMITE VIOLADO: chave/credencial ou API externa no código
=== 6d: teste alterado no working tree ===
LIMITE VIOLADO: hash do contrato mudou (1d4e3f011dfb3b2e ≠ 54978bc62a246c62)
=== 6e: teste alterado e commitado ===
LIMITE VIOLADO: hash do contrato mudou (1d4e3f011dfb3b2e ≠ 54978bc62a246c62)
=== 6g: bind 0.0.0.0 no código ===        LIMITE VIOLADO: bind em 0.0.0.0
=== 6h: docs/novo.md fora do escopo ===    LIMITE VIOLADO: arquivos fora do escopo: docs/novo.md
=== 6i: import requests ===                LIMITE VIOLADO: dependência externa ou SDK de API
=== 6f: de volta ao stub honesto ===
LIMITES OK (hash 54978bc62a246c62, 93 testes, escopo ok, sem API/rede)
```

Clone, stubs e teste temporário apagados; `git status` da árvore real limpo; nenhum processo meu vivo (o `atende serve` de outra sessão não foi tocado).
