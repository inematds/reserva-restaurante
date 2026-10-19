# reserva-restaurante

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Restaurante](guia/assets/banner.jpg)](https://inematds.github.io/reserva-restaurante/guia/)

## 📖 User guide

Full guide (landing page + step by step): **https://inematds.github.io/reserva-restaurante/guia/**

Table reservations for **a single restaurant**, built with Python 3 and the standard library: dining rooms and tables with capacity, shifts by day of the week, automatic allocation of the smallest table that fits, automatic confirmation ("1 confirms / 2 cancels"), no-shows, waitlist, large groups with staff approval, FAQ, handoff to a human, a customer database of its own with consent (birthdays, come-back invitations, campaigns), web chat + WhatsApp through the Evolution API, staff access through Telegram and the `/equipe` page, backup/restore, Docker, and monthly export to the Recovery Dashboard of the Margin X-Ray (the `restaurante` package).

**Status:** v0.7.0 — complete implementation, including chat, staff and Docker delivery; 93/93 tests pass and LIMITES OK. Validated in a local browser; independent verification OK (a restaurant it had never seen, `docker build` + container healthcheck). What remains depends on the owner: real Evolution/WhatsApp and Telegram credentials, deployment on their VPS, and the restaurant's real data. To run it, see [Run locally](#run-locally) and [Deploy on the VPS](#deploy-on-the-vps).

## What the system does (contract summary)

- `./reserva serve --porta N --dados DIR` brings everything up; `DIR/restaurante.json` configures the restaurant (tables, shifts, duration by party size, holidays, kitchen limit, FAQ…).
- Customers book through the chat (`/`) or WhatsApp: name → party size → day → time. They can look up and cancel their own reservation, get answers from the FAQ, ask for an attendant, and send "PARAR" (stop).
- Staff: `/equipe` (token) with the day's reservations by shift and dining room, an occupancy map by time slot, arrival/no-show, approve/decline large groups, customer records and blocks; Telegram with `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` and alerts for new reservations, cancellations and large groups.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` writes `clientes_novos_mes` and `retorno_atual_pct` (ids from the `restaurante` package) to the Dashboard file.
- Integrations only through environment variables (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); without them, a simulated outbox is used and no network call is made.

## How it was built (method, to redo or adapt)

The system was built like this: decisions answered → contract frozen → an agent ran until `93 passed` + `LIMITES OK` → independent verification approved. All through a subscription (Codex or Claude Code); no paid API was called. If you just want to use the system, skip to [Run locally](#run-locally). The steps below stay in the repository for anyone who wants to redo or adapt it (change rules, another restaurant).

### Prerequisites

- Linux/macOS with `git`, `python3` ≥ 3.10 and `pytest` (`python3 -m pip install pytest` — a development tool; the application has no dependencies).
- An agent: **Codex CLI** (`codex`, logged in through the subscription) or **Claude Code** (`claude`).
- For the headless loop: `~/projetos/execucao-longa` cloned (or copied) — it uses `tools/loop-longrun.sh`; `systemd-run` (Linux) for the memory cap.
- For the independent verification: `docker` (runs `docker build` and brings the container up once).

### 1. Decisions and freezing

1. Read `docs/DECISOES-ABERTAS.md`. If you change anything marked ⚠, edit `docs/ESPECIFICACAO.md` and the tests **before** freezing.
2. Check that the suite collects without errors (in the current repository, with `./reserva` already implemented, it passes in full; when redoing from scratch, without `./reserva`, nothing passed at the start):
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 93 passed (from scratch, without ./reserva: 0 passed)
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

Reads `loop.env` (fast test, final test, protected files, 20 cycles × 30 min, 8 GB, stop after 3 cycles without progress, model `gpt-6-astra`, `CODEX_ARGS` with `sandbox_workspace_write.network_access=true` — without it the Codex sandbox blocks the tests' local server). Each cycle receives `prompt.md`, implements, runs the tests and updates `state.md`/`plan.md`/`progress.md`; the loop commits at each checkpoint and only finishes when the final test passes in full.

### 2b. `/goal` in Claude Code

Open a **new** Claude Code session in the project folder and follow `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md`: paste the `/goal` condition (the output must show `93 passed` and `LIMITES OK`) and, as the first message, the block from `prompt-goal-codex.md` starting at `RESULTADO:`. Local commits at each checkpoint, author `inematds`.

### 2c. `/goal` in the Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```
Paste the contents of `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`.

### 3. Monitoring

- `tail -f longrun/2026-10-05-reservas-v1/loop.log` (headless) and `progress.md` (one line per checkpoint, with `N passed / N failed`).
- `state.md` says what works, what is missing and how to resume; `failures.md` records test × spec conflicts (human gate: do **not** adjust a test or the spec on the agent's own initiative).
- `canal.md` holds facts and pitfalls that context compaction loses.
- Stop and take a look when: 3 cycles without progress, the same plan repeated, a request for an API/credential/deploy.

### 4. Final verification

```sh
python3 -m pytest -q tests/                                   # 93 passed
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh       # LIMITES OK
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` is the "limit" layer of `goal.md`: contract hash intact, same number of tests, only files within scope, no SDK/external dependency, no credentials, no external URL, no `0.0.0.0` in the code. `verificar-independente.py` (level 4, the agent does not see it in the prompt) looks for fixture values copied into the code, brings up a restaurant it has **never seen** (15-minute step, one shift, a combination of 3 tables, no kitchen limit) with all arguments explicit, and runs `docker build` + the container healthcheck. Afterwards, open `/` and `/equipe` in the browser.

## Structure

```
docs/ESPECIFICACAO.md      contract (protected)
docs/DECISOES-ABERTAS.md   default proposals + questions for the owner
docs/MAPA-RAIO-X.md        X-Ray leaks × system components
docs/VALIDACAO.md          adversarial validation of the plan (05/10): checklist, verified calculations, check output
tests/                     93 black-box tests + conftest (fake Evolution/Telegram server; autouse teardown shuts down every server)
tests/fixtures/restaurante.json   test restaurant (token segredo-teste)
exemplos/restaurante.json  same restaurant, token TROQUE-ESTE-TOKEN (copied to --dados if missing)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, freeze script, verifiers
```


## Run locally

Requires Python 3, with no additional packages for the application:

```sh
./reserva serve --porta 8080 --dados ./dados
```

The first line reports `PORTA=<n>`; `--porta 0` picks a free port.
The server listens on `127.0.0.1`. On the first run it creates the data folder,
copies `exemplos/restaurante.json` and seeds `reservas.sqlite3`.
Change the token in the JSON before using real data. Staff routes require
`X-Token`; `/api/saude`, `/api/saloes` and `GET /api/turnos` are public.
Tables, shifts and the FAQ are persisted in SQLite and edited through the routes in section 14;
editing those lists in the JSON after the first run does not change the database.
Other settings in the JSON are reloaded on restart.

`RESERVA_AGORA=AAAA-MM-DDTHH:MM` fixes the clock for testing; without the variable,
the system uses local time. Customers and reservations can already be managed through the API
(`/api/clientes`, `/api/reservas` and `/api/ocupacao`); availability is public
at `/api/horarios?data=AAAA-MM-DD&pessoas=N`. Cancellation, rescheduling and
arrival/no-show use the actions in section 5 of the contract. The conversation works through `POST /api/mensagens`; waitlist offers, confirmation,
approval/decline and campaigns use a simulated outbox (`GET /api/saida`).
Run `POST /api/tarefas/rodar` to generate the confirmations, birthdays and come-back invitations
that are due. Conversation state and history persist in the database.
Open `http://127.0.0.1:8080/` to chat or `/equipe` to operate with the token.
Evolution and Telegram use only the documented environment variables;
without configuration, sends are simulated. Staff can run tasks from the page.
The system does not charge a deposit/Pix: any policy for groups must be stated in the FAQ.

## Deploy on the VPS

The delivery uses the official Python image, without installing any packages. On a server
with Docker and Compose installed:

```sh
cp .env.exemplo .env
mkdir -p dados backups
cp exemplos/restaurante.json dados/restaurante.json
# Edit dados/restaurante.json: unique token, name, real tables and hours.
# Fill in .env only for the channels you want to enable.
chmod 600 .env dados/restaurante.json
docker compose up -d --build
docker compose ps
```

The `./dados:/dados` volume preserves SQLite and the configuration; `./backups:/backups`
receives the copies. The port is published at `127.0.0.1:8080:8080`. Configure the
VPS reverse proxy (Nginx or Caddy) with an HTTPS certificate for your domain,
forwarding to `http://127.0.0.1:8080`. Preserve the webhook headers.
Set the container's time zone to the restaurant's local time (the `TZ` variable
in the service environment, according to your region). Do not set `RESERVA_AGORA` in production.

Evolution: fill in `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`
and `WEBHOOK_SEGREDO`. In the instance, configure the `MESSAGES_UPSERT` event and the
HTTPS destination of your domain with `/webhook/evolution/<segredo>`; `<segredo>` must be
exactly `WEBHOOK_SEGREDO`.

Telegram: fill in `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
and `TELEGRAM_SEGREDO`. Through the Telegram service, register `setWebhook` with the `url`
field pointing to the HTTPS address `/webhook/telegram` and `secret_token` equal to
`TELEGRAM_SEGREDO`. Add the bot to the configured group. Replies to support requests
and the commands `/fila`, `/reservas`, `/responder`, `/encerrar`, `/aprovar` and `/recusar`
operate on the same database as the staff page. These external settings are made
by the operator; no real service was called during the implementation.

Daily backup: adapt `/caminho/reserva-restaurante` in the host's cron:

```cron
15 3 * * * cd /caminho/reserva-restaurante && docker compose exec -T reserva ./reserva backup --dados /dados --saida /backups/diario-$(date +\%F).zip
```

Copy the backups to secure storage outside the VPS and apply a retention policy.
To restore, first stop the service; then use a temporary container:

```sh
docker compose stop reserva
docker compose run --rm --no-deps reserva ./reserva restaurar --dados /dados --entrada /backups/diario-AAAA-MM-DD.zip
docker compose up -d reserva
```

Confirmations, birthdays, reactivation and resends depend on `POST /api/tarefas/rodar`.
Besides the button on the staff page, the operator can schedule this route on localhost with the
`X-Token` header, for example every five minutes; it is idempotent. Protect the token in the
scheduler and do not expose it in logs. No deployment was executed during the build: deploying to the VPS is the owner's job.

## Backup and indicators

`./reserva backup --dados ./dados --saida copia.bak` creates a ZIP file with
the configuration and a consistent copy of the SQLite database, even with the server running.
Stop the server before `./reserva restaurar --dados ./dados --entrada copia.bak`.
Restoring replaces the database and the configuration. Keep the backup with restricted access:
it contains the personal data that existed at the time of the copy.

`GET /api/raiox?mes=AAAA-MM` computes the monthly indicators for the staff.
`./reserva raiox --dados ./dados --mes AAAA-MM --acompanhamento painel.json`
updates the month in the existing tracking file, preserving the measures inherited
from the previous month (or from the baseline). Blocks are managed at `/api/bloqueios`;
deletion at `/api/clientes/{id}` anonymizes the record and cancels future reservations
through the normal flow of offering the slot to the waitlist.
