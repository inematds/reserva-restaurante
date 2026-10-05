# Plano (reescrever, não acumular)

## Estratégia atual
Nada implementado ainda. Implementar `./reserva` (Python 3, só biblioteca padrão; código em `src/`, páginas em `web/`) contra `docs/ESPECIFICACAO.md`, na ordem em que os testes se encadeiam: base → horários/alocação → reservas → conversa → confirmação/espera → grupo grande e base própria → cadastros/bloqueios/backup → LGPD/Raio-X → Evolution → Telegram → Docker/README → páginas. Rodar `python3 -m pytest -q tests/` a cada passo (ler só o fim da saída).

## Próximos passos
1. Base: `./reserva serve --porta 0 --dados DIR` imprimindo `PORTA=<n>`, SQLite em `DIR`, cópia de `exemplos/restaurante.json`, `RESERVA_AGORA`, token `X-Token`, `/api/saude`, `/api/saloes`, `/api/turnos` (→ `test_basico.py`).
2. Horários e alocação (seção 3): duração por grupo, grade por turno, feriado/antecedência/janela, menor `max` + ordem, combinação com `min/max`, limite da cozinha, `GET /api/horarios`, `POST /api/reservas` com 201/409/422/404 e transação para a concorrência (→ `test_horarios.py`, `test_reservas.py`).
3. Conversa (seção 6) com estado persistido por telefone, depois confirmação/espera (seções 7–8).
