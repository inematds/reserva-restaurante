# reserva-restaurante

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Restaurante](guia/assets/banner.jpg)](https://inematds.github.io/reserva-restaurante/guia/)

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/reserva-restaurante/guia/**

Reserva de mesa para **un restaurante**, con Python 3 y biblioteca estándar: salones y mesas con capacidad, turnos por día de la semana, asignación automática de la mesa más pequeña que sirva, confirmación automática ("1 confirma / 2 cancela"), no-show, lista de espera, grupo grande con aprobación del equipo, FAQ, traspaso a un humano, base propia de clientes con consentimiento (cumpleaños, invitación de regreso, campañas), chat web + WhatsApp mediante la Evolution API, equipo por Telegram y por la página `/equipe`, backup/restauración, Docker y exportación mensual al Panel de Recuperación del Raio-X de Margem (paquete `restaurante`).

**Estado:** v0.7.0 — implementación completa, incluyendo chat, equipo y entrega Docker; 93/93 pruebas pasan y LIMITES OK. Navegador local validado; verificación independiente OK (restaurante nunca visto, `docker build` + healthcheck del contenedor). Falta lo que depende del dueño: credenciales reales de Evolution/WhatsApp y de Telegram, despliegue en su VPS y datos reales del restaurante. Para ejecutarlo, vea [Ejecutar localmente](#ejecutar-localmente) y [Despliegue en la VPS](#despliegue-en-la-vps).

## Qué hace el sistema (resumen del contrato)

- `./reserva serve --porta N --dados DIR` levanta todo; `DIR/restaurante.json` configura el restaurante (mesas, turnos, duración por tamaño de grupo, festivos, límite de la cocina, FAQ…).
- El cliente reserva por el chat (`/`) o por WhatsApp: nombre → personas → día → horario. Consulta y cancela su propia reserva, resuelve dudas del FAQ, pide un agente, envía "PARAR".
- Equipo: `/equipe` (token) con las reservas del día por turno y salón, mapa de ocupación por horario, llegada/no-show, aprobar/rechazar grupo grande, registros y bloqueos; Telegram con `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` y avisos de reserva nueva, cancelada y grupo grande.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` graba `clientes_novos_mes` y `retorno_atual_pct` (ids del paquete `restaurante`) en el archivo del Panel.
- Integraciones solo mediante variables de entorno (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); sin ellas, bandeja de salida simulada y ninguna llamada de red.

## Cómo se construyó (método, para rehacer o adaptar)

El sistema se construyó así: decisiones respondidas → contrato congelado → un agente corrió hasta `93 passed` + `LIMITES OK` → verificación independiente aprobada. Todo mediante la suscripción (Codex o Claude Code); no se llamó a ninguna API de pago. Para solo usar el sistema, salte a [Ejecutar localmente](#ejecutar-localmente). Los pasos siguientes permanecen en el repositorio para quien quiera rehacer o adaptar (cambiar reglas, otro restaurante).

### Requisitos previos

- Linux/macOS con `git`, `python3` ≥ 3.10 y `pytest` (`python3 -m pip install pytest` — herramienta de desarrollo; la aplicación no tiene dependencias).
- Un agente: **Codex CLI** (`codex`, con sesión iniciada mediante la suscripción) o **Claude Code** (`claude`).
- Para el loop headless: `~/projetos/execucao-longa` clonado (o copiado) — usa `tools/loop-longrun.sh`; `systemd-run` (Linux) para el tope de memoria.
- Para la verificación independiente: `docker` (hace `docker build` y levanta el contenedor una vez).

### 1. Decisiones y congelamiento

1. Lea `docs/DECISOES-ABERTAS.md`. Si cambia algo marcado con ⚠, edite `docs/ESPECIFICACAO.md` y las pruebas **antes** de congelar.
2. Compruebe que la suite se recoge sin error (en el repositorio actual, con `./reserva` ya implementado, pasa completa; al rehacer desde cero, sin `./reserva`, nada pasaba al inicio):
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 93 passed (do zero, sem ./reserva: 0 passed)
   ```
3. Haga commit de todo y congele el contrato (graba el hash de `tests/`, `pytest.ini`, la spec y el verificador + el commit base en `hash-congelado.txt`):
   ```sh
   git add -A && git commit -m "contrato v1"
   bash longrun/2026-10-05-reservas-v1/congelar.sh
   ```

### 2a. Loop headless (Codex `codex exec`, recomendado)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Lee `loop.env` (prueba rápida, prueba final, archivos protegidos, 20 ciclos × 30 min, 8 GB, parada tras 3 ciclos sin avance, modelo `gpt-6-astra`, `CODEX_ARGS` con `sandbox_workspace_write.network_access=true` — sin eso el sandbox de Codex bloquea el servidor local de las pruebas). Cada ciclo recibe `prompt.md`, implementa, ejecuta las pruebas y actualiza `state.md`/`plan.md`/`progress.md`; el loop hace el commit en cada checkpoint y solo cierra cuando la prueba final pasa completa.

### 2b. `/goal` en Claude Code

Abra una sesión **nueva** de Claude Code en la carpeta del proyecto y siga `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md`: pegue la condición de `/goal` (la salida debe mostrar `93 passed` y `LIMITES OK`) y, como primer mensaje, el bloque de `prompt-goal-codex.md` a partir de `RESULTADO:`. Commits locales en cada checkpoint, autor `inematds`.

### 2c. `/goal` en el Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```
Pegue el contenido de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`.

### 3. Seguimiento

- `tail -f longrun/2026-10-05-reservas-v1/loop.log` (headless) y `progress.md` (una línea por checkpoint, con `N passed / N failed`).
- `state.md` dice qué funciona, qué falta y cómo retomar; `failures.md` registra prueba × spec en conflicto (puerta humana: **no** ajustar prueba ni spec por cuenta del agente).
- `canal.md` guarda hechos y trampas que la compactación de contexto pierde.
- Parar y revisar cuando: 3 ciclos sin avance, el mismo plan repetido, solicitud de API/credencial/despliegue.

### 4. Verificación final

```sh
python3 -m pytest -q tests/                                   # 93 passed
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh       # LIMITES OK
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` es la capa "límite" del `goal.md`: hash del contrato intacto, nº de pruebas igual, solo archivos del alcance, sin SDK/dependencia externa, sin credencial, sin URL externa, sin `0.0.0.0` en el código. `verificar-independente.py` (nivel 4, el agente no lo ve en el prompt) busca valores de la fixture copiados en el código, levanta un restaurante **nunca visto** (paso de 15 min, un turno, combinación de 3 mesas, sin límite de cocina) con todos los argumentos explícitos, y hace `docker build` + healthcheck del contenedor. Después, abrir `/` y `/equipe` en el navegador.

## Estructura

```
docs/ESPECIFICACAO.md      contrato (protegido)
docs/DECISOES-ABERTAS.md   propostas padrão + perguntas do dono
docs/MAPA-RAIO-X.md        vazamentos do Raio-X × peças do sistema
docs/VALIDACAO.md          validação adversarial do plano (05/10): checklist, contas conferidas, saída dos checks
tests/                     93 testes caixa-preta + conftest (servidor falso de Evolution/Telegram; teardown autouse derruba todo servidor)
tests/fixtures/restaurante.json   restaurante de teste (token segredo-teste)
exemplos/restaurante.json  mesmo restaurante, token TROQUE-ESTE-TOKEN (copiado para --dados se faltar)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, congelar, verificadores
```


## Ejecutar localmente

Requiere Python 3, sin paquetes adicionales para la aplicación:

```sh
./reserva serve --porta 8080 --dados ./dados
```

La primera línea informa `PORTA=<n>`; `--porta 0` elige un puerto libre.
El servidor escucha en `127.0.0.1`. En la primera ejecución crea la carpeta de datos,
copia `exemplos/restaurante.json` y siembra `reservas.sqlite3`.
Cambie el token en el JSON antes de usar datos reales. Las rutas del equipo exigen
`X-Token`; `/api/saude`, `/api/saloes` y `GET /api/turnos` son públicas.
Mesas, turnos y FAQ se persisten en SQLite y se editan mediante las rutas de la sección 14;
editar esas listas en el JSON después de la primera ejecución no altera la base de datos.
Las demás configuraciones del JSON se recargan al reiniciar.

`RESERVA_AGORA=AAAA-MM-DDTHH:MM` fija el reloj para pruebas; sin la variable,
el sistema usa la hora local. Los clientes y las reservas ya pueden gestionarse por la API
(`/api/clientes`, `/api/reservas` y `/api/ocupacao`); la disponibilidad es pública
en `/api/horarios?data=AAAA-MM-DD&pessoas=N`. La cancelación, la reprogramación y
la llegada/no-show usan las acciones de la sección 5 del contrato. La conversación funciona mediante `POST /api/mensagens`; las ofertas de espera, la confirmación,
la aprobación/rechazo y las campañas usan una bandeja de salida simulada (`GET /api/saida`).
Ejecute `POST /api/tarefas/rodar` para generar las confirmaciones, cumpleaños e invitaciones
de regreso pendientes. El estado de la conversación y el historial persisten en la base de datos.
Abra `http://127.0.0.1:8080/` para conversar o `/equipe` para operar con el token.
Evolution y Telegram usan exclusivamente las variables de entorno documentadas;
sin configuración, los envíos son simulados. El equipo puede ejecutar tareas en la página.
El sistema no cobra señal/Pix: cualquier política para grupos debe constar en el FAQ.

## Despliegue en la VPS

La entrega usa la imagen oficial de Python, sin instalar paquetes. En el servidor con
Docker y Compose instalados:

```sh
cp .env.exemplo .env
mkdir -p dados backups
cp exemplos/restaurante.json dados/restaurante.json
# Edite dados/restaurante.json: token exclusivo, nome, mesas e horários reais.
# Preencha .env somente para os canais que deseja ativar.
chmod 600 .env dados/restaurante.json
docker compose up -d --build
docker compose ps
```

El volumen `./dados:/dados` preserva SQLite y la configuración; `./backups:/backups`
recibe las copias. El puerto queda publicado en `127.0.0.1:8080:8080`. Configure el
proxy inverso de la VPS (Nginx o Caddy) con certificado HTTPS para su dominio,
reenviando a `http://127.0.0.1:8080`. Preserve los headers de los webhooks.
Ajuste la zona horaria del contenedor a la hora local del restaurante (variable `TZ`
en el entorno del servicio, según la región). No fije `RESERVA_AGORA` en producción.

Evolution: complete `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`
y `WEBHOOK_SEGREDO`. Configure en la instancia el evento `MESSAGES_UPSERT` y el destino
HTTPS de su dominio con `/webhook/evolution/<segredo>`; `<segredo>` debe ser
exactamente `WEBHOOK_SEGREDO`.

Telegram: complete `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
y `TELEGRAM_SEGREDO`. Mediante el servicio de Telegram, registre `setWebhook` con el campo
`url` apuntando a la dirección HTTPS `/webhook/telegram` y `secret_token` igual a
`TELEGRAM_SEGREDO`. Agregue el bot al grupo configurado. Las respuestas a las atenciones
y los comandos `/fila`, `/reservas`, `/responder`, `/encerrar`, `/aprovar` y `/recusar`
operan sobre la misma base que la página del equipo. Estas configuraciones externas las realiza
el operador; ningún servicio real fue llamado durante la implementación.

Backup diario: adapte `/caminho/reserva-restaurante` en el cron del host:

```cron
15 3 * * * cd /caminho/reserva-restaurante && docker compose exec -T reserva ./reserva backup --dados /dados --saida /backups/diario-$(date +\%F).zip
```

Copie los backups a un almacenamiento seguro fuera de la VPS y aplique retención.
Para restaurar, primero detenga el servicio; después use un contenedor temporal:

```sh
docker compose stop reserva
docker compose run --rm --no-deps reserva ./reserva restaurar --dados /dados --entrada /backups/diario-AAAA-MM-DD.zip
docker compose up -d reserva
```

Las confirmaciones, cumpleaños, reactivación y reenvíos dependen de `POST /api/tarefas/rodar`.
Además del botón en el equipo, el operador puede programar esa ruta en localhost con el header
`X-Token`, por ejemplo cada cinco minutos; es idempotente. Proteja el token en el
programador y no lo exponga en logs. No se ejecutó ningún despliegue durante la construcción: el despliegue en la VPS corresponde al dueño.

## Backup e indicadores

`./reserva backup --dados ./dados --saida copia.bak` crea un archivo ZIP con
la configuración y una copia consistente del SQLite, incluso con el servidor encendido.
Detenga el servidor antes de `./reserva restaurar --dados ./dados --entrada copia.bak`.
La restauración sustituye la base de datos y la configuración. Guarde el backup con acceso restringido:
contiene los datos personales existentes en el momento de la copia.

`GET /api/raiox?mes=AAAA-MM` calcula los indicadores mensuales para el equipo.
`./reserva raiox --dados ./dados --mes AAAA-MM --acompanhamento painel.json`
actualiza el mes en el seguimiento existente, preservando las medidas heredadas
del mes anterior (o de la base). Los bloqueos se gestionan en `/api/bloqueios`;
la eliminación en `/api/clientes/{id}` anonimiza y cancela las reservas futuras
mediante el flujo normal de oferta a la lista de espera.
