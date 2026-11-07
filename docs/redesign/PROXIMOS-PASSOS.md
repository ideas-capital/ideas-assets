# Próximos passos

Ordem sugerida, do que destrava mais valor para o que depende de decisão sua.

## Verificar no app publicado (precisa de você)
1. **Troca de tema pelo menu ⋮ → Settings → Theme**: confirmar que a tela re-renderiza sem recarregar e que a escolha persiste. Se não re-renderizar, decidir por um seletor próprio (o `?tema=` NÃO serve: só muda o CSS próprio).
2. **Supabase real**: criar o projeto, rodar `docs/redesign/supabase.sql`, colocar `SUPABASE_URL` e `SUPABASE_KEY` (service_role) nos secrets do Streamlit e do GitHub, e conferir watchlists/alertas/diário.
3. **Telegram**: criar o bot, definir `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` nos secrets do GitHub e rodar o workflow `alertas` manualmente (workflow_dispatch).
4. **Logo**: enviar `assets/logo.svg`; o app já usa `st.logo()` quando o arquivo existir.

## Pendências técnicas
- Recriar os workflows `radar-diario.yml` e `relatorio-mensal.yml` (descritos no GUIA, ausentes do repositório; os scripts existem).
- Alertas por e-mail (só Telegram existe).
- Fonte Inter no PDF (exige empacotar TTF); hoje usa Helvetica.
- Casas decimais das tabelas nativas seguem o idioma do navegador.
- Reavaliar o score (`python scripts/validar_score.py`) quando houver mais dados; hoje reprovado.
- Aviso de log do Streamlit ao carregar filtro salvo do Scanner (valor padrão + session_state); só cosmético.

## Roadmap do produto (CLAUDE.md)
1. Módulo de carteira (posições locais, limites do Satélite, rebalanceamento) — o diário e o store já existem como base.
2. Módulo fiscal (Lei 14.754, custo médio do dólar) — o diário mostra resultado bruto por isso.
3. Protocolo de Emergência / sucessão (local, cifrado).
4. Fundamentos oficiais via edgartools (XBRL da SEC), para reduzir a dependência do `.info` instável do Yahoo.
