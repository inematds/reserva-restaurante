# Estado — atualizado 2026-10-19 14:04 -0300

## Funciona
- v0.5.0: base HTTP/SQLite/auth/relógio, cadastros, clientes, horários/alocação, reservas e conversa persistente.
- Confirmação/espera, aprovação/recusa, aniversários, reativação, campanhas e fila humana local com saída simulada.
- Bloqueios de restaurante, salão e mesa, com conflitos sem cancelamento automático; DELETE libera disponibilidade.
- Backup CLI consistente via SQLite backup + configuração em ZIP; restauração com servidor parado.
- LGPD: anonimização preserva id e visitas, limpa textos/observações, cancela esperas próprias antes de oferecer vagas, cancela reservas futuras pelo caminho normal e remove estado do telefone antigo. Históricos anonimizados associados por cliente_id para não misturar clientes sem telefone.
- Raio-X HTTP/CLI: coorte da primeira visita, retorno em até 60 dias, presença/no-show e mesa-minutos; CLI mescla sobre mês anterior/base e substitui mês sem duplicar.
- Suíte completa: **74 passed / 19 failed** em 67,36 s; log `pytest-ciclo-4.log`. Nenhuma regressão observada. Checagem local adicional de dois históricos anonimizados isolados e telefone antigo desconhecido: OK.
- Verificador: **LIMITES OK**, hash a177d907bfc8ce90, 93 testes, escopo preservado. Sem API real/rede externa ou commit.

## Falta
- Evolution/Telegram, reenvio de pendentes, webhooks e avisos à equipe (15 testes de integrações ainda falham).
- Dockerfile, Compose e .env.exemplo (3 testes); páginas web (1 teste), finalizar README operacional.
- Rever pendências de confirmação após remarcação e vínculo do histórico ao editar telefone (fora da cobertura atual).
- Não marcar concluído: restam 19 testes e partes do contrato.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec inteira, conftest e fixture foram lidos neste ciclo.
2. `Application` herda Operations, Conversation e Booking. `src/operations.py` concentra bloqueios, anonimização e indicadores; CLI em `src/cli.py`.
3. `output()` deve integrar transporte por ambiente; `cancel()` já oferece espera. As operações estão sob Store.transaction(). Integrações só contra falso local dos testes.
4. Histórico atual por telefone; registros anonimizados recebem cliente_id. Não comparar telefone nulo na consulta de dados. Backup inclui banco e restaurante.json; restauração exige processo parado.
5. Rodar suíte completa com saída em arquivo e ler apenas tail -n 30; executar verificar-limites.sh. Não fazer commit.
