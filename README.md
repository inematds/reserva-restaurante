# reserva-restaurante

Reserva de mesa para **um restaurante**, com Python 3 e biblioteca padrão (planejado): salões e mesas com capacidade, turnos por dia da semana, alocação automática da menor mesa que serve, confirmação automática ("1 confirma / 2 cancela"), no-show, lista de espera, grupo grande com aprovação da equipe, FAQ, passagem para humano, base própria de clientes com consentimento (aniversário, convite de retorno, campanhas), chat web + WhatsApp pela Evolution API, equipe pelo Telegram e pela página `/equipe`, backup/restauração, Docker e exportação mensal para o Painel de Recuperação do Raio-X de Margem (pacote `restaurante`).

**Estado (05/10/2026): só o plano.** Este repo tem o contrato (`docs/ESPECIFICACAO.md`), 93 testes de aceitação caixa-preta (`tests/`), as decisões (`docs/DECISOES-ABERTAS.md`), o mapa para o Raio-X (`docs/MAPA-RAIO-X.md`) e a pasta de execução longa (`longrun/2026-10-05-reservas-v1/`). **Não há implementação** (`./reserva`, `src/`, `web/`, `Dockerfile`): ela é produzida por um agente rodando contra os testes, no seu ambiente, como descrito abaixo. O README da implementação (execução local, deploy, webhooks, backup) é parte do que o agente entrega (seção 19 da spec).

## O que o sistema faz (resumo do contrato)

- `./reserva serve --porta N --dados DIR` sobe tudo; `DIR/restaurante.json` configura o restaurante (mesas, turnos, duração por tamanho de grupo, feriados, limite da cozinha, FAQ…).
- Cliente reserva pelo chat (`/`) ou pelo WhatsApp: nome → pessoas → dia → horário. Consulta e cancela a própria reserva, tira dúvidas do FAQ, pede atendente, manda "PARAR".
- Equipe: `/equipe` (token) com reservas do dia por turno e salão, mapa de ocupação por horário, chegada/no-show, aprovar/recusar grupo grande, cadastros e bloqueios; Telegram com `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` e avisos de reserva nova, cancelada e grupo grande.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` grava `clientes_novos_mes` e `retorno_atual_pct` (ids do pacote `restaurante`) no arquivo do Painel.
- Integrações só por variáveis de ambiente (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); sem elas, caixa de saída simulada e nenhuma chamada de rede.

## Como rodar no seu ambiente

O ciclo é: responder as decisões → congelar o contrato → rodar um agente até `93 passed` + `LIMITES OK` → verificação independente. Tudo pela assinatura (Codex ou Claude Code); nenhuma API paga é chamada.

### Pré-requisitos

- Linux/macOS com `git`, `python3` ≥ 3.10 e `pytest` (`python3 -m pip install pytest` — ferramenta de desenvolvimento; a aplicação não terá dependências).
- Um agente: **Codex CLI** (`codex`, logado pela assinatura) ou **Claude Code** (`claude`).
- Para o loop headless: `~/projetos/execucao-longa` clonado (ou copiado) — usa `tools/loop-longrun.sh`; `systemd-run` (Linux) para o teto de memória.
- Para a verificação independente: `docker` (faz `docker build` e sobe o container uma vez).

### 1. Decisões e congelamento

1. Leia `docs/DECISOES-ABERTAS.md`. Se mudar algo marcado ⚠, edite `docs/ESPECIFICACAO.md` e os testes **antes** de congelar.
2. Confira que a suíte coleta sem erro e nada passa ainda:
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 0 passed (falhas/erros limpos: falta ./reserva)
   ```
3. Commit tudo e congele o contrato (grava hash de `tests/`, `pytest.ini`, spec e verificador + o commit-base em `hash-congelado.txt`):
   ```sh
   git add -A && git commit -m "contrato v1"
   bash longrun/2026-10-05-reservas-v1/congelar.sh
   ```

### 2a. Loop headless (Codex `codex exec`, recomendado)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Lê `loop.env` (teste rápido, teste final, arquivos protegidos, 20 ciclos × 30 min, 8 GB, parada por 3 ciclos sem avanço, modelo `gpt-6-astra`, `CODEX_ARGS` com `sandbox_workspace_write.network_access=true` — sem isso o sandbox do Codex bloqueia o servidor local dos testes). Cada ciclo recebe `prompt.md`, implementa, roda os testes e atualiza `state.md`/`plan.md`/`progress.md`; o loop faz o commit a cada checkpoint e só fecha quando o teste final passa inteiro.

### 2b. `/goal` no Claude Code

Abra uma sessão **nova** do Claude Code na pasta do projeto e siga `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md`: cole a condição de `/goal` (a saída precisa mostrar `93 passed` e `LIMITES OK`) e, como primeira mensagem, o bloco de `prompt-goal-codex.md` a partir de `RESULTADO:`. Commits locais a cada checkpoint, autor `inematds`.

### 2c. `/goal` no Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```
Cole o conteúdo de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`.

### 3. Acompanhar

- `tail -f longrun/2026-10-05-reservas-v1/loop.log` (headless) e `progress.md` (uma linha por checkpoint, com `N passed / N failed`).
- `state.md` diz o que funciona, o que falta e como retomar; `failures.md` registra teste × spec em conflito (portão humano: **não** ajustar teste nem spec por conta do agente).
- `canal.md` guarda fatos e armadilhas que a compactação de contexto perde.
- Parar e olhar quando: 3 ciclos sem avanço, mesmo plano repetido, pedido de API/credencial/deploy.

### 4. Verificação final

```sh
python3 -m pytest -q tests/                                   # 93 passed
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh       # LIMITES OK
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` é a camada "limite" do `goal.md`: hash do contrato intacto, nº de testes igual, só arquivos do escopo, sem SDK/dependência externa, sem credencial, sem URL externa, sem `0.0.0.0` no código. `verificar-independente.py` (nível 4, o agente não o vê no prompt) procura valores da fixture copiados no código, sobe um restaurante **nunca visto** (passo de 15 min, um turno, combinação de 3 mesas, sem limite de cozinha) com todos os argumentos explícitos, e faz `docker build` + healthcheck do container. Depois, abrir `/` e `/equipe` no navegador.

## Estrutura

```
docs/ESPECIFICACAO.md      contrato (protegido)
docs/DECISOES-ABERTAS.md   propostas padrão + perguntas do dono
docs/MAPA-RAIO-X.md        vazamentos do Raio-X × peças do sistema
tests/                     93 testes caixa-preta + conftest (servidor falso de Evolution/Telegram)
tests/fixtures/restaurante.json   restaurante de teste (token segredo-teste)
exemplos/restaurante.json  mesmo restaurante, token TROQUE-ESTE-TOKEN (copiado para --dados se faltar)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, congelar, verificadores
```
