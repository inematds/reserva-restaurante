# Estado — atualizado 2026-10-19 13:59 -0300

## Funciona
- v0.4.0: base HTTP/SQLite/auth/relógio, cadastros, clientes, horários/alocação e reservas mantidos sem regressão na suíte.
- Conversa persistente por telefone: nome/pessoas/dia/horário, datas relativas, opções inválidas, consulta e cancelamento ordenado, FAQ imediato, grupo grande e entrada na lista de espera.
- Histórico de entrada/saída inclui mensagens anteriores ao cadastro. PARAR persiste; fila humana abre por pedido ou segunda incompreensão, silencia o bot e permite responder/encerrar pela API local.
- Caixa de saída simulada persistente; confirmação idempotente e resposta 1/2; remarcação renova confirmação; cancelamento compartilhado pela API/chat oferece espera ao primeiro elegível, com nova alocação ao aceitar.
- Aprovação/recusa de grupo grande, aniversário anual, reativação por última visita e campanhas com consentimento.
- Suíte completa: **68 passed / 25 failed** em 65,24 s. Todas as suítes de conversa, confirmação/espera e grupo/base própria passam. Log: `pytest-ciclo-3.log`.
- Checagem local adicional: CONVERSA PERSISTENTE E HISTÓRICO OK (reabertura do banco no passo nome, histórico anterior ao cadastro e silêncio durante atendimento).
- Verificador: **LIMITES OK**, hash a177d907bfc8ce90, 93 testes, escopo preservado. Nenhuma API real/rede externa; nenhum commit.

## Falta
- Rotas de bloqueios e comandos de backup/restauração.
- Exclusão/anonimização LGPD e Raio-X HTTP/CLI; consulta de dados já inclui histórico.
- Evolution e Telegram, reenvio real de pendentes e notificações à equipe; hoje toda saída é simulada e reenviadas = 0.
- Docker, Compose, .env.exemplo, páginas web e finalização das instruções operacionais do README.
- Rever pendências antigas de confirmação após remarcação antes de disparar nova confirmação; verificar vínculo do histórico quando telefone é editado e futura anonimização. Não são cobertos pela suíte atual.
- Não marcar concluído: restam 25 testes e partes do contrato.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec inteira, conftest e fixture lidos neste ciclo.
2. `Application` herda `Conversation` e `Booking`; `src/conversation.py` concentra conversa, saída, tarefas, fila humana e espera. `Store.transaction()` protege cada operação completa.
3. `cancel(db, reservation)` é o caminho compartilhado para cancelamento e oferta de espera; usar também na exclusão LGPD. `output()` grava caixa de saída e histórico; integrar envio por ambiente nesse ponto.
4. Estado em cadastros por tipo: conversas (id = telefone), mensagens, saida, humano, espera. Tarefas guardam marcadores nas reservas/clientes. Histórico é associado por telefone; anonimização precisa apagar textos e desvincular estado antigo.
5. Rodar `python3 -m pytest -q tests/` com saída em arquivo e ler apenas `tail -n 30`; executar `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh`.
