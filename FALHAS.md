# FALHAS

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-10-05 | validação: `Servidor` subido fora de `try/finally` em 5 testes (`test_estado_persiste_ao_reiniciar`, `test_confirmacao_sobrevive_a_reinicio`, `test_reativacao_apos_60_dias_uma_por_visita`, `test_semente_so_na_primeira_vez`, `test_backup_e_restaurar`, `montar_mes`) — asserção falhando antes do `parar()` deixava `reserva serve` órfão (aconteceu 14 h no atende-clinica) | `conftest.py`: lista `SERVIDORES` + fixture `autouse` que para todos no teardown | infra |
| 2026-10-05 | validação: contradição spec × teste — §14 e `test_mesa_nova_validacoes` diziam 422 para `POST /api/mesas` com salão inexistente, mas a regra geral da §5 (commit `fc103f3`) manda 404 para id inexistente no corpo; implementador honesto falharia o teste | unificar para 404 (linha 15 do teste + 2 células da tabela §14) | prompt |
| 2026-10-05 | validação: spec §1 não dizia que `--dados DIR` é criado se faltar; o `verificar-independente.py` faz `docker run` sem volume em `/dados` → container cairia e `INDEPENDENTE OK` nunca sairia | frase em §1 ("cria DIR se não existir") e §19 (sobe sem volume; healthcheck via `python3 -c`) | prompt |
| 2026-10-05 | validação: §4 não dizia que o 401 precede 404/409/422 (`test_rotas_da_equipe_exigem_token` manda `{}` sem token e espera 401) | frase em §4 | prompt |
| 2026-10-05 | validação: §6.5 não fixava a ordem da lista "minha reserva" (teste espera ordem de `inicio` e o número escolhido depende dela) | "em ordem de `inicio`" em §6.5 | prompt |
| 2026-10-05 | validação: §6.4 "última mensagem de saída" ambígua — §11 chama de `saida` também as respostas do bot; lida assim, qualquer FAQ apagaria a pendência de confirmação | "última mensagem da caixa de saída (`/api/saida`)" em §6.4 | prompt |
| 2026-10-05 | validação: §5 `remarcar` dizia que as mesas da própria reserva contam como livres, mas não que as `pessoas` dela saem da soma do limite da cozinha | frase na linha de `remarcar` | prompt |
| 2026-10-05 | validação: §14 turnos — "sobreposição" sem regra de ponta; `test_turno_novo_e_validacoes` espera que `[11:30,15:00)` e `[15:00,17:00)` não se sobreponham | referência à regra semiaberta da §3 | prompt |
| 2026-10-05 | validação: `test_env_exemplo` exige `"http" not in` o arquivo inteiro e a §19 só dizia "nenhuma URL real" (um comentário `# ex.: http://...` derrubaria o teste); o exemplo `http://evolution:8080` da §17 copiado para o código cai no grep do `verificar-limites.sh` | frases em §17 e §19 | prompt |
| 2026-10-05 | validação: conftest só decodifica JSON em 2xx quando `Content-Type` contém `json`; a spec não exigia o header | frase no topo da §5 | prompt |
| 2026-10-05 | validação: `test_dados_e_exclusao` espera `GET .../dados` 200 anonimizado após `DELETE`; §5/§11 só diziam "204; anonimiza" | frase na linha do `DELETE` | prompt |
| 2026-10-05 | validação: §10 não dizia que a data de um `chegou` é o `inicio` da reserva (não o momento da marcação) para coorte e retorno | frase em §10 | prompt |
| 2026-10-05 | validação: §6 fluxo — `test_reserva_cliente_conhecido` exige que a resposta ao cliente conhecido não contenha `nome`; spec só dizia o caso do desconhecido | frase em §6 | prompt |
