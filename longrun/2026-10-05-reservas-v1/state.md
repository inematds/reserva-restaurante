# Estado — atualizado 2026-10-19 13:54 -0300

## Funciona
- v0.3.0: base HTTP/SQLite/auth/relógio e cadastros persistentes de mesas, turnos e FAQ mantidos.
- Clientes: cadastro, telefone normalizado e deduplicado, busca sem acento/caixa ou por telefone, edição, origem validada, aniversário e consulta dos dados cadastrais/reservas.
- Horários: grade por turno/duração, feriados, antecedência, janela inclusiva, salão, menor mesa e desempate por ordem, combinações como segunda opção e limite da cozinha.
- Reservas: criação/listagem/filtros, cancelamento com liberação, remarcação atômica excluindo a própria ocupação, chegada/no-show, visitas e ocupação por horário. Grupo grande nasce pendente.
- Concorrência e persistência verificadas pela suíte: dez pedidos pela mesma mesa dão um 201 e nove 409; reiniciar mantém reservas e conflitos.
- Suíte completa neste ciclo: **38 passed / 55 failed** em 30,81 s. Todos os testes de test_horarios.py e test_reservas.py passaram. Log: `pytest-ciclo-2.log`.
- Verificador: **LIMITES OK**, hash a177d907bfc8ce90, 93 testes, escopo preservado. Nenhuma API real ou rede externa utilizada; nenhum commit.

## Falta
- Conversa e histórico (o campo mensagens da consulta de dados ainda está vazio), FAQ no chat e fila humana.
- Confirmação/espera e caixa de saída; o cancelamento libera mesas, mas ainda não oferece espera. Remarcação precisa integrar o marcador de confirmação ao futuro mecanismo de saída.
- Aprovação/recusa de grupos e notificações; tarefas de aniversário/reativação/campanhas.
- Rotas de bloqueios (o alocador já considera registros de bloqueio, ainda não criáveis pela API), backup/restauração, LGPD e Raio-X.
- Evolution/Telegram contra servidores falsos, Docker/.env.exemplo, páginas web e instruções operacionais finais do README.
- Não marcar concluído: faltam 55 testes e o restante do contrato.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec inteira, conftest e fixture lidos neste ciclo.
2. `src/booking.py` concentra regras de clientes, grade e alocação; `Application` em `src/server.py` herda `Booking`. Query string já chega separada ao dispatch.
3. Usar a mesma transação `Store.transaction()` para alocar e gravar; nunca consultar disponibilidade fora da transação para depois inserir. Estado em `cadastros`, discriminado por tipo, ordem global de criação e ids UUID.
4. Implementar conversa/histórico e saída persistentes antes dos canais externos; integrar espera ao caminho compartilhado de cancelamento.

```sh
python3 -m pytest -q tests/ > longrun/2026-10-05-reservas-v1/pytest-proximo.log 2>&1
tail -n 30 longrun/2026-10-05-reservas-v1/pytest-proximo.log
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh
```
