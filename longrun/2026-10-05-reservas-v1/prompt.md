Você está num ciclo de uma execução longa no repo /home/nmaldaner/projetos/reserva-restaurante.

RESULTADO: `./reserva` (Python 3, só biblioteca padrão; código em `src/` e páginas em `web/`) implementa docs/ESPECIFICACAO.md por inteiro — reserva de mesa para um restaurante com WhatsApp (Evolution), equipe no Telegram e em /equipe, base própria de clientes, cadastros, backup, Raio-X e Docker.

ANTES DE AGIR: leia longrun/2026-10-05-reservas-v1/goal.md → state.md → plan.md → canal.md → últimas linhas de progress.md e failures.md. Na primeira vez, leia docs/ESPECIFICACAO.md inteiro, tests/conftest.py e tests/fixtures/restaurante.json.

NESTE CICLO: escolha a próxima ação útil (comece pela base: `./reserva serve` imprimindo `PORTA=<n>`, SQLite em --dados, auth, relógio RESERVA_AGORA; depois horários/alocação → reservas → conversa → confirmação/espera → grupo grande e base própria → cadastros/bloqueios/backup → LGPD/raiox → Evolution → Telegram → Docker/README → páginas), implemente, rode `python3 -m pytest -q tests/` (leva até ~1 min). Leia só o fim da saída (`| tail -n 30`); saída longa vai para arquivo.

AO TERMINAR O CICLO (obrigatório):
- reescreva state.md (Funciona / Falta / Como retomar) e plan.md (próximos 3 passos);
- acrescente 1 linha em progress.md: data-hora, o que mudou, resultado do pytest (N passed / N failed);
- se algo deu errado, 1 linha em failures.md: erro → tentativa → resultado;
- decisões de design em decisions.md; fatos e armadilhas novos em canal.md (só acrescentar);
- quando `python3 -m pytest -q tests/` passar inteiro E `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` imprimir LIMITES OK, escreva "concluído" na primeira linha de "## Funciona" do state.md.

SE UM TESTE CONTRADIZ A ESPECIFICAÇÃO: não altere o teste nem a spec. Registre em failures.md (teste, trecho da spec, o conflito) e siga com os outros itens; isso é portão humano.

INTEGRAÇÕES: Evolution e Telegram só pelas variáveis de ambiente da spec; teste só contra o servidor falso dos testes. Nunca chame api.telegram.org nem uma Evolution real, nunca escreva URL externa no código. `.env.exemplo` com valores vazios.

RESTRIÇÕES: não altere tests/, pytest.ini, docs/, goal.md, hash-congelado.txt, congelar.sh, verificar-*, loop.env, prompt.md. Só biblioteca padrão do Python 3 (`python3`, não `python`). Nenhuma API, nenhuma rede externa, nenhuma chave. Servidor só em 127.0.0.1 (o `0.0.0.0` existe só no CMD do Dockerfile). Não use `pkill -f`; mate só o PID que você subiu. Não copie valores da fixture (nomes, telefones, datas, ids de mesa) para o código: a lógica tem que valer para qualquer restaurante.json. Não faça commit (o loop externo faz).
