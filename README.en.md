# reserva-restaurante

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Restaurante](guia/assets/banner-en.jpg)](https://inematds.github.io/reserva-restaurante/guia/en/)

## 📖 User guide

Full guide (landing page + step by step): **https://inematds.github.io/reserva-restaurante/guia/en/**

Table booking for **a single restaurant**, with Python 3 and its standard library (planned): dining rooms and tables with capacity, shifts by weekday, automatic allocation of the smallest table that fits, automatic confirmation ("1 confirms / 2 cancels"), no-show, waitlist, large parties approved by the staff, FAQ, handoff to a human, an own customer base with consent (birthday, return invitation, campaigns), web chat + WhatsApp through the Evolution API, staff desk on Telegram and on the `/equipe` page, backup/restore, Docker and a monthly export to the Recovery Panel of Raio-X de Margem (package `restaurante`).

> The business rules built in (LGPD, Brazil's privacy law, and marketplace terms such as iFood's) are Brazilian.

**Status (05/10/2026): the plan only.** This repo holds the contract (`docs/ESPECIFICACAO.md`), 93 black-box acceptance tests (`tests/`), the decisions (`docs/DECISOES-ABERTAS.md`), the map to Raio-X (`docs/MAPA-RAIO-X.md`) and the long-run folder (`longrun/2026-10-05-reservas-v1/`). **There is no implementation** (`./reserva`, `src/`, `web/`, `Dockerfile`): an agent produces it, running against the tests in your own environment, as described below. The implementation's README (local run, deploy, webhooks, backup) is part of what the agent delivers (section 19 of the spec). The spec and the decision files are written in Portuguese.

## What the system does (summary of the contract)

- `./reserva serve --porta N --dados DIR` brings everything up; `DIR/restaurante.json` configures the restaurant (tables, shifts, duration by party size, holidays, kitchen limit, FAQ...).
- The customer books through the chat (`/`) or WhatsApp: name → party size → day → time. They check and cancel their own booking, get FAQ answers, ask for a human and send "PARAR" (stop).
- Staff: `/equipe` (token) with the day's bookings by shift and dining room, an occupancy map by time slot, arrival/no-show, approve/refuse large parties, records and blocks; Telegram with `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` and alerts for new bookings, cancellations and large parties.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` writes `clientes_novos_mes` and `retorno_atual_pct` (ids of the `restaurante` package) into the Panel file.
- Integrations only through environment variables (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); without them, a simulated outbox and no network calls.

## How to run it in your environment

The cycle is: answer the decisions → freeze the contract → run an agent until `93 passed` + `LIMITES OK` → independent verification. All through your subscription (Codex or Claude Code); no paid API is called.

### Prerequisites

- Linux/macOS with `git`, `python3` ≥ 3.10 and `pytest` (`python3 -m pip install pytest` — a development tool; the application will have no dependencies).
- An agent: **Codex CLI** (`codex`, logged in through the subscription) or **Claude Code** (`claude`).
- For the headless loop: `~/projetos/execucao-longa` cloned (or copied) — it uses `tools/loop-longrun.sh`; `systemd-run` (Linux) for the memory cap.
- For the independent verification: `docker` (does a `docker build` and starts the container once).

### 1. Decisions and freezing

1. Read `docs/DECISOES-ABERTAS.md`. If you change anything marked ⚠, edit `docs/ESPECIFICACAO.md` and the tests **before** freezing.
2. Check that the suite is collected without errors and that nothing passes yet:
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 0 passed (clean failures/errors: ./reserva is missing)
   ```
3. Commit everything and freeze the contract (records the hash of `tests/`, `pytest.ini`, the spec and the verifier + the base commit in `hash-congelado.txt`):
   ```sh
   git add -A && git commit -m "contrato v1"
   bash longrun/2026-10-05-reservas-v1/congelar.sh
   ```

### 2a. Headless loop (Codex `codex exec`, recommended)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Reads `loop.env` (quick test, final test, protected files, 20 cycles × 30 min, 8 GB, stop after 3 cycles without progress, model `gpt-6-astra`, `CODEX_ARGS` with `sandbox_workspace_write.network_access=true` — without it the Codex sandbox blocks the tests' local server). Each cycle receives `prompt.md`, implements, runs the tests and updates `state.md`/`plan.md`/`progress.md`; the loop commits at each checkpoint and only closes when the final test passes in full.

### 2b. `/goal` in Claude Code

Open a **fresh** Claude Code session in the project folder and follow `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md`: paste the `/goal` condition (the output must show `93 passed` and `LIMITES OK`) and, as the first message, the block of `prompt-goal-codex.md` starting at `RESULTADO:`. Local commits at each checkpoint, author `inematds`.

### 2c. `/goal` in the Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```
Paste the contents of `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`.

### 3. Follow progress

- `tail -f longrun/2026-10-05-reservas-v1/loop.log` (headless) and `progress.md` (one line per checkpoint, with `N passed / N failed`).
- `state.md` says what works, what is missing and how to resume; `failures.md` records a test × spec conflict (human gate: do **not** adjust the test or the spec on the agent's behalf).
- `canal.md` keeps facts and pitfalls that context compaction loses.
- Stop and look when: 3 cycles without progress, the same plan repeated, a request for an API/credential/deploy.

### 4. Final verification

```sh
python3 -m pytest -q tests/                                   # 93 passed
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh       # LIMITES OK
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` is the "limit" layer of `goal.md`: contract hash intact, same number of tests, only files in scope, no SDK/external dependency, no credential, no external URL, no `0.0.0.0` in the code. `verificar-independente.py` (level 4, the agent does not see it in the prompt) looks for fixture values copied into the code, brings up a **never-seen** restaurant (15-minute step, one shift, a 3-table combination, no kitchen limit) with every argument explicit, and does a `docker build` + healthcheck of the container. Then open `/` and `/equipe` in the browser.

## Structure

```
docs/ESPECIFICACAO.md      contract (protected)
docs/DECISOES-ABERTAS.md   default proposals + owner's questions
docs/MAPA-RAIO-X.md        Raio-X leaks × pieces of the system
docs/VALIDACAO.md          adversarial validation of the plan (05/10): checklist, verified arithmetic, check output
tests/                     93 black-box tests + conftest (fake Evolution/Telegram server; an autouse teardown stops every server)
tests/fixtures/restaurante.json   test restaurant (token segredo-teste)
exemplos/restaurante.json  same restaurant, token TROQUE-ESTE-TOKEN (copied into --dados if missing)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, freeze script, verifiers
```
