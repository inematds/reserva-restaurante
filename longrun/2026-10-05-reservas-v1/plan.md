# Plano

## Estratégia atual
Operações locais implementadas e verificadas; 74/93 testes passam. Próximo ciclo deve implementar transportes por ambiente e testar somente com servidor falso.

## Próximos 3 passos
1. Evolution: webhook com segredo/deduplicação, origem whatsapp, envio de respostas e saída, retry de pendentes; revisar pendência de confirmação após remarcação.
2. Telegram: abertura/repasse da fila humana, replies/comandos, proteção do webhook e avisos de reservas/grupos/cancelamentos; rodar suíte completa.
3. Docker/Compose/.env.exemplo, README operacional e páginas web; testar suíte e limites, concluir apenas com 93 passed e LIMITES OK.
