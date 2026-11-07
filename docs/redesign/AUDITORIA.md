# Auditoria — estado v4 (Sessão 1, 06/11/2026)

Método: leitura de `app.py`, `pwass/ui/*`, `paginas/*`, configs e testes; execução do `pytest` (31 testes verdes) e do app em AppTest e em Chromium (Playwright).

## Achados objetivos
| # | Achado | Impacto | Ação |
|---|---|---|---|
| 1 | `theme.apply_theme()` usava `st._config.set_option` (API privada, global ao processo). Dois navegadores abertos brigavam pelo tema. | Alto | **Corrigido:** removido; tema vem de `[theme.light/dark]` + `st.context.theme.type`. |
| 2 | Não existia `.gitignore`, embora o CLAUDE.md afirme que `secrets.toml`, `*.local.yaml`, `vault/` e `exports/` estão ignorados. | **Alto (segurança)** | **Corrigido:** `.gitignore` criado. |
| 3 | Tokens v4 sem contraste validado; `muted` claro (#6A7187) ≈ 4,4:1 sobre o fundo. | Médio | **Corrigido:** `tokens.py` + teste WCAG AA (79 casos). |
| 4 | Cores hex em páginas (`#64748B` em `estrategias.py` e `mercado.py`) e em gráficos (MM50/MM200/RSI/Bollinger em `tvchart.py`; paleta própria em `charts.py`). | Médio | **Corrigido:** páginas via `var(--muted)`; séries em `tokens.SERIES`; teste de grep. |
| 5 | Logo "IC" com gradiente (contra §3.4). | Baixo | Corrigido (cor sólida). `assets/logo.*` não existe → mantida a marca (ver PENDENCIAS). |
| 6 | Menu com seções/rotulagem diferentes da proposta; seletor de estratégia aparecia em todas as páginas. | Baixo | Seções renomeadas; seletor só no Painel. |
| 7 | Seletor "Tema escuro" na sidebar dependia do item 1. | Médio | Removido; dica de onde trocar no menu nativo. |
| 8 | Sem busca global, sem indicação de "dados de" nem status de pregão. | Médio | **Criados:** `topbar`, `pwass/engine/mercado.py` (NYSE/B3, testado). |
| 9 | `mercado.py` fora do menu e sobreposto ao Painel/Radar. | Baixo | Decisão no PLANO (fundir na Sessão 2). |
| 10 | Páginas importam `pwass.engine` direto (ex.: `ativo.py`) e calculam/combinam dados na própria tela, contra §2.3. | Médio | Tratar página a página nas Sessões 2–3. |
| 11 | Tabelas HTML (`theme.table`) coexistem com `st.dataframe`. | Baixo | `data_table` é o padrão; HTML só para badges. |
| 12 | Backtests e motores sem fixtures de regressão. | Médio | Criar fixtures antes de mexer em `swing.py`/`backtest.py` (Sessão 2, antes da primeira alteração de engine). |

## Ambiente
Yahoo, BCB e SEC responderam (HTTP 200). **FRED CSV não respondeu** neste ambiente (bloqueio de rede da sessão, não necessariamente do app). Testes que dependem do FRED devem usar fixtures.
