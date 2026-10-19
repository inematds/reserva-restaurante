# Plano

## Estratégia atual
Base, clientes e motor de horários/reservas implementados e verificados. Reutilizar o alocador transacional em todos os canais. A consulta de dados do cliente ainda não tem histórico; acrescentá-lo junto com a conversa.

## Próximos 3 passos
1. Conversa persistente por telefone: normalização/FAQ, histórico entrada/saída, fluxo nome/pessoas/dia/horário, consulta/cancelamento e fila humana; garantir PARAR e precedência das intenções.
2. Caixa de saída, confirmação e lista de espera: tarefas idempotentes, resposta à pendência, ofertas na mesma data/turno após cancelamento, remarcação renovando confirmação; aprovação/recusa e base própria (aniversário/reativação/campanhas).
3. Bloqueios e backup → LGPD/Raio-X → Evolution/Telegram usando apenas servidor falso → Docker/README → páginas. Rodar suíte completa e verificar limites a cada ciclo; manter contratos congelados.
