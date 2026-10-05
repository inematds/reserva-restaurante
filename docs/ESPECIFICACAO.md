# Especificação v1 — reserva-restaurante (contrato congelado)

> Este arquivo é **protegido** durante a execução longa: o agente implementa contra ele e não o altera.
> Os testes em `tests/` verificam exatamente o que está aqui. Mudança de contrato = humano edita, recongela o hash e reinicia o longrun.

## 0. O que é

Sistema de **reserva de mesa** para **um restaurante** com salão: salões e mesas com capacidade, turnos por dia da semana, grade de horários, alocação automática da menor mesa que serve, confirmação automática, no-show, lista de espera, aprovação humana de grupo grande, FAQ, passagem para humano, **base própria de clientes** com consentimento (aniversário e convite de retorno), página da equipe, exportação de números para o **Painel de Recuperação do Raio-X de Margem** (pacote `restaurante`).

Canais: **chat web**, **WhatsApp pela Evolution API** (seção 17) e caixa de saída **simulada** quando a Evolution não está configurada. Equipe interna atende pelo **Telegram** (seção 18) e pela página `/equipe`. Cadastros (seção 14), bloqueios (seção 15), backup (seção 16), entrega em **Docker** para VPS (seção 19).

**Não é** sistema de pedido/delivery nem de pagamento (seção 12).

## 1. Execução

- Ponto de entrada: arquivo executável `./reserva` na raiz do repo.
- `./reserva serve --porta N --dados DIR [--host H]`
  - `--porta 0` = porta livre escolhida pelo sistema. A **primeira linha** do stdout é `PORTA=<n>` (com flush), impressa quando o servidor já aceita conexões.
  - Escuta em `--host` (padrão `127.0.0.1`; no Docker, `0.0.0.0` passado pelo comando do container — nunca escrito no código).
  - `DIR/restaurante.json` = configuração (seção 2). Se não existir, copiar `exemplos/restaurante.json`.
  - Todo o estado persiste em `DIR/` (ex.: SQLite). Reiniciar com o mesmo `DIR` mantém tudo.
- **Relógio:** variável de ambiente `RESERVA_AGORA` (`AAAA-MM-DDTHH:MM`, hora local do restaurante, sem fuso) fixa o "agora" do processo. Sem ela, usa o relógio real. Datas/horas no contrato são sempre `AAAA-MM-DDTHH:MM` local; datas soltas, `AAAA-MM-DD`.
- `./reserva raiox --dados DIR --mes AAAA-MM --acompanhamento ARQ` (seção 10).
- `./reserva backup` / `./reserva restaurar` (seção 16).
- Integrações externas **só** por variáveis de ambiente (seções 17–18). Sem elas, nenhuma chamada de rede sai do processo. Nenhuma URL externa, chave ou token escrito no código.

## 2. `restaurante.json`

```json
{
  "nome": "Cantina do Bairro",
  "token": "segredo",                    // exigido no header X-Token das rotas da equipe [E]
  "passo_min": 30,                       // grade de horários
  "antecedencia_min_horas": 1,           // não oferece/aceita início antes de agora + isto
  "janela_dias": 30,                     // até quantos dias à frente aceita reserva
  "confirmacao_horas": 24,               // pede confirmação quando a reserva começa em até 24 h
  "grupo_grande_a_partir": 8,            // pessoas >= isto → aprovação humana (seção 9)
  "limite_pessoas_por_horario": 20,      // soma de pessoas das reservas ativas com o mesmo início; null = sem limite
  "reativacao_dias": 60,                 // convite de retorno quando a última visita completa X dias
  "feriados": ["2026-10-15"],            // dias fechados (sem turno)
  "duracao": [                           // duração da reserva pelo nº de pessoas: 1ª regra com pessoas <= ate; ate null = qualquer
    {"ate": 2, "min": 90}, {"ate": 6, "min": 120}, {"ate": null, "min": 180}
  ],
  "saloes": [ {"id": "interno", "nome": "Salão interno"}, {"id": "varanda", "nome": "Varanda"} ],
  "combinacoes": [ {"id": "m3m4", "mesas": ["m3", "m4"], "min": 7, "max": 8} ],
  "turnos": [ {"id": "almoco", "nome": "Almoço", "dias": ["ter","qua","qui","sex","sab","dom"], "inicio": "11:30", "fim": "15:00"} ],
  "mesas": [ {"id": "m1", "salao": "interno", "min": 1, "max": 2} ],
  "faq": [ {"id": "pet", "perguntas": ["aceitam pet"], "resposta": "Sim, na varanda."} ]
}
```

Dias da semana: `seg ter qua qui sex sab dom`. `duracao` é avaliada na ordem escrita; a lista termina obrigatoriamente com `ate: null`. A fixture dos testes está em `tests/fixtures/restaurante.json`; o exemplo em `exemplos/restaurante.json` é igual, com token `TROQUE-ESTE-TOKEN`.

