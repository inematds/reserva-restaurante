# Decisões — propostas padrão já aplicadas (05/10/2026)

Cada item tem uma **proposta padrão** já escrita na `docs/ESPECIFICACAO.md` e nos testes (93). Responder "ok em tudo" destrava a execução. Se mudar algo que afete o contrato (marcado ⚠), ajustar a spec e os testes **antes** de rodar `congelar.sh`.

| # | Decisão | Proposta padrão | Por quê |
|---|---|---|---|
| 1 | Nome do projeto / repo | `reserva-restaurante` (pasta e futuro repo `inematds/reserva-restaurante`) | regra: repo = nome da pasta |
| 2 ⚠ | Linguagem | **Python 3, só biblioteca padrão** (`http.server` + `sqlite3`), igual ao atende-clinica | zero dependência; os testes são caixa-preta (HTTP/CLI), então trocar de linguagem não invalida os testes — mas aí ajustar `verificar-limites.sh`, `goal.md` e `prompt.md` antes de congelar |
| 3 | Canais | chat web + **WhatsApp pela Evolution API** (simulado quando não configurado); equipe pelo **Telegram** e pela página `/equipe` com token | mesma pilha e mesmos canais do atende-clinica (briefing) |
| 4 ⚠ | Alocação de mesa | **menor `max` que serve**, empate pela **ordem do cadastro**; combinação de mesas (com `min`/`max` próprios) **só quando nenhuma mesa única livre serve** | regra escrita e testável; evita dar mesa de 6 a casal. Alternativa descartada: "mesa mais usada/mais perto da janela" (não determinístico) |
| 5 ⚠ | Duração da reserva | tabela `duracao` por nº de pessoas (fixture: ≤2 → 90 min, ≤6 → 120, resto → 180) e a reserva cabe inteira no turno | grupo grande fica mais tempo; duração fixa dava buraco na grade |
| 6 ⚠ | Grupo grande | `pessoas >= grupo_grande_a_partir` (8) nasce **`pendente` ocupando as mesas** até `aprovar`/`recusar`; aviso no Telegram | não ocupar deixaria outro grupo pegar as mesas enquanto a equipe decide. Alternativa: não ocupar + aprovar só se ainda couber |
| 7 ⚠ | Limite da cozinha | opcional; soma de pessoas das reservas ativas com o **mesmo `inicio`** (não por sobreposição) | simples de explicar e de conferir no mapa de ocupação; `null` desliga |
| 8 ⚠ | Confirmação | pede 24 h antes, "1 confirma / 2 cancela"; remarcar pede de novo; `pendente` não recebe | mesmo mecanismo do atende-clinica (48 h lá) |
| 9 ⚠ | No-show | marcado pela equipe (`chegada {compareceu: false}`); `no_show` continua ocupando a mesa no histórico; **sem cobrança** | cobrança de no-show exige PSP (fora do v1); manter ocupado preserva a ocupação medida |
| 10 ⚠ | Lista de espera | por `data + turno + pessoas`; ao cancelar, oferta ao **primeiro** pedido que cabe no horário liberado; `1` aceita; recusa de grupo grande e no-show não disparam | determinístico e igual ao da clínica; "cabe" usa a mesma alocação |
| 11 ⚠ | Base própria (canal próprio) | `origem` sem valor de marketplace (`ifood`, `rappi`... → 422); aniversário `MM-DD` (sem ano); reativação após `reativacao_dias` (60), **uma por visita**; campanha e aniversário/reativação **só com consentimento**; confirmação e espera sem consentimento (execução do pedido) | iFood cl. 3.3.1 + LGPD art. 7º (I e V). Sem trava de conselho: restaurante não tem publicidade regulada |
| 12 ⚠ | O que vai ao Raio-X | só `clientes_novos_mes` e `retorno_atual_pct` são **ids reais** do pacote `restaurante`; `reservas_atendidas_mes`, `no_show_pct` e `ocupacao_pct` são extras que o painel ignora | o pacote não tem entrada de no-show/ocupação (ver `docs/MAPA-RAIO-X.md`); números sem fonte no Raio-X são premissa |
| 13 | Um restaurante ou vários | **um por instalação** (`--dados DIR`; um container por restaurante) | multi-unidade é outra ordem de complexidade |
| 14 | Idioma | **só PT no v1** | EN/ES depois, pelo processo trilíngue já testado (relatórios do WiFi) |
| 15 | Quem executa | **headless: `loop-longrun.sh` com Codex `gpt-6-astra`** (rota testada no atende-clinica). Alternativas: `/goal` no Codex TUI ou no Claude Code (README) | o loop confere hash dos testes e para por estagnação sozinho. O `loop.env` já leva `CODEX_ARGS="-c sandbox_workspace_write.network_access=true"` (o sandbox do Codex bloqueia socket em 127.0.0.1) |
| 16 | Tetos | 20 ciclos × 30 min, 8 GB por ciclo, parar após 3 ciclos sem avanço | ≤ 10 h no pior caso; o atende-clinica fechou em 7 ciclos com spec deste nível |
| 17 | GitHub / VPS | **não criar agora**; deploy na VPS pelo dono com o README da implementação; repo local | criar repo é ação externa → o dono confirma |
| 18 ⚠ | Pagamento / sinal para grupo grande | **fora do v1** (política escrita no FAQ/README; nada cobrado) | precisa de PSP/API de pagamento = portão humano |
| 19 ⚠ | Emergência | **sem regra de emergência** (diferente da clínica); "atendente/humano" cobre | restaurante não tem o dever de tutela da saúde da clínica |
| 20 ⚠ | Chat: data e gatilhos | `DD/MM` = próxima ocorrência a partir de hoje; `hoje`/`amanhã`; gatilho de reserva = `reservar`/`reserva` (não `mesa`, para não engolir FAQ "tem mesa na varanda?"); `cancelar` solto = cancelar reserva | regras de borda apontadas na revisão do plano |

## Perguntas que só você responde

- Tem um **restaurante real** para o piloto (salões, mesas, turnos, duração, FAQ verdadeiros)? Se sim, trocar `exemplos/restaurante.json` (e, se o contrato mudar, a fixture + testes antes de congelar).
- Isto é **produto para implantar via kit do Raio-X** ou **projeto aberto/curso**? Muda o que vem depois do v1 (guia, licença, deploy), não o v1.
- Quer o **mapa de mesas gráfico** já no v1? O padrão é tabela de ocupação por horário (seção 5, `/api/ocupacao`); o gráfico fica para v2.
- Qual a **política de sinal/Pix para grupo grande** (texto a colocar no FAQ)? Sem resposta, o FAQ do exemplo não fala em sinal.
- Página `/equipe` só funcional (padrão) ou já com o visual INEMA?
