# reserva-restaurante

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Restaurante](guia/assets/banner-es.jpg)](https://inematds.github.io/reserva-restaurante/guia/es/)

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/reserva-restaurante/guia/es/**

Reserva de mesa para **un solo restaurante**, con Python 3 y su biblioteca estándar (planificado): salones y mesas con capacidad, turnos por día de la semana, asignación automática de la mesa más pequeña que sirve, confirmación automática ("1 confirma / 2 cancela"), no-show, lista de espera, grupos grandes con aprobación del equipo, preguntas frecuentes, traspaso a un humano, base propia de clientes con consentimiento (cumpleaños, invitación de regreso, campañas), chat web + WhatsApp mediante la Evolution API, equipo en Telegram y en la página `/equipe`, respaldo/restauración, Docker y exportación mensual al Panel de Recuperación de Raio-X de Margem (paquete `restaurante`).

> Las reglas de negocio incorporadas (LGPD, la ley de privacidad de Brasil, y términos de marketplaces como iFood) son de Brasil.

**Estado (05/10/2026): solo el plan.** Este repo tiene el contrato (`docs/ESPECIFICACAO.md`), 93 pruebas de aceptación de caja negra (`tests/`), las decisiones (`docs/DECISOES-ABERTAS.md`), el mapa hacia Raio-X (`docs/MAPA-RAIO-X.md`) y la carpeta de ejecución larga (`longrun/2026-10-05-reservas-v1/`). **No hay implementación** (`./reserva`, `src/`, `web/`, `Dockerfile`): la produce un agente que corre contra las pruebas, en tu propio entorno, como se describe abajo. El README de la implementación (ejecución local, despliegue, webhooks, respaldo) es parte de lo que entrega el agente (sección 19 de la spec). La spec y los archivos de decisiones están escritos en portugués.

## Qué hace el sistema (resumen del contrato)

- `./reserva serve --porta N --dados DIR` levanta todo; `DIR/restaurante.json` configura el restaurante (mesas, turnos, duración según el tamaño del grupo, feriados, límite de cocina, preguntas frecuentes...).
- El cliente reserva por el chat (`/`) o por WhatsApp: nombre → personas → día → hora. Consulta y cancela su propia reserva, resuelve dudas con las preguntas frecuentes, pide un humano y envía "PARAR".
- Equipo: `/equipe` (token) con las reservas del día por turno y salón, mapa de ocupación por horario, llegada/no-show, aprobar/rechazar grupos grandes, registros y bloqueos; Telegram con `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` y avisos de reserva nueva, cancelada y grupo grande.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` graba `clientes_novos_mes` y `retorno_atual_pct` (ids del paquete `restaurante`) en el archivo del Panel.
- Integraciones solo por variables de entorno (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); sin ellas, bandeja de salida simulada y ninguna llamada de red.

## Cómo ejecutarlo en tu entorno

El ciclo es: responder las decisiones → congelar el contrato → ejecutar un agente hasta `93 passed` + `LIMITES OK` → verificación independiente. Todo por suscripción (Codex o Claude Code); no se llama a ninguna API de pago.

### Requisitos previos

- Linux/macOS con `git`, `python3` ≥ 3.10 y `pytest` (`python3 -m pip install pytest` — herramienta de desarrollo; la aplicación no tendrá dependencias).
- Un agente: **Codex CLI** (`codex`, con sesión iniciada por suscripción) o **Claude Code** (`claude`).
- Para el bucle headless: `~/projetos/execucao-longa` clonado (o copiado) — usa `tools/loop-longrun.sh`; `systemd-run` (Linux) para el tope de memoria.
- Para la verificación independiente: `docker` (hace un `docker build` y levanta el contenedor una vez).

### 1. Decisiones y congelamiento

1. Lee `docs/DECISOES-ABERTAS.md`. Si cambias algo marcado con ⚠, edita `docs/ESPECIFICACAO.md` y las pruebas **antes** de congelar.
2. Comprueba que la suite se recoge sin errores y que aún nada pasa:
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 0 passed (fallos/errores limpios: falta ./reserva)
   ```
3. Haz commit de todo y congela el contrato (graba el hash de `tests/`, `pytest.ini`, la spec y el verificador + el commit base en `hash-congelado.txt`):
   ```sh
   git add -A && git commit -m "contrato v1"
   bash longrun/2026-10-05-reservas-v1/congelar.sh
   ```

### 2a. Bucle headless (Codex `codex exec`, recomendado)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Lee `loop.env` (prueba rápida, prueba final, archivos protegidos, 20 ciclos × 30 min, 8 GB, parada tras 3 ciclos sin avance, modelo `gpt-6-astra`, `CODEX_ARGS` con `sandbox_workspace_write.network_access=true` — sin esto el sandbox de Codex bloquea el servidor local de las pruebas). Cada ciclo recibe `prompt.md`, implementa, ejecuta las pruebas y actualiza `state.md`/`plan.md`/`progress.md`; el bucle hace commit en cada checkpoint y solo cierra cuando la prueba final pasa completa.

### 2b. `/goal` en Claude Code

Abre una sesión **nueva** de Claude Code en la carpeta del proyecto y sigue `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md`: pega la condición de `/goal` (la salida debe mostrar `93 passed` y `LIMITES OK`) y, como primer mensaje, el bloque de `prompt-goal-codex.md` a partir de `RESULTADO:`. Commits locales en cada checkpoint, autor `inematds`.

### 2c. `/goal` en el Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```
Pega el contenido de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`.

### 3. Seguir el avance

- `tail -f longrun/2026-10-05-reservas-v1/loop.log` (headless) y `progress.md` (una línea por checkpoint, con `N passed / N failed`).
- `state.md` dice qué funciona, qué falta y cómo retomar; `failures.md` registra un conflicto prueba × spec (compuerta humana: **no** ajustar la prueba ni la spec por cuenta del agente).
- `canal.md` guarda hechos y trampas que la compactación de contexto pierde.
- Detenerse y mirar cuando: 3 ciclos sin avance, el mismo plan repetido, un pedido de API/credencial/despliegue.

### 4. Verificación final

```sh
python3 -m pytest -q tests/                                   # 93 passed
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh       # LIMITES OK
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` es la capa "límite" del `goal.md`: hash del contrato intacto, mismo número de pruebas, solo archivos del alcance, sin SDK/dependencia externa, sin credencial, sin URL externa, sin `0.0.0.0` en el código. `verificar-independente.py` (nivel 4, el agente no lo ve en el prompt) busca valores de la fixture copiados en el código, levanta un restaurante **nunca visto** (paso de 15 min, un turno, combinación de 3 mesas, sin límite de cocina) con todos los argumentos explícitos, y hace `docker build` + healthcheck del contenedor. Después, abre `/` y `/equipe` en el navegador.

## Estructura

```
docs/ESPECIFICACAO.md      contrato (protegido)
docs/DECISOES-ABERTAS.md   propuestas por defecto + preguntas del dueño
docs/MAPA-RAIO-X.md        fugas de Raio-X × piezas del sistema
docs/VALIDACAO.md          validación adversarial del plan (05/10): checklist, cuentas verificadas, salida de los checks
tests/                     93 pruebas de caja negra + conftest (servidor falso de Evolution/Telegram; un teardown autouse detiene todo servidor)
tests/fixtures/restaurante.json   restaurante de prueba (token segredo-teste)
exemplos/restaurante.json  el mismo restaurante, token TROQUE-ESTE-TOKEN (se copia a --dados si falta)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, script de congelamiento, verificadores
```
