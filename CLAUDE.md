# CLAUDE.md — reserva-restaurante

Sistema de reserva de mesa para um restaurante: salões/mesas, turnos, alocação automática, confirmação, no-show, lista de espera, grupo grande com aprovação, FAQ, fila humana, base própria de clientes (aniversário, reativação, campanhas com consentimento) e exportação para o Painel do Raio-X de Margem (pacote `restaurante`).

- Repo local (sem remoto ainda). Autor de commit: `inematds <inematds@gmail.com>` (config local).
- **Contrato:** `docs/ESPECIFICACAO.md`. Testes caixa-preta em `tests/` (pytest sobe `./reserva serve --porta 0`). Contrato e testes são **protegidos** durante a execução longa — só humano altera, e aí recongela o hash no `goal.md`.
- Decisões: `docs/DECISOES-ABERTAS.md`. Relação com o Raio-X: `docs/MAPA-RAIO-X.md`.
- Execução longa: `longrun/2026-10-05-reservas-v1/` (método em `~/projetos/execucao-longa`). Como rodar: `README.md`.
- Molde: `~/projetos/atende-clinica` (mesma pilha, mesmos canais, mesmo conftest).
- `python3` (não existe `python` neste host). Sem dependência externa no v1.
- Nenhuma API (WhatsApp/Meta, LLM pago, Pix/PSP, OpenRouter, Groq) sem autorização explícita. Sem rede externa no código; integrações só por variáveis de ambiente.
- Servidor de teste: só `127.0.0.1`, porta 0; matar só o PID que subiu (nunca `pkill -f`).
- Versão em `VERSION` (semver do CLAUDE global: minor carrega o patch).

## Self-learning

When I correct you, or you catch yourself making a mistake: before continuing, add the lesson as a one-line rule under ## Lessons, so it never happens again.

## Lessons