## 3. Regras de horário e alocação

**Duração** de uma reserva de `pessoas` = `min` da primeira regra de `duracao` com `pessoas <= ate` (`ate: null` casa qualquer).

**Horário candidato** para uma data: para cada turno ativo que tem o dia da semana em `dias`, os instantes `turno.inicio + k × passo_min` (k ≥ 0) tais que `[inicio, inicio + duracao)` cabe inteiro em `[turno.inicio, turno.fim)` (isto é, `inicio + duracao <= turno.fim`). Turnos ativos do mesmo dia não se sobrepõem (seção 14).

**Inválido (422)** se: não é horário candidato (fora da grade, não cabe no turno, dia sem turno); dia em `feriados`; `inicio < agora + antecedencia_min_horas`; `data(inicio) > data(agora) + janela_dias` (o dia `data(agora) + janela_dias` ainda vale); `pessoas < 1`; `mesa` pedida não serve o grupo (`pessoas < min` ou `pessoas > max`) ou está inativa; há bloqueio do restaurante inteiro cobrindo qualquer instante de `[inicio, fim)` (seção 15).

**Mesa serve** um pedido se: está ativa; `min <= pessoas <= max`; pertence ao `salao` pedido (quando informado); não está sob bloqueio de mesa/salão que sobreponha `[inicio, fim)`; e está **livre**: nenhuma reserva **ativa** que a ocupe sobrepõe `[inicio, fim)` (intervalos semiabertos: sobrepõe se `inicio < outro.fim` e `fim > outro.inicio`).

**Escolha automática** (sem `mesa` informada):
1. entre as mesas que servem, a de **menor `max`**; empate → a que vem **primeiro na ordem do cadastro** (ordem de `mesas` no JSON, depois ordem de criação pela API);
2. **só se nenhuma mesa única serve**, entre as `combinacoes` com `min <= pessoas <= max` cujas mesas estão **todas** ativas, no salão pedido (quando informado), sem bloqueio e livres: a de menor `max`; empate → ordem da lista. A reserva ocupa **todas** as mesas da combinação.
3. nada serve → **409** `{"erro": "sem_mesa"}`.

**Limite da cozinha:** com `limite_pessoas_por_horario` não nulo, a soma de `pessoas` das reservas ativas com o **mesmo `inicio`** mais o pedido não pode passar do limite; senão **409** `{"erro": "limite_cozinha"}` (verificado depois de achar mesa; também filtra `/api/horarios`).

**Mesa informada** (`mesa` no corpo): usa só ela (ou a combinação cujo `id` for informado em `mesa`); ocupada → 409 `sem_mesa`; não serve/inativa → 422.

**Status.** Reserva **ativa** = `reservada`, `confirmada`, `pendente`, `chegou` ou `no_show` (ocupa mesas, conta no limite da cozinha e na ocupação). `cancelada` e `recusada` liberam as mesas.

`GET /api/horarios` lista só horários candidatos válidos em que a escolha automática encontraria mesa **e** o limite da cozinha permite; ordem por `inicio`.

**Concorrência:** dois pedidos simultâneos pela mesma mesa/horário: exatamente um vence (201), o outro recebe 409.

## 4. Autenticação

Rotas marcadas **[E]** (equipe) exigem header `X-Token` igual a `restaurante.json.token`; sem ele ou errado → **401**. Rotas públicas: `/`, `/equipe` (página; os dados vêm de rotas [E]), `/api/saude`, `GET /api/turnos`, `GET /api/saloes`, `/api/horarios`, `/api/mensagens`. Webhooks têm segredo próprio (seções 17 e 18).

