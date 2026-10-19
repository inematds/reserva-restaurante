# Canal — reservas-v1 (só acrescentar; nunca reescrever)

Conhecimento do projeto que a compactação perde: fatos descobertos, aprendizados, glossário, armadilhas, onde estão as coisas.
Não é estado da tarefa (isso vai em state/plan/progress). Preencha cedo — o hook avisa na faixa 1 (~50% do contexto).

Formato: `- AAAA-MM-DD HH:MM · fato|aprendizado|glossário|armadilha · texto`


- 2026-10-19 13:50 -0300 · fato · Spec inteira, conftest e fixture lidos. Base criada; 6/93 testes passam. Não há clientes nem reservas ainda.
- 2026-10-19 13:50 -0300 · armadilha · Semente única deve usar marcador persistente: esvaziar FAQ não autoriza importar a lista do JSON outra vez. Config geral é recarregada a cada início.
- 2026-10-19 13:50 -0300 · fato · Testes locais de HTTP e servidor falso funcionam neste ambiente; nenhuma rede externa foi chamada. Logs longos ficam nesta pasta; ler apenas últimas 30 linhas.

- 2026-10-19 13:54 -0300 · fato · Todos os testes de horários/reservas passam; total 38/93. O servidor agora repassa query string ao dispatch. Booking/APIError ficam em src/booking.py, evitando import circular.
- 2026-10-19 13:54 -0300 · armadilha · Cancelamento ainda não dispara espera e dados do cliente ainda não incluem mensagens; integrar esses efeitos antes de considerar as rotas completas. Alocador já lê bloqueios do armazenamento, mas ainda falta API de bloqueios. No-show continua ativo; remarcação ignora a própria reserva em mesas e cozinha.

- 2026-10-19 13:59 -0300 · fato · Conversa/confirmação/espera/grupo/base própria passam integralmente; total 68/93. Conversation é mixin de Application, com saída simulada e histórico por telefone. Store suporta novos tipos sem migração.
- 2026-10-19 13:59 -0300 · armadilha · Testes de integrações aguardam avisos ausentes e levam a suíte a 65 s. Ainda não há transporte: reenviadas=0. Fila humana local silencia bot; mensagens recebidas ficam no histórico, mas repasse Telegram falta. LGPD deve limpar conversas e textos antigos além de cancelar pelo helper cancel().

- 2026-10-19 14:04 -0300 · fato · Operações locais passam; total 74/93. Novo mixin Operations em src/operations.py. Backup é ZIP (SQLite + JSON), não arquivo SQLite puro. Históricos apagados usam cliente_id; comparar telefone=None misturaria clientes removidos. Checagem com dois clientes anonimizados passou. Faltam 15 testes de integrações, 3 Docker e 1 páginas.

- 2026-10-19 14:09 -0300 · fato · Integrações passam integralmente: 89/93 testes. src/integrations.py é mixin da Application; webhook_auth recebe headers no Handler. Telegram replies reconhecem abertura e repasses pelos message_ids persistidos. Restam 3 testes Docker e 1 páginas.
- 2026-10-19 14:09 -0300 · armadilha · Reenvio deve preceder criação de saídas na rodada (falha nova permanece pendente). Chamadas HTTP síncronas têm timeout de 3 s; não chamar handlers que abrem transação dentro de uma transação existente.

- 2026-10-19 14:15 -0300 · fato · Entrega v0.7.0 fecha os 93 testes e LIMITES OK. web/ contém chat/equipe/style e dois JS; servidor expõe allowlist de cinco caminhos. Docker/Compose/env/README concluídos, build real ainda é portão humano.
- 2026-10-19 14:15 -0300 · armadilha · Histórico pelo telefone sozinho perde dados ao editar e mistura titulares quando o número é reutilizado. Novas mensagens recebem cliente_id; cadastro reivindica apenas histórico sem dono; LGPD preserva mensagens de outro cliente. Remarcação marca confirmação anterior obsoleta/respondida e retry a ignora.
- 2026-10-19 14:15 -0300 · fato · Playwright disponível globalmente em /home/nmaldaner/.npm-global/lib/node_modules/playwright; Chromium local funcionou sem rede externa. Teste no navegador passou com 1360 px e 390 px, incluindo criação de mesa; detector sem apontamentos.
