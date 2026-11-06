# Progresso do redesign v5

Branch de trabalho desta sessão: `claude/confident-euler-7jpavc` (o prompt cita `redesign-v5`; a plataforma designou esta branch e foi mantida).

## Sessão 1 — Auditoria, plano e Design System: **concluída**
Feito:
- `AUDITORIA.md`, `PLANO.md`, `DESIGN-SYSTEM.md`, `PENDENCIAS.md`.
- `pwass/ui/tokens.py` (tokens, séries, escalas) + `.streamlit/config.toml` com `[theme.light]`/`[theme.dark]` e sidebar; `theme.py` sem `st._config` (modo via `st.context.theme.type`, `?tema=` como override).
- `pwass/ui/components.py` (12 componentes com estados) e página oculta `/componentes`.
- `app.py`: menu em seções novas, topbar com busca global (abre Ativo), status NYSE/B3 (`pwass/engine/mercado.py`), seletor de estratégia só no Painel, dica de tema.
- Séries de `tvchart.py`/`charts.py` lidas de `tokens.SERIES`; hex removidos das páginas.
- `.gitignore` criado (não existia — ver AUDITORIA #2).

Testes: `pytest` 118 verdes (31 antigos + tokens/contraste, config, mercado, smoke `_componentes`, hex em páginas, badge). Smoke `AppTest` do `app.py` em todas as 9 páginas × 2 temas, sem exceção. Nenhum arquivo de cálculo existente foi alterado (regressão numérica preservada por construção; fixtures vêm na Sessão 2).

Checklist manual: busca global (selectbox renderiza; navegação testada só em AppTest) · troca de tema pelo menu **não verificada** (ver PENDENCIAS) · mobile e exportação não verificados nesta sessão.

## Sessão 2 — Painel + Ativo + Scanner: **concluída**
Feito:
- **Regressão numérica primeiro:** fixtures reais (`tests/fixtures/ohlcv_swing.parquet`, `precos_carteiras.parquet`: SPY, QQQ, AAPL, GLD até 05/11/2026 + 8 ETFs mensais) e `golden.json` (3 estratégias × 4 ativos, GEM e GTAA) gerados com o código ANTES de qualquer mudança; `tests/test_regressao.py` compara. Nenhum arquivo de cálculo existente (`swing.py`, `backtest.py`, `strategies.py`...) foi alterado.
- `indicators.py`: MACD, pivôs clássicos, pivôs de swing (com data de confirmação, sem olhar o futuro) e suporte/resistência, com testes.
- **Painel**, **Ativo** (6 abas) e **Scanner** (10 filtros, chips, CSV/Excel, clique abre o Ativo) refeitos no Design System; detalhes em `MUDANCAS.md`. `paginas/mercado.py` removida.
- Novos puros/testados: `engine/mercado.py` (+amplitude/percentil/novidades), `engine/ativo.py`, `engine/screener.py`.
- Verificação visual em Chromium (Painel dark/light desktop, Painel mobile, Ativo): ok; corrigidos 5A vazio no Ativo, sidebar cobrindo o conteúdo no celular, fonte duplicada no cabeçalho do Painel.

Testes: `pytest` **130 verdes**. Smoke `AppTest` das 9 páginas × 2 temas sem exceção com dados reais (`scripts/smoke_paginas.py`); Scanner exercitado com clique em "Rodar" (25 linhas, 22 colunas). Yahoo `.info`/calendário/notícias ficam intermitentes (401/429) neste ambiente: as telas mostram "—" com motivo.

Limitações conhecidas (ver PENDENCIAS.md): filtros salvos e ★ dependem do store (Sessão 4); troca de tema ao vivo ainda sem verificação manual; Ativo/Scanner não conferidos em 390 px; screenshots oficiais só na Sessão 6.

## Sessão 3 — Laboratório + Carteiras + Zonas + Analista IA: **concluída**
Feito (detalhes em `MUDANCAS.md`): Laboratório de swing (nova), Carteiras do Núcleo com aba Lado a lado, Zonas de entrada com plano e justificativa, Analista IA com formato fixo e validação. Menu atualizado (`estrategias.py` → `carteiras.py`).
Testes: `pytest` **143 verdes** (novos: lab, carteiras, zonas, estruturada). `scripts/smoke_paginas.py`: 10 páginas × 2 temas sem exceção, com dados reais. Fluxo da IA exercitado com resposta SIMULADA (sem chave aqui) — o detector pegou o número inventado de propósito. Verificação visual (Chromium): Laboratório dark e Zonas light ok; corrigidos: cores inconsistentes entre curva e drawdown, R/R com ponto decimal, linhas S/R em excesso.
Achado importante: `?tema=` só muda o CSS próprio (não o tema nativo) → não é fallback real para a troca de tema (ver PENDENCIAS).
Limitações: ver PENDENCIAS (operações reais, persistência da IA, checagem de números, mobile do Laboratório/Zonas/Carteiras não conferido).

## Próxima ação exata
**Sessão 4** (PROMPT §12): (1) `pwass/store.py` com interface `get/put/list/delete` por coleção, backend local (`data/*.local.json`, já no `.gitignore`) e Supabase opcional (`SUPABASE_URL`/`SUPABASE_KEY`), `docs/redesign/supabase.sql` com RLS, backend ativo visível; testes do store local. (2) **Watchlist** (múltiplas listas, ★ no `asset_header` do Ativo, sinais e variações) e **Alertas** (preço, variação, RSI, cruzamento, rompimento, volume, sinal de estratégia) em página única "Alertas e watchlist" com popover real de contagem na topbar; verificação no GitHub Actions (junto de `radar-diario.yml`), Telegram/e-mail opcionais. (3) **Comparar** (2–4 ativos, base 100, datas alinhadas cripto × bolsa, vol./drawdown/correlação). (4) **Diário de operações reais** (entrada, saída, motivo; "o que fiz × o que a regra mandava") e ligar ao Laboratório com rótulo próprio. (5) Migrar análises da IA e filtros do Scanner para o store. (6) Atualizar PROGRESSO e commitar.
