# Estado — atualizado 2026-10-05 (plano entregue; execução não iniciada)

## Funciona
- Nada implementado. Contrato (`docs/ESPECIFICACAO.md`), 93 testes caixa-preta, fixture, exemplo e esta pasta estão prontos. `python3 -m pytest -q --collect-only` → 93 coletados; `python3 -m pytest -q` → 0 passed (falta `./reserva`).

## Falta
- Tudo da seção "Próximos passos" do `plan.md`: `./reserva`, `src/`, `web/`, `Dockerfile`, `docker-compose.yml`, `.env.exemplo`, `.dockerignore`, README da implementação (seção 19), `VERSION` bump.
- Humano: responder `docs/DECISOES-ABERTAS.md`, commitar e rodar `congelar.sh` antes de iniciar o loop/goal.

## Como retomar (comandos exatos)
```
cd /home/nmaldaner/projetos/reserva-restaurante
python3 -m pytest -q tests/ 2>&1 | tail -n 30
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh
```

Ao retomar/após compactação: ler goal.md → state.md → plan.md → canal.md → fim de progress.md e failures.md.
