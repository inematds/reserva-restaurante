# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|

- 2026-10-19 13:50 -0300 · Cadastros em tabela SQLite com ordem autoincremental e JSON por item; marcador de semente independente de tabelas vazias. Cada operação usa conexão própria e BEGIN IMMEDIATE; motor de reservas deverá validar e inserir na mesma transação. HTTP com biblioteca padrão e autenticação central antes do corpo.

- 2026-10-19 13:54 -0300 · Clientes e reservas reutilizam armazenamento de documentos SQLite ordenados por criação, com ids UUID. Booking concentra validação/alocação e todas as mutações ocorrem sob BEGIN IMMEDIATE, incluindo remarcação e atualização das visitas. Horários consultam o mesmo alocador das reservas.

- 2026-10-19 13:59 -0300: conversa e efeitos locais ficam na mesma transação SQLite do alocador. Histórico separado da caixa de saída: resposta do bot não substitui pendência de confirmação/espera. Cancelamento compartilhado oferece espera; recusa de grupo não oferece. Transporte externo fica para próximo ciclo.

- 2026-10-19 14:04 -0300 · Backup ZIP contém snapshot obtido por sqlite3.Connection.backup e restaurante.json; restauração com servidor parado. LGPD vincula histórico apagado ao id do cliente e desvincula o telefone; cancela espera própria antes de liberar mesas. Raio-X compartilhado HTTP/CLI calcula visitas pelo início da reserva e mescla sobre último mês anterior/base.

- 2026-10-19 14:09 -0300 · Transportes stdlib com timeout de 3 s e URLs exclusivamente do ambiente. Reenvio considera pendentes anteriores à rodada para não mascarar falha recém-ocorrida. Vínculos Telegram e deduplicação Evolution persistem no SQLite; operações Telegram reutilizam handlers sem aninhar transações.

- 2026-10-19 14:15 -0300 · Interface operacional em HTML/CSS/JS locais, sem dependências: superfície clara com contraste verde, títulos serifados, tabelas com rolagem contida e controles rotulados. Token só em memória, conteúdo via textContent, recursos em allowlist e CSP same-origin. Escopo congelado prevalece sobre documentos adicionais sugeridos por skill de design.
- 2026-10-19 14:15 -0300 · Docker copia somente runtime e exemplo; volume bind para dados e backups, porta publicada em localhost. Build real delegado ao portão humano de nível 4 para não baixar imagem neste ciclo sem rede externa. Histórico usa cliente_id; confirmações da reserva remarcada ficam obsoletas e não são reenviadas.
