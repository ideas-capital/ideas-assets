# Design System v5

Catálogo ao vivo: abra `/componentes` (página oculta). Fonte única de cores/escalas: `pwass/ui/tokens.py`; `.streamlit/config.toml` espelha esses valores (teste garante).

## Tokens
| Token | Dark | Light |
|---|---|---|
| bg / bg2 / surface / surface_raised | #0B1019 / #101827 / #151D2B / #1B2638 | #F5F7FA / #FFFFFF / #FFFFFF / #F1F5F9 |
| border | #263247 | #E2E8F0 |
| text / text_muted | #F1F5F9 / #94A3B8 | #172033 / #5B6B82 |
| primary / primary_text | #2563EB / #60A5FA | #2563EB / #2563EB |
| up / down | #10B981 / #F87171 | #047857 / #CC2222 |
| warn / indicator | #F59E0B / #C084FC | #B45309 / #9333EA |
| grid | #1A2333 | #EEF2F6 |

Ajustes vs. prompt (para WCAG AA): dark `down` e `indicator` mais claros; light `up`, `down` e `text-muted` mais escuros.
**Séries de gráfico** (iguais nos dois temas, ≥3:1 em ambos os fundos): MM20 #3B82F6 · MM50 #EA580C · MM200 #A855F7 · Bollinger #6B7A90 · RSI #A855F7 · candle alta #059669 · baixa #EF4444. (MM50, Bollinger e candle de alta ficaram um pouco mais escuros que no prompt para passar no fundo branco.)

Escalas: tipografia 24/18/14/14/12, KPI 26 px com `tabular-nums`; espaçamento 4·8·12·16·24·32·48; raio 6/10; sombra só no claro; breakpoints 1280/768.

## Componentes (`pwass/ui/components.py`)
Todos aceitam `state` ∈ normal | loading | empty | error quando fazem sentido.
| Função | Uso |
|---|---|
| `page_header(título, sub, source, asof)` | cabeçalho de página, com fonte/atualização |
| `topbar(data_asof, n_alerts)` | busca global (ticker livre aceito) + "Dados de:" |
| `kpi(label, value, delta, spark, source)` + `kpi_row` | indicador com variação e sparkline |
| `ticker_strip(items)` | faixa de cotações |
| `asset_header(...)` | ticker, nome, mercado, classe, preço, variação, horário |
| `badge(status)` | COMPRA · PERTO · EM POSIÇÃO · AGUARDAR · EVITAR · SAIR (status inválido = erro) |
| `origin_tag(kind)` | observado · calculado · simulado · ia |
| `data_table(df, column_config, on_select_open_asset, export_name)` | `st.dataframe` + CSV; seleção abre o Ativo |
| `chart_container(...)` | título, controles, legenda e fonte |
| `insight_card(observado, interpretação, limitação)` | padrão de insight |
| `chips`, `empty_state`, `error_state`, `loading_state`, `source_note` | auxiliares |

Formatação (`theme.py`): `pct`, `num`, `money(x, cur="US$")`; ausente → `—`.
Regras: cor só por token/`var(--…)`; todo número com fonte e data; ausente = `—`.
