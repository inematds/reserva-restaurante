# Estado — atualizado 2026-10-19 (verificação independente, Claude)

## Funciona
concluído

- v0.7.0: base HTTP/SQLite/auth/relógio, cadastros, clientes, horários/alocação, reservas, conversa persistente, confirmação/espera, grupos, campanhas, bloqueios, backup/restauração, LGPD, Raio-X e integrações Evolution/Telegram por ambiente.
- Chat em `/` e equipe em `/equipe`, arquivos locais em web/. Equipe tem filtros, reservas/ações, ocupação, espera, clientes/histórico, mesas, turnos, FAQ, bloqueios, fila humana, saída, campanhas, tarefas e Raio-X. Token apenas em memória; saída limpa o painel. Conteúdo remoto renderizado com textContent.
- Dockerfile com healthcheck stdlib, Compose com dados/backups persistentes e porta localhost, .env.exemplo inteiramente vazio. README preservado e complementado com execução, Deploy na VPS, webhooks, backup e restauração.
- Histórico vinculado por cliente_id preserva troca de telefone sem vazar para novo titular. Remarcação invalida confirmação anterior e impede seu reenvio; nova confirmação continua devida.
- Suíte final: **93 passed / 0 failed**, 18,17 s, `pytest-ciclo-6.log`.
- **LIMITES OK**: hash a177d907bfc8ce90, 93 testes, escopo preservado. Nenhum teste/spec/verificador alterado, nenhuma API real/rede externa ou commit.
- Navegador Chromium local: chat, login, dados, criação de mesa, logout e mobile 390 px sem overflow; nenhum erro JS. Detector da interface sem apontamentos. Regressão local adicional de troca/reuso de telefone, LGPD e confirmação antiga/nova: OK.

## Falta
- ~~Portão nível 4~~ FEITO 2026-10-19 (Claude, verificação independente): 93 passed, LIMITES OK, `verificar-independente.py` → INDEPENDENTE OK com `docker build` real + healthcheck do container (imagem `reserva-restaurante-verif`, 148 MB). Dockerfile, docker-compose.yml, .env.exemplo (8 variáveis vazias) e README "Deploy na VPS" conferidos contra a seção 19. Nenhum código alterado; VERSION fica 0.7.0.
- Humano: abrir `/` e `/equipe` no navegador (opcional; o ciclo 6 já testou em Chromium headless), criar remoto/push e deploy na VPS com credenciais reais.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec inteira, conftest e fixture já foram lidos neste ciclo.
2. Critérios do ciclo estão atendidos; não reabrir implementação sem nova evidência. Próximo passo é validação independente humana, sem alterar testes/contrato.
3. Application herda Integrations, Operations, Conversation e Booking. Handler serve somente cinco caminhos fixos em web/; não há servidor genérico de arquivos.
4. Artefatos temporários desta verificação: /tmp/reserva-browser.cjs, /tmp/reserva-regressao.py e screenshots /tmp/reserva-*.png. Servidores de teste foram encerrados pelo PID criado.
5. O loop externo faz o commit; não foi feito commit neste ciclo.
