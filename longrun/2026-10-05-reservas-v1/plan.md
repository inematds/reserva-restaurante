# Plano

## Estratégia atual
Conversa e automações locais implementadas; 68/93 testes passam. Completar operações locais antes dos transportes externos. Reutilizar cancelamento e saída compartilhados.

## Próximos 3 passos
1. Bloqueios e backup/restauração; depois exclusão LGPD (cancelamento normal, ofertas, anonimização de mensagens e estado) e Raio-X HTTP/CLI.
2. Evolution e Telegram exclusivamente pelos ambientes da spec e servidores falsos: envio/retry, webhooks, deduplicação, fila humana e avisos. Rever invalidação de pendências na remarcação.
3. Docker/Compose/.env.exemplo e README operacional, depois páginas em web/. Rodar suíte completa e limites; concluir apenas com 93 passed e LIMITES OK.
