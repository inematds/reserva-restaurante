# Canal — reservas-v1 (só acrescentar; nunca reescrever)

Conhecimento do projeto que a compactação perde: fatos descobertos, aprendizados, glossário, armadilhas, onde estão as coisas.
Não é estado da tarefa (isso vai em state/plan/progress). Preencha cedo — o hook avisa na faixa 1 (~50% do contexto).

Formato: `- AAAA-MM-DD HH:MM · fato|aprendizado|glossário|armadilha · texto`


- 2026-10-19 13:50 -0300 · fato · Spec inteira, conftest e fixture lidos. Base criada; 6/93 testes passam. Não há clientes nem reservas ainda.
- 2026-10-19 13:50 -0300 · armadilha · Semente única deve usar marcador persistente: esvaziar FAQ não autoriza importar a lista do JSON outra vez. Config geral é recarregada a cada início.
- 2026-10-19 13:50 -0300 · fato · Testes locais de HTTP e servidor falso funcionam neste ambiente; nenhuma rede externa foi chamada. Logs longos ficam nesta pasta; ler apenas últimas 30 linhas.
