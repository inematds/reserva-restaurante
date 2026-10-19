# Estado — atualizado 2026-10-19 14:09 -0300

## Funciona
- v0.6.0: base HTTP/SQLite/auth/relógio, cadastros, clientes, horários/alocação, reservas, conversa persistente, confirmação/espera, grupos e campanhas.
- Bloqueios, backup/restauração, anonimização LGPD e Raio-X HTTP/CLI continuam passando.
- Evolution por ambiente: segredo antes do corpo, webhook com deduplicação persistente, texto simples/estendido, origem whatsapp, respostas em ordem e saída enviado/pendente/simulado. Tarefas reenviam pendentes anteriores e respeitam nao_contatar.
- Telegram por ambiente: abertura/repasse com vínculo persistido dos message_ids, replies, responder/encerrar/fila/reservas/aprovar/recusar, proteção por segredo e grupo; avisos de reservas/grupos/cancelamentos.
- Suíte completa: **89 passed / 4 failed** em 18,11 s, log `pytest-ciclo-5.log`; todos os testes de integrações passam, sem regressão observada.
- Verificador: **LIMITES OK**, hash a177d907bfc8ce90, 93 testes, escopo preservado. Testes só contra falso local, sem API real/rede externa nem commit.

## Falta
- Dockerfile, docker-compose.yml e .env.exemplo (3 testes); páginas web em web/ (1 teste), README com Deploy na VPS conforme seção 19.
- Rever pendências antigas de confirmação após remarcação e vínculo do histórico ao editar telefone (fora da cobertura atual).
- Não marcar concluído: restam quatro testes e partes do contrato.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec inteira, conftest e fixture foram lidos neste ciclo.
2. Application herda Integrations, Operations, Conversation e Booking. Novo src/integrations.py concentra transportes/webhooks; Handler valida segredo antes de ler JSON.
3. Saídas tentam envio sincronamente com timeout de 3 s. Retry acontece antes de gerar novas mensagens; falha nova fica pendente até a próxima rodada. Env ausente não dispara rede.
4. Telegram usa métodos das mesmas rotas da equipe, fora de transações aninhadas. Avisos de criação ficam após insert; cancelamentos de conversa avisam separadamente do helper genérico.
5. Implementar entrega Docker e páginas reais, preservando README existente. Rodar suíte completa para arquivo, ler tail -n 30 e executar verificar-limites.sh. Não fazer commit.