## 5. API HTTP (JSON, UTF-8)

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/saude` | — | 200 `{"ok": true, "versao": "<conteúdo de VERSION>"}` |
| `GET /api/saloes` | — | 200 `{"saloes": [{id, nome}]}` na ordem do JSON |
| `GET /api/turnos` | — | 200 `{"turnos": [{id, nome, dias, inicio, fim, ativo}]}` só os ativos, ordem do cadastro |
| `GET /api/horarios?data=AAAA-MM-DD&pessoas=N[&salao=S]` | — | 200 `{"horarios": [{"inicio", "turno"}]}` ordenado por `inicio`; `pessoas` ausente, não inteiro ou `< 1` → 422; `salao` inexistente → 404; data sem turno, feriado, fora da janela ou passada → 200 com lista vazia |
| `POST /api/clientes` [E] | `{nome, telefone, consentimento_marketing?: bool, aniversario?: "MM-DD", origem?}` | 201 `{id}`; telefone já cadastrado → 200 com o mesmo `{id}` (demais campos não mudam); telefone inválido ou `aniversario` fora de `MM-DD` → 400; `origem` fora da lista (seção 9) → 422 `{"erro": "origem_invalida"}` |
| `GET /api/clientes?busca=T` [E] | — | 200 `{"clientes": [{id, nome, telefone, consentimento_marketing, nao_contatar, aniversario, origem, ultima_visita, visitas}]}`; `busca` casa parte do nome (sem acento, sem caixa) ou dígitos do telefone; sem `busca` = todos, ordem de criação |
| `PUT /api/clientes/{id}` [E] | `{nome?, telefone?, consentimento_marketing?, nao_contatar?, aniversario?, origem?}` | 200 com o cliente; telefone inválido/aniversário inválido → 400; telefone de outro cliente → 409; origem inválida → 422; inexistente → 404 |
| `GET /api/clientes/{id}/dados` [E] | — | 200 `{cliente, reservas, mensagens}` (seção 11) |
| `DELETE /api/clientes/{id}` [E] | — | 204; anonimiza (seção 11) |
| `POST /api/reservas` [E] | `{cliente_id, inicio, pessoas, salao?, mesa?, observacao?}` | 201 `{id, status, inicio, fim, pessoas, turno, salao, mesas: [ids], cliente_id, observacao}`; `status` = `pendente` se `pessoas >= grupo_grande_a_partir`, senão `reservada`; 409/422 conforme seção 3; cliente, salão ou mesa inexistente → 404 |
| `GET /api/reservas?data=AAAA-MM-DD[&turno=T][&salao=S]` [E] | — | 200 `{"reservas": [{id, cliente_id, nome, telefone, pessoas, inicio, fim, turno, salao, mesas, status, observacao}]}` ordenado por `inicio`, depois `id`; inclui canceladas/recusadas (filtrar pelo `status`) |
| `GET /api/reservas?de=AAAA-MM-DD&ate=AAAA-MM-DD[&turno=T][&salao=S]` [E] | — | mesma lista, pontas inclusivas |
| `POST /api/reservas/{id}/cancelar` [E] | — | 200 `{status: "cancelada"}`; dispara a lista de espera (seção 7); só de `reservada`, `confirmada` ou `pendente`, senão 409 `{"erro": "status"}` |
| `POST /api/reservas/{id}/remarcar` [E] | `{inicio?, pessoas?}` (ao menos um) | 200 com a reserva realocada (mesmo `id`; mesas podem mudar; as mesas da própria reserva contam como livres); `status` vira `reservada` (ou `pendente` se as novas `pessoas >= grupo_grande_a_partir`) e a confirmação volta a ser devida; mesmas regras 409/422; só de `reservada`, `confirmada` ou `pendente`, senão 409 |
| `POST /api/reservas/{id}/chegada` [E] | `{compareceu: bool}` | 200 `{status: "chegou" \| "no_show"}`; só de `reservada` ou `confirmada`, senão 409; `chegou` atualiza `ultima_visita`/`visitas` do cliente (seção 9); não depende do relógio |
| `POST /api/reservas/{id}/aprovar` [E] | — | 200 `{status: "reservada"}`; só de `pendente`, senão 409; envia mensagem `tipo: "aprovacao"` ao cliente (seção 9) |
| `POST /api/reservas/{id}/recusar` [E] | — | 200 `{status: "recusada"}`; só de `pendente`, senão 409; libera as mesas (**não** dispara a lista de espera); envia `tipo: "recusa"` |
| `GET /api/ocupacao?data=AAAA-MM-DD[&salao=S]` [E] | — | 200 `{"data", "horarios": [{inicio, turno, mesas_total, mesas_ocupadas, pessoas}]}`: um item por instante da grade de cada turno ativo do dia (`turno.inicio + k × passo_min < turno.fim`), ordem por `inicio`. `mesas_total` = mesas ativas (do salão, se informado); `mesas_ocupadas` = dessas, as ocupadas por reserva ativa com `reserva.inicio <= instante < reserva.fim`; `pessoas` = soma de `pessoas` dessas reservas (cada reserva conta uma vez). Feriado/dia sem turno → lista vazia |
| `POST /api/espera` [E] | `{cliente_id, data, turno, pessoas}` | 201 `{id}`; turno inexistente/inativo → 404; `pessoas < 1` → 422 |
| `GET /api/espera?data=AAAA-MM-DD` [E] | — | 200 `{"espera": [{id, cliente_id, nome, telefone, data, turno, pessoas, status}]}` ordem de criação; `status` ∈ `pendente, ofertada, atendida, cancelada` |
| `POST /api/tarefas/rodar` [E] | `{agora?}` (padrão = relógio do processo) | 200 `{"enviadas": n, "reenviadas": n}` (seção 8); idempotente: rodar de novo no mesmo instante → `enviadas: 0` |
| `GET /api/saida` [E] | — | 200 `{"mensagens": [{id, tipo, telefone, cliente_id, texto, reserva_id, status, quando}]}` em ordem de criação. `tipo` ∈ `confirmacao, espera, aprovacao, recusa, aniversario, reativacao, campanha, humano`; `status` ∈ `simulado, enviado, pendente` (seção 17) |
| `POST /api/mensagens` | `{telefone, texto}` | 200 `{"respostas": [texto, ...]}` (seção 6) |
| `GET /api/atendimento-humano` [E] | — | 200 `{"fila": [{id, telefone, nome, motivo, status}]}` só os `aberto`, ordem de abertura |
| `POST /api/atendimento-humano/{id}/responder` [E] / `.../encerrar` [E] | `{texto}` / — | 200 (seção 18) |
| `POST /api/campanhas` [E] | `{texto}` | 200 `{"enviadas": n}`; texto vazio (só espaços) → 422 (seção 9) |
| `GET /api/raiox?mes=AAAA-MM` [E] | — | 200 (seção 10) |

Cadastros (mesas, turnos, FAQ) e bloqueios: seções 14 e 15.

**Ids inexistentes:** qualquer rota com `{id}` no caminho (`/api/reservas/{id}/...`, `/api/clientes/{id}...`, `/api/mesas/{id}`, `/api/turnos/{id}`, `/api/faq/{id}`, `/api/bloqueios/{id}`, `/api/atendimento-humano/{id}/...`) e qualquer referência por id no corpo (`cliente_id`, `salao`, `mesa`, `turno`) a algo que não existe → **404**, antes das validações de 409/422. Corpo que não é JSON ou sem os campos obrigatórios → **422**.

**Telefone:** aceita com ou sem `+55`, espaços, parênteses e hífen; normaliza para `+55DDNNNNNNNNN` (DDD + 8 ou 9 dígitos). Fora disso → inválido. Todas as respostas usam o telefone normalizado.

**Rotas síncronas:** `POST /api/mensagens`, `tarefas/rodar`, `campanhas`, `cancelar` (oferta da lista de espera), `aprovar`, `recusar`, `responder`, e `DELETE /api/clientes/{id}` só devolvem a resposta HTTP depois de criar as mensagens de saída e tentar os envios (o `status` em `/api/saida` já está definido). Respostas ao webhook da Evolution e avisos ao Telegram podem ser assíncronos.

## 6. Conversa (`POST /api/mensagens`)

O texto é normalizado (minúsculas, sem acento, sem pontuação; `amanhã` vira `amanha`) antes de decidir. Ordem de decisão:

1. **Parar** — texto igual a `parar`, `sair` ou `pare`: cliente fica `nao_contatar`; resposta contém `não vai mais receber`. Mensagens automáticas (`confirmacao`, `espera`, `aniversario`, `reativacao`, `campanha`) não vão mais para esse telefone; respostas a pedidos dele (`aprovacao`, `recusa`, `humano`) continuam.
2. **Humano** — contém `atendente`, `humano` ou `falar com alguem`: fila humana; resposta contém `atendente`.
3. **Fluxo em andamento** (reserva, cancelamento ou lista de espera, abaixo) consome a mensagem.
4. **Resposta a pendência:** se a última mensagem de saída para o telefone foi `confirmacao` (sem resposta ainda): `1`/`sim`/`confirmo` → status `confirmada`, resposta contém `confirmad`; `2`/`cancelar`/`nao` → `cancelada` (dispara espera), resposta contém `cancelad`. Se foi `espera` (sem resposta): `1`/`sim` → cria a reserva no horário ofertado se ainda couber (resposta contém `reservad`), senão resposta contém `ocupad`; a espera vira `atendida` no primeiro caso. Qualquer outro texto não consome a pendência.
5. **Consultar/cancelar** — contém `minha reserva`, `minhas reservas` ou `cancelar`: lista as reservas **futuras ativas** (`inicio > agora`, exceto `chegou`/`no_show`) do telefone, uma linha `N) DD/MM HH:MM — P pessoas` cada. Sem reservas → resposta contém `não encontrei`. Com `cancelar`: uma só → cancela na hora (resposta contém `cancelad`, `DD/MM`); várias → lista e a próxima mensagem com o número cancela (fluxo de cancelamento; `0` ou `cancelar` sai sem cancelar).
6. **Reservar** — contém `reservar` ou `reserva`: inicia o fluxo de reserva.
7. **FAQ** — palavras significativas (≥ 3 letras, fora de artigos/preposições/pronomes comuns) de alguma pergunta do FAQ: se ≥ 60 % delas aparecem no texto, responde **exatamente** a `resposta` daquele item (só ela, uma mensagem). Mais de um item casa → o de maior %; empate → o primeiro do FAQ.
8. **Não entendi** — resposta contém `não entendi` e oferece `atendente`. Na **segunda** seguida sem entender, entra na fila humana automaticamente.

**Fluxo de reserva pelo chat** (estado por telefone, persistido; em cada passo a resposta faz a pergunta do passo):
- telefone sem cliente → pergunta o nome (resposta contém `nome`); a próxima mensagem vira o nome e o cliente é criado (`consentimento_marketing: false`, `origem: "chat"`, ou `"whatsapp"` quando vem pela Evolution);
- pergunta **quantas pessoas** (resposta contém `pessoas`); aceita inteiro ≥ 1, senão repete;
- pergunta **o dia** (resposta contém `dia`); aceita `hoje`, `amanha`, `DD/MM` ou `DD/MM/AAAA`. `DD/MM` = a próxima ocorrência a partir de hoje (hoje incluso). Dia inválido, passado, sem turno, feriado ou fora da janela → resposta contém `não` e `dia`, repete;
- lista os horários livres do dia para o grupo (regra da seção 3, a partir de `agora + antecedencia_min_horas`), **até 8**, em ordem, uma linha `N) HH:MM (<nome do turno>)` cada; o número escolhido cria a reserva; resposta contém `reservad`, `DD/MM`, `HH:MM` e `<P> pessoas`. Se o status for `pendente` (grupo grande), a resposta contém `aguardando` e `equipe`;
- dia com turno mas **sem horário livre** para o grupo → resposta contém `lista de espera` e oferece `1` (sim) / `2` (não). `1`: se o dia tem mais de um turno, pergunta qual, numerado `N) <nome do turno>` na ordem do cadastro; cria o pedido de espera (`data`, `turno`, `pessoas`) e a resposta contém `lista de espera`. `2` → sai do fluxo;
- número inválido em qualquer passo → repete as opções. `cancelar` dentro do fluxo → sai do fluxo (resposta contém `cancelad` e **não** cancela reserva nenhuma).
- O bot **nunca** inventa preço, cardápio ou disponibilidade: fora do FAQ e do fluxo, cai na regra 8.

## 7. Lista de espera

Ao cancelar uma reserva (pela API, pela conversa ou pela exclusão LGPD), o primeiro pedido de espera `pendente` (ordem de criação) com a **mesma `data`** e o **mesmo `turno`** da reserva cancelada, cujo cliente não esteja `nao_contatar` e cujas `pessoas` a escolha automática consegue alocar no `inicio` liberado (seção 3, inclusive limite da cozinha), recebe mensagem `tipo: "espera"` contendo `HH:MM` do horário e `1`. O pedido fica `ofertada` com esse `inicio` guardado (não recebe outra oferta). Recusa de grupo grande e `no_show` não disparam a lista.

## 8. Confirmação, aniversário e reativação (`POST /api/tarefas/rodar`)

- **Confirmação:** toda reserva `reservada` com `agora < inicio <= agora + confirmacao_horas` que ainda não recebeu confirmação (desde a última criação/remarcação) → mensagem `tipo: "confirmacao"` com `reserva_id`. Texto contém `DD/MM`, `HH:MM`, `<P> pessoas`, `1` (confirmar) e `2` (cancelar). **Não contém valor em R$.** Reservas `pendente` não recebem confirmação (esperam aprovação).
- **Aniversário:** cliente com `aniversario` igual a `MM-DD` do dia de `agora`, `consentimento_marketing: true`, não `nao_contatar` → mensagem `tipo: "aniversario"` contendo o primeiro nome do cliente, **uma vez por ano** (ano de `agora`).
- **Reativação:** cliente com `consentimento_marketing: true`, não `nao_contatar`, `ultima_visita` não nula e `data(agora) >= ultima_visita + reativacao_dias` → mensagem `tipo: "reativacao"` contendo o nome do restaurante. **Uma por visita**: não se repete enquanto `ultima_visita` não mudar.
- `enviadas` = mensagens criadas nesta rodada; `reenviadas` = `pendente` que viraram `enviado` (seção 17). Cliente `nao_contatar` nunca recebe estes tipos. Confirmação e oferta de espera **não** dependem de `consentimento_marketing` (execução do que o próprio cliente pediu); aniversário, reativação e campanha **dependem**.

## 9. Grupo grande, base própria e campanhas

- **Grupo grande:** reserva com `pessoas >= grupo_grande_a_partir` nasce `pendente` (ocupa as mesas), avisa a equipe (seção 18) e espera `aprovar`/`recusar`. Aprovada → `reservada` + mensagem `tipo: "aprovacao"` ao cliente contendo `confirmad`, `DD/MM`, `HH:MM`. Recusada → `recusada` (mesas liberadas) + mensagem `tipo: "recusa"` contendo `não foi possível`. Sinal/Pix para grupo grande é **política escrita** (FAQ/README), sem cobrança no sistema (seção 12).
- **Origem do cliente:** `origem` ∈ `salao, whatsapp, chat, telefone, site, indicacao, equipe, outro`; padrão `equipe` na API, `chat` no chat web, `whatsapp` pela Evolution. Qualquer outro valor (ex.: `ifood`, `marketplace`, `rappi`) → 422 `origem_invalida`: **contato que chegou por marketplace não entra na base** (contrato iFood cl. 3.3.1 — `raio-x-margem/docs/TERMOS.md`). A base é só de canais do próprio restaurante.
- **Visitas:** `chegou` grava `ultima_visita` = data (`AAAA-MM-DD`) do `inicio` da reserva, se maior que a atual, e `visitas` = nº de reservas `chegou` do cliente.
- **Campanhas:** `POST /api/campanhas {texto}` cria `tipo: "campanha"` com o texto para cada cliente com `consentimento_marketing: true`, sem `nao_contatar` e com telefone (LGPD art. 7º, I — consentimento). Devolve `{"enviadas": n}`. Não há trava de conselho (restaurante não tem publicidade regulada por conselho profissional).

## 10. Exportação para o Raio-X (Painel de Recuperação)

`GET /api/raiox?mes=AAAA-MM` → `{"pacote": "restaurante", "mes": "AAAA-MM", "valores": {...}}`, percentuais arredondados a 1 casa (`round` half-even do Python):

- `clientes_novos_mes` = clientes cujo **primeiro** `chegou` cai no mês (inteiro) — **id real** do pacote `setores/restaurante.js`;
- `retorno_atual_pct` = da coorte acima, % com um **segundo** `chegou` até 60 dias (inclusive) depois do primeiro (0 se a coorte for vazia) — **id real** do pacote ("desses, quantos voltam em 60 dias");
- `reservas_atendidas_mes` = reservas `chegou` com `inicio` no mês (inteiro);
- `no_show_pct` = `no_show ÷ (chegou + no_show) × 100` das reservas com `inicio` no mês (0 se não houver);
- `ocupacao_pct` = mesa-minutos reservados ÷ mesa-minutos disponíveis × 100, onde reservados = soma, nas reservas ativas com `inicio` no mês, de `nº de mesas ocupadas × duracao`, e disponíveis = soma, por dia do mês que não é feriado, de `mesas ativas × soma das durações dos turnos ativos do dia` (bloqueios **não** são descontados).

Os três últimos não são entradas do pacote: o painel só lê as entradas de cada vazamento e ignora o resto; eles ficam no arquivo para a equipe. O número de `retorno_atual_pct` de um mês só fecha 60 dias depois — rodar a exportação de novo atualiza.

`./reserva raiox --dados DIR --mes M --acompanhamento ARQ`: lê `ARQ` (formato do `raio-x-margem/app/painel-motor.js`: `{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}`), insere ou substitui o mês `M` com `valores` = os da rota acima **mesclados** sobre os valores do mês anterior (ou da base) e `obs: "reserva-restaurante"`, e grava de volta. Campos que o sistema não mede (ex.: `ticket_medio`, `fat_marketplace`) ficam como estavam. Sai com código 0.

## 11. LGPD

- `GET /api/clientes/{id}/dados` devolve tudo o que há do cliente: `cliente` `{id, nome, telefone, consentimento_marketing, nao_contatar, aniversario, origem, ultima_visita, visitas}`, `reservas` (mesmo formato da listagem) e `mensagens` = recebidas e enviadas, cada uma `{direcao: "entrada" | "saida", texto, quando}`.
- `DELETE /api/clientes/{id}`: nome vira `removido`, telefone, aniversário vira `null`, reservas futuras ativas (`reservada`, `confirmada`, `pendente`) viram `cancelada` pelo caminho normal (dispara espera), `chegou`/`no_show` ficam, textos de mensagens dele viram `""`, pedidos de espera dele viram `cancelada`. Depois disso, mensagens ao telefone antigo são tratadas como de telefone desconhecido. Números agregados do `/api/raiox` continuam contando as visitas passadas.

## 12. Fora do v1 (não implementar; portão humano ou próxima versão)

Pedido/delivery e cardápio com carrinho, pagamento (sinal por Pix, PSP, cobrança de no-show), WhatsApp Cloud API oficial (v1 usa a Evolution), SMS/e-mail, deploy na VPS (é do humano: README explica), mapa gráfico de mesas (v1 é tabela por horário), reservas recorrentes, vários restaurantes no mesmo servidor, login por usuário, LLM nas respostas (pode entrar depois atrás de uma opção desligada; os testes nunca a usam), interface EN/ES, integração com marketplaces (iFood etc.).

## 13. Páginas

- `GET /` → HTML do chat do cliente, com elemento `id="chat"`, que usa `/api/mensagens`.
- `GET /equipe` → HTML da equipe com elementos `id="reservas"`, `id="ocupacao"`, `id="fila-humano"`, `id="espera"` e `id="mesas"`; pede o token e usa as rotas [E] (reservas do dia por turno e salão, mapa de ocupação, chegada/no-show, aprovar/recusar, cadastros de mesas, turnos, FAQ, bloqueios, fila humana com responder/encerrar, caixa de saída).

## 14. Cadastros [E]

`restaurante.json` é lido a cada início para `nome, token, passo_min, antecedencia_min_horas, janela_dias, confirmacao_horas, grupo_grande_a_partir, limite_pessoas_por_horario, reativacao_dias, feriados, duracao, saloes, combinacoes`. Já `mesas`, `turnos` e `faq` só **semeiam** o banco na primeira vez (banco vazio); depois o banco é a fonte e se edita pela API.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/mesas` | — | 200 `{"mesas": [{id, salao, min, max, ativa}]}` ordem do cadastro (inclui inativas) |
| `POST /api/mesas` | `{id, salao, min, max}` | 201; `id` repetido → 409; salão inexistente, `min < 1` ou `max < min` → 422 |
| `PUT /api/mesas/{id}` | campos parciais (`salao, min, max`) | 200 com a mesa; inexistente → 404; mesmas validações |
| `DELETE /api/mesas/{id}` | — | 200 `{"ativa": false}`. Inativa não serve reserva nova, some de `mesas_total` e inutiliza combinações que a incluem; as reservas já feitas continuam |
| `POST /api/turnos` | `{id, nome, dias, inicio, fim}` | 201; `id` repetido → 409; `dias` fora de `seg..dom`, `inicio >= fim` ou sobreposição com turno ativo no mesmo dia → 422 |
| `PUT /api/turnos/{id}` / `DELETE /api/turnos/{id}` | parcial / — | 200 / 200 `{"ativo": false}` (horários do turno somem na hora; reservas já feitas continuam) |
| `GET /api/faq` | — | 200 `{"faq": [{id, perguntas, resposta}]}` |
| `POST /api/faq` | `{perguntas: [..], resposta}` | 201 `{id}`; o bot passa a usar na hora |
| `DELETE /api/faq/{id}` | — | 204; o bot para de usar na hora |

