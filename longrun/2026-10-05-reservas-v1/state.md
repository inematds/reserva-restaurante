# Estado — atualizado 2026-10-19 13:50 -0300

## Funciona
- Base v0.2.0: `./reserva serve --porta 0 --dados DIR`, stdout `PORTA=<n>`, host padrão local, criação da pasta/JSON e SQLite persistente.
- Relógio central `Application.now()` respeita RESERVA_AGORA; sem variável usa hora local.
- Autenticação de rotas da equipe antes de interpretar JSON; respostas JSON UTF-8 com status e tamanho.
- Saúde e versão, salões públicos, turnos ativos públicos; CRUD de mesas/turnos/FAQ com ordem persistida, validação e semente única.
- Suíte inteira: **6 passed / 87 failed** (13,01 s), log em `pytest-ciclo-1.log`. `verificar-limites.sh`: **LIMITES OK**, hash a177d907bfc8ce90, 93 testes.
- Verificação local complementar: diretório inexistente, relógio fixo, JSON inválido com/sem token, recarga do JSON e FAQ vazio sem ressemeadura → BASE OK.

## Falta
- Clientes, horários/alocação, reservas e ocupação; conversa e histórico; confirmação/espera; grupos grandes e base própria; bloqueios/backup; LGPD/Raio-X; Evolution/Telegram; Docker e páginas.
- README preservado e atualizado com execução local e seção de deploy explicitamente pendente. Completar instruções operacionais quando os respectivos comandos existirem.
- Ainda não há `web/`, Dockerfile, compose ou .env.exemplo. Não marcar concluído: suíte incompleta.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e conftest/fixture foram lidos integralmente neste ciclo.
2. Continuar em `src/storage.py` (transações BEGIN IMMEDIATE), `src/server.py` (HTTP/cadastros) e `src/cli.py`.
3. Implementar clientes e motor de horários/reservas, preservando autenticação e cadastros.

```sh
python3 -m pytest -q tests/ > longrun/2026-10-05-reservas-v1/pytest-proximo.log 2>&1
tail -n 30 longrun/2026-10-05-reservas-v1/pytest-proximo.log
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh
```
Nenhum commit neste ciclo; o loop externo é responsável.
