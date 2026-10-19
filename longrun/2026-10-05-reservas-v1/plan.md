# Plano

## Estratégia atual
Base e cadastros persistentes implementados. Próximo incremento deve habilitar reservas reais, usando regras e transações compartilhadas entre horários, reserva e posteriormente chat. Não adicionar respostas fictícias para rotas pendentes.

## Próximos 3 passos
1. Clientes: normalização/deduplicação de telefone, validação de origem/aniversário, consulta/edição; criar tabelas próprias no SQLite.
2. Horários/alocação e reservas: grade, duração, antecedência/janela/feriados, menor capacidade e ordem, combinações, cozinha e transação atômica; listagem, cancelamento, remarcação, chegada e ocupação. Rodar suíte completa.
3. Conversa persistida com FAQ/fila humana e fluxo de reserva; confirmação e espera com caixa de saída simulada. Depois seguir grupos/base própria → bloqueios/backup → LGPD/Raio-X → integrações falsas → Docker/README → páginas.