## 15. Bloqueios [E]

`POST /api/bloqueios {inicio, fim, motivo, salao?, mesa?}` → 201 `{id, conflitos: [ids de reservas ativas que sobrepõem o bloqueio nas mesas afetadas]}` (não cancela nada sozinho). Sem `salao` e sem `mesa` = **restaurante inteiro** (evento fechado): horários que sobrepõem `[inicio, fim)` somem de `/api/horarios` e a reserva neles dá **422**. Com `salao` ou `mesa`: as mesas afetadas ficam indisponíveis no período (como ocupadas); se nenhuma outra serve → **409** `sem_mesa`. `salao`/`mesa` inexistente → 404. `GET /api/bloqueios` → 200 `{"bloqueios": [{id, inicio, fim, motivo, salao, mesa}]}` ordenado por `inicio`. `DELETE /api/bloqueios/{id}` → 204 e libera.

## 16. Banco de dados

- `./reserva backup --dados DIR --saida ARQ` → grava em `ARQ` uma cópia consistente de todo o estado (pode rodar com o servidor ligado). Código 0.
- `./reserva restaurar --dados DIR --entrada ARQ` → com o servidor parado, substitui o estado de `DIR` pelo do backup. Código 0. Ao subir de novo, tudo volta como estava no momento do backup.

