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

## Próxima ação exata
**Sessão 2** (PROMPT §12): (1) gravar fixtures de regressão (`tests/fixtures/`) e teste de números de swing/carteiras ANTES de tocar engine; (2) refazer o **Painel** (`terminal.py`) com `ticker_strip`, `kpi`, regime/amplitude/VIX, ativo em destaque, oportunidades, insights, fundindo o que servir de `mercado.py`; (3) **Ativo** em abas (+MACD e pivôs em `pwass/engine/indicators.py` com teste); (4) **Scanner** com filtros combináveis, chips e exportação via `data_table`; (5) migrar `theme.card/cards` nessas páginas; (6) atualizar este arquivo e commitar.
