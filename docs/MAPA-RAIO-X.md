# Como o Raio-X de Margem alimenta este projeto

Fonte: `~/projetos/raio-x-margem` (pacote `setores/restaurante.js` v0.2.0; receitas `docs/modulos/canal-proprio.md`, `aquisicao.md`, `marketing-local.md`, `cardapio-vivo.md`, `cobranca.md`; `docs/ANALISE.md`; `docs/TERMOS.md`).

## Vazamentos do restaurante × o que o reserva-restaurante ataca

| Vazamento (id no Raio-X) | Peça no v1 | Seção da spec |
|---|---|---|
| `retencao` — clientes que compram uma vez e não voltam (entradas `clientes_novos_mes`, `retorno_atual_pct`, `retorno_meta_pct`) | base própria com consentimento, `ultima_visita`/`visitas`, convite de retorno após X dias, aniversário; exporta `clientes_novos_mes` e `retorno_atual_pct` medidos na reserva | 8, 9, 10 |
| `marketplace` — marketplace cobrando de novo por cliente que já é seu | o **contato fica com o restaurante**: reserva pelo chat/WhatsApp próprio cria o cliente na base; `origem` recusa marketplace (iFood cl. 3.3.1). O sistema não faz delivery — ataca a parte "quem tem o contato" da receita *aquisição* (marketplace = aquisição, canal próprio = retenção) | 6, 9, 17 |
| `marketing` — anúncio pagando de novo por quem já é cliente | base própria + `POST /api/campanhas` só com consentimento (falar de graça com quem já é cliente). A lista de exclusão nos anúncios é manual (fora) | 9 |
| `mao_de_obra` — equipe presa em WhatsApp à mão (`horas_repetitivas_semana`) | reserva, consulta e cancelamento pelo chat; FAQ; confirmação automática; lista de espera automática; Telegram para a equipe | 6, 7, 8, 18 |
| `ticket`, `cardapio` | **fora** — exigem PDV/cardápio com carrinho (receita *cardápio vivo*, caminho SaaS) | 12 |
| `pagamentos`, `antecipacao`, `caixa` | **fora** — receita *cobrança* é financeira, não de atendimento; sinal/Pix de grupo grande fica para v2 com PSP | 12 |
| `desperdicio`, `compras` | **fora** — cozinha/compras | 12 |

**Premissas sem fonte no Raio-X:** o pacote não tem entrada de no-show nem de ocupação de salão. `no_show_pct` e `ocupacao_pct` são medidas operacionais do próprio sistema (seção 10), úteis para a equipe, e **não** entram na conta de vazamento do painel. Qualquer número de "no-show médio do setor" é premissa até ter fonte.

## Regras que viraram trava testável

- **Termos do marketplace** (`TERMOS.md`): contato que veio do iFood não entra na base → `origem` ∈ canais do próprio restaurante; `ifood`/`marketplace`/`rappi` → 422 `origem_invalida`. Nada do sistema aponta canal próprio dentro do app (fora do escopo por construção).
- **LGPD:** confirmação e oferta de espera = execução do que o cliente pediu (art. 7º, V) → sem consentimento de marketing; aniversário, reativação e campanha = consentimento (art. 7º, I). "PARAR" bloqueia os automáticos. Exportar (`/dados`) e anonimizar (`DELETE`) (art. 18). Aniversário sem ano (minimização).
- **Bot não inventa:** fora do FAQ e do fluxo → "não entendi" → humano no 2º. Nenhum preço, cardápio ou disponibilidade de cabeça.

## Receitas do Raio-X usadas

- *Aquisição* (frente 2: capturar contato com consentimento em todo ponto que é do restaurante; segmentar inativo > X dias; régua) → base própria, `reativacao_dias`, campanhas.
- *Marketing local* (clube do bairro, data da casa) → campanhas só para quem consentiu; o clube em si é operação do implantador.
- *Canal próprio* (atendimento e status pelo WhatsApp do restaurante) → Evolution + Telegram.
- *Cardápio vivo* → só a parte "o cardápio responde o que a equipe respondia à mão" (FAQ); cardápio/pedido ficam no SaaS recomendado pela receita.

## Volta para o Raio-X

`GET /api/raiox?mes=` e `./reserva raiox --acompanhamento` produzem `clientes_novos_mes` e `retorno_atual_pct` (ids do pacote `restaurante`) no formato do `app/painel-motor.js` (Painel de Recuperação), mesclados sobre os valores anteriores — `ticket_medio`, `fat_marketplace` etc. ficam como o diagnóstico registrou. Ciclo: Raio-X mede o "antes" → reserva-restaurante implanta a base própria e a reserva pelo canal do restaurante → o painel mostra o "depois" todo mês, com retorno em 60 dias tirado das visitas reais (coorte fecha 60 dias depois: rodar a exportação de novo).