## 17. WhatsApp pela Evolution API

Variáveis: `EVOLUTION_URL` (ex.: `http://evolution:8080`), `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`, `WEBHOOK_SEGREDO`. Sem `EVOLUTION_URL` → canal simulado (só caixa de saída, `status: "simulado"`).

**Entrada** — `POST /webhook/evolution/{WEBHOOK_SEGREDO}` (segredo errado → 404). Formato da Evolution v2:
```json
{"event": "messages.upsert", "instance": "restaurante",
 "data": {"key": {"remoteJid": "5541999990001@s.whatsapp.net", "fromMe": false, "id": "ABC123"},
          "pushName": "Maria", "message": {"conversation": "oi"}, "messageType": "conversation"}}
```
- Sempre responde 200. Ignora: `event` diferente de `messages.upsert`, `fromMe: true`, `remoteJid` de grupo (`@g.us`), `key.id` já processado (a Evolution reenvia).
- Texto = `message.conversation` ou `message.extendedTextMessage.text`. Sem texto (áudio, imagem...) → responde `Por enquanto só consigo ler mensagens de texto.`
- Telefone = dígitos do `remoteJid` antes do `@`, normalizado como na seção 5. Passa pela mesma conversa da seção 6 (o mesmo cliente, o mesmo estado).
- Cada resposta da conversa vai por `POST {EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCIA}` com header `apikey: {EVOLUTION_API_KEY}` e corpo `{"number": "<dígitos com 55>", "text": "<texto>"}`, na ordem.

