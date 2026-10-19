# Plano

## Estratégia atual
Critérios automatizados concluídos: v0.7.0, 93 passed e LIMITES OK. Não iniciar novas funcionalidades sem demanda.

## Próximos 3 passos
1. Humano: executar verificar-independente.py para restaurante alternativo, build Docker e healthcheck do container (nível 4).
2. Humano: revisar `/` e `/equipe` e configurar restaurante, fuso e credenciais somente no ambiente destinado à operação, seguindo README.
3. Se surgir falha concreta, registrar evidência e fazer correção mínima; repetir suíte completa e limites. Deploy permanece com o operador, commit com o loop externo.
