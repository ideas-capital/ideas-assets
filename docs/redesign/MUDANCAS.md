# Mudanças do redesign v5

## Sessão 1
Design System (`tokens.py`, `components.py`, `/componentes`), temas nativos no `config.toml`, topbar com busca, status NYSE/B3, `.gitignore`. Detalhes em PROGRESSO.md e AUDITORIA.md.

## Sessão 2
**Páginas reformuladas**
- **Painel** (`terminal.py`): faixa configurável (`config/painel.yaml`, 10 itens), inteligência de mercado (regime, amplitude, VIX com percentil, resultados da semana), sinal do dia, gráfico + métricas da regra, tabela de oportunidades (`data_table`, linha abre o Ativo), "o que mudou" (novos setups, saídas, cruzamentos da MM200) e resumo de mercado por IA.
  - Removido: aba "Todas as classes" (o Radar de mercado já cobre), cartões HTML da faixa antiga.
- **Ativo** (`ativo.py`): cabeçalho, abas Visão geral · Técnica (MACD, Fibonacci, suporte/resistência por pivôs, intervalo e período) · Fundamentos (por classe: ação, ETF, outros) · Histórico (3 regras neste ativo) · Notícias e eventos (Yahoo + SEC) · IA.
- **Scanner** (`scanner.py`): 10 filtros combináveis + chips + CSV/Excel; clicar na linha abre o Ativo (substitui o seletor "Abrir Raio-X").
- `paginas/mercado.py` **removida** (já estava fora do menu): macro FRED vive no Radar de mercado, o resumo de IA foi para o Painel e o gráfico comparativo será a página **Comparar** (Sessão 4).

**Novos módulos:** `engine/mercado.py` (amplitude, percentil, novidades), `engine/ativo.py` (classe, performance), `engine/screener.py`, `indicators.macd/pivot_points/swing_pivots/support_resistance`, `market.news/earnings_calendar`.
**Dependências:** nenhuma nova (`openpyxl` já estava no requirements).
**Alterados:** `tvchart.render` aceita `levels` e painéis MACD/SR; `INFO_KEYS` ganhou `aum` e `expense_ratio`; `app.py` usa `initial_sidebar_state="auto"` (no celular a sidebar abria por cima do conteúdo).