**Saída** (confirmação, espera, aprovação, recusa, aniversário, reativação, campanha, humano): com a Evolution configurada, cada mensagem da caixa de saída é enviada do mesmo jeito. Em `/api/saida` cada mensagem tem `status`: `enviado` (2xx), `pendente` (erro HTTP ou de conexão) ou `simulado`. `POST /api/tarefas/rodar` reenvia as `pendente` e devolve `"reenviadas": n` (as que viraram `enviado`).

## 18. Atendimento interno pelo Telegram

Variáveis: `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (grupo da equipe), `TELEGRAM_SEGREDO`. Sem elas, nada vai ao Telegram (o resto funciona igual). Envio: `POST {TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendMessage` com `{"chat_id", "text"[, "reply_to_message_id"]}`; a resposta do Telegram traz `result.message_id`.

**Atendimento humano** (`/api/atendimento-humano` → `{"fila": [{id, telefone, nome, motivo, status}]}` só com os `aberto`):
- Ao abrir (pedido de atendente, 2º "não entendi"): manda ao grupo um texto com `#<id>`, telefone, nome (se houver), motivo e a última mensagem do cliente. Guarda o `message_id`.
- Enquanto o atendimento do telefone estiver `aberto`, o bot **não responde** sozinho (`respostas: []`); cada mensagem do cliente vai ao grupo como `#<id> <nome ou telefone>: <texto>`, em resposta (`reply_to_message_id`) à mensagem de abertura.
- `POST /webhook/telegram` exige header `X-Telegram-Bot-Api-Secret-Token: {TELEGRAM_SEGREDO}` (senão 401). Só aceita updates de `message.chat.id == TELEGRAM_CHAT_ID`; os outros são ignorados (200, sem efeito).
- Mensagem da equipe que é resposta (`reply_to_message.message_id`) a uma mensagem do atendimento `#id` → o texto vai ao cliente (caixa de saída `tipo: "humano"`, e pela Evolution se configurada).
- Comandos: `/responder <id> <texto>` (o mesmo, sem precisar responder em cima); `/encerrar <id>` → status `encerrado`, o bot volta a responder aquele telefone; `/fila` → lista dos abertos (cada um com `#id`); `/reservas [AAAA-MM-DD]` (padrão: hoje pelo relógio) → reservas ativas do dia, ordem de `inicio`, uma linha `HH:MM <nome> — <P> pessoas — <mesas unidas por +> (<status>)` cada; `/aprovar <id>` e `/recusar <id>` → o mesmo que as rotas da seção 5 (o bot confirma no grupo com `#<id>`).
- Pela página [E]: `POST /api/atendimento-humano/{id}/responder {texto}` e `POST /api/atendimento-humano/{id}/encerrar` fazem o mesmo.
- **Avisos à equipe:** reserva `reservada` feita pelo chat/WhatsApp → `Nova reserva: DD/MM HH:MM <nome> — <P> pessoas`; reserva `pendente` criada por qualquer canal → `Grupo grande #<id>: DD/MM HH:MM <nome> — <P> pessoas` (e **não** o aviso de nova reserva); cancelamento pelo chat/WhatsApp (inclusive pela resposta `2`) → texto começando com `Cancelada:` e com `DD/MM HH:MM`.

## 19. Docker / VPS

- `Dockerfile` (imagem oficial `python:3-slim` ou similar, **sem `pip install`**) que roda `./reserva serve --host 0.0.0.0 --porta 8080 --dados /dados`, com `HEALTHCHECK` em `/api/saude`.
- `docker-compose.yml` com o serviço `reserva`: `build: .`, `restart: unless-stopped`, `env_file: .env`, volume para `/dados`, porta publicada só em `127.0.0.1:8080` (na VPS fica atrás de proxy reverso com HTTPS).
- `.env.exemplo` com todas as variáveis das seções 17 e 18, **valores vazios** (nenhum segredo, nenhuma URL real).
- `README.md` com a seção **Deploy na VPS**: subir o compose, proxy HTTPS, configurar o webhook da Evolution para `/webhook/evolution/<segredo>` (evento `MESSAGES_UPSERT`), registrar o webhook do Telegram com `setWebhook` + `secret_token`, e o backup diário (`./reserva backup` no cron).
