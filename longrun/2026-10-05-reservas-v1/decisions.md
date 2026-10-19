# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|

- 2026-10-19 13:50 -0300 · Cadastros em tabela SQLite com ordem autoincremental e JSON por item; marcador de semente independente de tabelas vazias. Cada operação usa conexão própria e BEGIN IMMEDIATE; motor de reservas deverá validar e inserir na mesma transação. HTTP com biblioteca padrão e autenticação central antes do corpo.

- 2026-10-19 13:54 -0300 · Clientes e reservas reutilizam armazenamento de documentos SQLite ordenados por criação, com ids UUID. Booking concentra validação/alocação e todas as mutações ocorrem sob BEGIN IMMEDIATE, incluindo remarcação e atualização das visitas. Horários consultam o mesmo alocador das reservas.
