# reserva-restaurante

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Restaurante](guia/assets/banner.jpg)](https://inematds.github.io/reserva-restaurante/guia/)

## 📖 Guia de uso

Guia completo (landing + passo a passo): **https://inematds.github.io/reserva-restaurante/guia/**

Reserva de mesa para **um restaurante**, com Python 3 e biblioteca padrão: salões e mesas com capacidade, turnos por dia da semana, alocação automática da menor mesa que serve, confirmação automática ("1 confirma / 2 cancela"), no-show, lista de espera, grupo grande com aprovação da equipe, FAQ, passagem para humano, base própria de clientes com consentimento (aniversário, convite de retorno, campanhas), chat web + WhatsApp pela Evolution API, equipe pelo Telegram e pela página `/equipe`, backup/restauração, Docker e exportação mensal para o Painel de Recuperação do Raio-X de Margem (pacote `restaurante`).

**Estado:** v0.7.0 — implementação completa, incluindo chat, equipe e entrega Docker; 93/93 testes passam e LIMITES OK. Navegador local validado; verificação independente OK (restaurante nunca visto, `docker build` + healthcheck do container). Falta o que depende do dono: credenciais reais da Evolution/WhatsApp e do Telegram, deploy na VPS dele e dados reais do restaurante. Para rodar, veja [Executar localmente](#executar-localmente) e [Deploy na VPS](#deploy-na-vps).

## O que o sistema faz (resumo do contrato)

- `./reserva serve --porta N --dados DIR` sobe tudo; `DIR/restaurante.json` configura o restaurante (mesas, turnos, duração por tamanho de grupo, feriados, limite da cozinha, FAQ…).
- Cliente reserva pelo chat (`/`) ou pelo WhatsApp: nome → pessoas → dia → horário. Consulta e cancela a própria reserva, tira dúvidas do FAQ, pede atendente, manda "PARAR".
- Equipe: `/equipe` (token) com reservas do dia por turno e salão, mapa de ocupação por horário, chegada/no-show, aprovar/recusar grupo grande, cadastros e bloqueios; Telegram com `/reservas`, `/fila`, `/responder`, `/encerrar`, `/aprovar`, `/recusar` e avisos de reserva nova, cancelada e grupo grande.
- `./reserva raiox --mes AAAA-MM --acompanhamento ARQ` grava `clientes_novos_mes` e `retorno_atual_pct` (ids do pacote `restaurante`) no arquivo do Painel.
- Integrações só por variáveis de ambiente (`EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_SEGREDO`); sem elas, caixa de saída simulada e nenhuma chamada de rede.

## Como foi construído (método, para refazer ou adaptar)

O sistema foi construído assim: decisões respondidas → contrato congelado → um agente rodou até `93 passed` + `LIMITES OK` → verificação independente aprovada. Tudo pela assinatura (Codex ou Claude Code); nenhuma API paga foi chamada. Para só usar o sistema, pule para [Executar localmente](#executar-localmente). Os passos abaixo continuam no repositório para quem quiser refazer ou adaptar (mudar regras, outro restaurante).

### Pré-requisitos

- Linux/macOS com `git`, `python3` ≥ 3.10 e `pytest` (`python3 -m pip install pytest` — ferramenta de desenvolvimento; a aplicação não tem dependências).
- Um agente: **Codex CLI** (`codex`, logado pela assinatura) ou **Claude Code** (`claude`).
- Para o loop headless: `~/projetos/execucao-longa` clonado (ou copiado) — usa `tools/loop-longrun.sh`; `systemd-run` (Linux) para o teto de memória.
- Para a verificação independente: `docker` (faz `docker build` e sobe o container uma vez).

### 1. Decisões e congelamento

1. Leia `docs/DECISOES-ABERTAS.md`. Se mudar algo marcado ⚠, edite `docs/ESPECIFICACAO.md` e os testes **antes** de congelar.
2. Confira que a suíte coleta sem erro (no repositório atual, com `./reserva` já implementado, ela passa inteira; ao refazer do zero, sem `./reserva`, nada passava no início):
   ```sh
   python3 -m pytest -q --collect-only | tail -1   # 93 tests collected
   python3 -m pytest -q | tail -1                  # 93 passed (do zero, sem ./reserva: 0 passed)
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
docs/VALIDACAO.md          validação adversarial do plano (05/10): checklist, contas conferidas, saída dos checks
tests/                     93 testes caixa-preta + conftest (servidor falso de Evolution/Telegram; teardown autouse derruba todo servidor)
tests/fixtures/restaurante.json   restaurante de teste (token segredo-teste)
exemplos/restaurante.json  mesmo restaurante, token TROQUE-ESTE-TOKEN (copiado para --dados se faltar)
longrun/2026-10-05-reservas-v1/   goal, plan, state, loop.env, prompts, congelar, verificadores
```


## Executar localmente

Requer Python 3, sem pacotes adicionais para a aplicação:

```sh
./reserva serve --porta 8080 --dados ./dados
```

A primeira linha informa `PORTA=<n>`; `--porta 0` escolhe uma porta livre.
O servidor escuta em `127.0.0.1`. Na primeira execução cria a pasta de dados,
copia `exemplos/restaurante.json` e semeia `reservas.sqlite3`.
Troque o token no JSON antes de usar dados reais. Rotas da equipe exigem
`X-Token`; `/api/saude`, `/api/saloes` e `GET /api/turnos` são públicas.
Mesas, turnos e FAQ são persistidos no SQLite e editados pelas rotas da seção 14;
editar essas listas no JSON depois da primeira execução não altera o banco.
Outras configurações do JSON são recarregadas ao reiniciar.

`RESERVA_AGORA=AAAA-MM-DDTHH:MM` fixa o relógio para testes; sem a variável,
o sistema usa a hora local. Clientes e reservas já podem ser gerenciados pela API
(`/api/clientes`, `/api/reservas` e `/api/ocupacao`); a disponibilidade é pública
em `/api/horarios?data=AAAA-MM-DD&pessoas=N`. Cancelamento, remarcação e
chegada/no-show usam as ações da seção 5 do contrato. A conversa funciona por `POST /api/mensagens`; ofertas de espera, confirmação,
aprovação/recusa e campanhas usam uma caixa de saída simulada (`GET /api/saida`).
Execute `POST /api/tarefas/rodar` para gerar confirmações, aniversários e convites
de retorno devidos. Estado da conversa e histórico persistem no banco.
Abra `http://127.0.0.1:8080/` para conversar ou `/equipe` para operar com o token.
Evolution e Telegram usam exclusivamente as variáveis de ambiente documentadas;
sem configuração, os envios são simulados. A equipe pode rodar tarefas na página.
O sistema não cobra sinal/Pix: qualquer política para grupos deve constar no FAQ.

## Deploy na VPS

A entrega usa a imagem oficial Python, sem instalar pacotes. No servidor com
Docker e Compose instalados:

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

O volume `./dados:/dados` preserva SQLite e configuração; `./backups:/backups`
recebe as cópias. A porta fica publicada em `127.0.0.1:8080:8080`. Configure o
proxy reverso da VPS (Nginx ou Caddy) com certificado HTTPS para seu domínio,
encaminhando para `http://127.0.0.1:8080`. Preserve os headers dos webhooks.
Ajuste o fuso do container para o horário local do restaurante (variável `TZ`
no ambiente do serviço, conforme a região). Não fixe `RESERVA_AGORA` na produção.

Evolution: preencha `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`
e `WEBHOOK_SEGREDO`. Configure na instância o evento `MESSAGES_UPSERT` e o destino
HTTPS do seu domínio com `/webhook/evolution/<segredo>`; `<segredo>` deve ser
exatamente `WEBHOOK_SEGREDO`.

Telegram: preencha `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
e `TELEGRAM_SEGREDO`. Pelo serviço do Telegram, registre `setWebhook` com o campo
`url` apontando ao endereço HTTPS `/webhook/telegram` e `secret_token` igual a
`TELEGRAM_SEGREDO`. Adicione o bot ao grupo configurado. As respostas aos atendimentos
e os comandos `/fila`, `/reservas`, `/responder`, `/encerrar`, `/aprovar` e `/recusar`
operam a mesma base da página da equipe. Essas configurações externas são feitas
pelo operador; nenhum serviço real foi chamado durante a implementação.

Backup diário: adapte `/caminho/reserva-restaurante` no cron do host:

```cron
15 3 * * * cd /caminho/reserva-restaurante && docker compose exec -T reserva ./reserva backup --dados /dados --saida /backups/diario-$(date +\%F).zip
```

Copie os backups para armazenamento seguro fora da VPS e aplique retenção.
Para restaurar, primeiro pare o serviço; depois use um container temporário:

```sh
docker compose stop reserva
docker compose run --rm --no-deps reserva ./reserva restaurar --dados /dados --entrada /backups/diario-AAAA-MM-DD.zip
docker compose up -d reserva
```

Confirmações, aniversários, reativação e reenvios dependem de `POST /api/tarefas/rodar`.
Além do botão na equipe, o operador pode agendar essa rota em localhost com header
`X-Token`, por exemplo a cada cinco minutos; ela é idempotente. Proteja o token no
agendador e não o exponha em logs. Nenhum deploy foi executado durante a construção: o deploy na VPS é do dono.

## Backup e indicadores

`./reserva backup --dados ./dados --saida copia.bak` cria um arquivo ZIP com
configuração e cópia consistente do SQLite, mesmo com o servidor ligado.
Pare o servidor antes de `./reserva restaurar --dados ./dados --entrada copia.bak`.
A restauração substitui banco e configuração. Guarde o backup com acesso restrito:
ele contém os dados pessoais existentes no momento da cópia.

`GET /api/raiox?mes=AAAA-MM` calcula os indicadores mensais para a equipe.
`./reserva raiox --dados ./dados --mes AAAA-MM --acompanhamento painel.json`
atualiza o mês no acompanhamento existente, preservando as medidas herdadas
do mês anterior (ou da base). Bloqueios são gerenciados em `/api/bloqueios`;
a exclusão em `/api/clientes/{id}` anonimiza e cancela reservas futuras
pelo fluxo normal de oferta à lista de espera.
