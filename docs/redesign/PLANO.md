# Plano do redesign v5

## Navegação final (alvo)
Visão geral: Painel · Radar de mercado · Análise: Ativo · Scanner · Comparar* · Zonas de entrada · Estratégias: Laboratório de swing* · Carteiras do Núcleo · Inteligência: Analista IA · Alertas e watchlist* · Sistema: Relatórios* · Configurações e fontes* · Guia. (*novo)

Estado após a Sessão 1: seções e rótulos já aplicados às páginas existentes; as novas entram nas sessões indicadas.

## Arquivos
| Ação | Arquivo | Sessão |
|---|---|---|
| criado | `pwass/ui/tokens.py`, `pwass/ui/components.py`, `paginas/_componentes.py`, `pwass/engine/mercado.py`, `.streamlit/config.toml`, `.gitignore`, testes | 1 |
| alterado | `app.py`, `pwass/ui/theme.py`, `charts.py`, `tvchart.py`, `paginas/ativo.py` (lê `?t=`), `estrategias.py`/`mercado.py` (hex) | 1 |
| alterar | `terminal.py` → Painel; `ativo.py` (abas, MACD, pivôs); `scanner.py` (filtros/chips/exportação); `radar_ativos.py` | 2 |
| criar/fundir | Laboratório de swing (de `estrategias.py`), Carteiras, Zonas, Analista IA (formato fixo) | 3 |
| criar | `pwass/store.py`, Watchlist, Comparar, Alertas, Diário, `supabase.sql`, workflow de alertas | 4 |
| criar | Relatórios (PDF/XLSX), `config/score.yaml` + `SCORE.md` (só se validar), Configurações/Fontes, Guia | 5 |
| descontinuado | `paginas/mercado.py` — removida na Sessão 2 (ver MUDANCAS.md) | 2 |
| migrar | `theme.card/cards/table/signal_box` → `components.*` conforme cada página é refeita; aliases v4 em `tokens.LEGACY` saem no fim | 2–6 |

## Decisões
1. **Tema:** nativo (`[theme.light/dark]`) + `st.context.theme.type`; `?tema=light|dark` na URL força o modo (testes/screenshots). Sem seletor próprio.
2. **Topbar** montada em `app.py` (uma vez, topo de todas as páginas), não em cada página.
3. **Botões sem ação não são exibidos:** `asset_header` não mostra ★ até existir watchlist (Sessão 4); alertas só mostram contagem se houver fonte real.
4. **Dependências:** nenhuma nova (`python-dateutil` já vem com o pandas).
5. **Regressão numérica:** nenhum arquivo de `pwass/engine/{swing,backtest,strategies,...}` foi alterado; fixtures de regressão serão gravadas na Sessão 2 antes de qualquer mudança em engine.
