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

## Próxima ação exata
**Sessão 3** (PROMPT §12): (1) **Laboratório de swing** (`paginas/laboratorio.py`, novo): seletor de estratégia, ficha (regras, custos, fonte), métricas completas (inclui exposição e média de ganho/perda), curva de capital, drawdown, histograma por operação, retorno por ano, comparação das 3 estratégias, aviso de viés de sobrevivência; separar BACKTEST de operações reais com `origin_tag`. Extrair o que for cálculo para `pwass/engine/` com teste (sem mudar regras — a regressão deve continuar verde). (2) **Carteiras do Núcleo** (de `estrategias.py`) no novo padrão + comparação lado a lado de 2–3 carteiras. (3) **Zonas de entrada** (`radar.py`) com zonas sobre o gráfico, justificativa e dado de origem. (4) **Analista IA** com formato fixo (Dados observados · Interpretação · Hipóteses · Decisão sem % · Riscos), JSON de entrada com data, modelo/custo/data. (5) Atualizar o menu do `app.py`, este arquivo, e commitar.
