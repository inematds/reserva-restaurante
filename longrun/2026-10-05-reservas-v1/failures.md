# Falhas (só acrescentar; ao fim, a menor correção vira linha no FALHAS.md do projeto)

| data | o que quebrou | tentativa | resultado | prompt \| infra |
|---|---|---|---|---|
| 2026-10-19 13:50 -0300 | Suíte: 87 falhas em funcionalidades ainda ausentes | Implementada e verificada a base e cadastros | 6 passed / 87 failed; seguir clientes/horários/reservas; nenhum conflito com spec identificado | implementação parcial |

| 2026-10-19 13:54 -0300 | 55 testes ainda falham em funcionalidades ausentes (conversa/saída, bloqueios/backup, LGPD/Raio-X, canais, páginas e Docker) | Implementados clientes e motor de reservas; suíte completa executada | 38 passed / 55 failed; nenhum conflito teste/spec identificado | implementação parcial |

| 2026-10-19 13:59 -0300 | 25 testes falham em partes ausentes (bloqueios/backup, LGPD/Raio-X, canais, páginas e Docker) | Implementadas conversa e automações locais; executada suíte completa | 68 passed / 25 failed; nenhum conflito teste/spec identificado | implementação parcial |

| 2026-10-19 14:04 -0300 | 19 testes ainda falham em integrações, Docker e páginas ausentes | Implementadas operações locais e rodada suíte completa | 74 passed / 19 failed; nenhum conflito teste/spec identificado | implementação parcial |

| 2026-10-19 14:09 -0300 | 4 testes falham por páginas, Dockerfile, Compose e .env.exemplo ausentes | Implementadas integrações e rodada suíte completa | 89 passed / 4 failed; nenhum conflito teste/spec identificado | implementação parcial |
