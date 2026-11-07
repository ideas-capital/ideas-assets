"""Laboratório de swing — as 3 estratégias numa página: ficha, métricas, gráficos e comparação.

Tudo aqui é BACKTEST (simulado): sinal no fechamento, execução na abertura seguinte, custos incluídos.
Operações reais (diário) entram na Sessão 4 e terão rótulo e cor próprios.
"""
import pandas as pd
import streamlit as st

from pwass.engine import lab, swing as S
from pwass.ui import cache, charts, components as ds, theme
from pwass.ui.theme import num, pct

sw = cache.config("swing")
risk = sw["risco"]
names = {t: (n, g) for g, d in sw["universo"].items() for t, n in d.items()}

ds.page_header("Laboratório de swing", "Três regras fixas, backtest honesto e comparação lado a lado. "
               f"Capital de laboratório US$ {num(risk['capital_laboratorio_usd'], 0)}, risco {risk['risco_por_operacao'] * 100:g}% por operação.")

with st.spinner("Carregando candles e rodando os backtests..."):
    data = cache.ohlcv(tuple(names), "10y")
asof = max(d.index[-1] for d in data.values())
src = "Yahoo Finance (diário, preços ajustados) · backtest simulado"

st.markdown(f'{ds.origin_tag("simulado")} <span class="ds-src">Todos os números desta página são simulações sobre dados históricos. '
            "Resultado passado não garante resultado futuro.</span>", unsafe_allow_html=True)
theme.note("<b>Viés de sobrevivência:</b> o universo é a lista atual de ativos líquidos (inclui vencedores recentes e não inclui "
           "o que deixou de existir). Isso tende a inflar os resultados de todas as regras. Compare sempre com o buy & hold "
           "do mesmo universo.", warn=True)

tab_uma, tab_cmp = st.tabs(["Uma estratégia", "Comparar as 3"])

# ------------------------------------------------------------------ uma estratégia
with tab_uma:
    sids = list(sw["estrategias"])
    a, b = st.columns([2, 2], vertical_alignment="bottom")
    sid = a.segmented_control("Estratégia", sids, default=st.session_state.get("estrategia_swing", sw.get("padrao", sids[0])),
                              format_func=lambda k: sw["estrategias"][k]["curto"], key="lab_sid") or sw.get("padrao")
    order = [t for t in names if t in data]
    tk = b.selectbox("Ativo", order, index=order.index("SPY") if "SPY" in order else 0,
                     format_func=lambda t: f"{t} · {names[t][0]}", key="lab_tk")
    p = sw["estrategias"][sid]

    with st.container(border=True):
        st.markdown(f"**{p['nome']}**")
        st.markdown(p["descricao"])
        params = {k: v for k, v in p.items() if k not in ("nome", "curto", "descricao", "fonte")}
        st.markdown(ds.source_note(p["fonte"]), unsafe_allow_html=True)
        ds.chips([f"{k}: {v}" for k, v in params.items()] +
                 ["Timeframe: diário", f"Custo: {risk['custo_por_lado'] * 100:.2f}% por lado", "Execução: abertura seguinte",
                  f"Stop inicial: {risk['multiplo_atr_stop']:g}× ATR", f"Alvos: {', '.join(f'{x:g}R' for x in risk['alvos_em_r'])}"])

    df = data[tk]
    bt = S.backtest(df, sid, p, risk["custo_por_lado"], risk["multiplo_atr_stop"])
    st_ = S.stats(bt, S.periods_per_year(df.index))
    exp_src = "backtest (simulado)"
    ds.kpi_row([ds.kpi("Taxa de acerto", pct(st_["Taxa de acerto"], 0, False), source=exp_src),
                ds.kpi("Profit factor", num(st_["Profit factor"], 2), source=exp_src),
                ds.kpi("Retorno acumulado", pct((1 + bt.daily).prod() - 1, 0), source=f"{st_['Anos']:.1f} anos, com custos"),
                ds.kpi("Máx. queda", pct(st_["Máx. queda estratégia"], 0), source=exp_src),
                ds.kpi("Operações", str(st_["Operações"]), source=exp_src)])
    ds.kpi_row([ds.kpi("Resultado médio/op.", pct(st_["Resultado médio"], 2), source=exp_src),
                ds.kpi("Ganho médio", pct(st_["Ganho médio"], 1), source=exp_src),
                ds.kpi("Perda média", pct(st_["Perda média"], 1), source=exp_src),
                ds.kpi("Exposição", pct(st_["Tempo posicionado"], 0, False), source="% do tempo posicionado"),
                ds.kpi("Buy & hold a.a.", pct(st_["CAGR buy & hold"]), source="mesmo período, sem custos")])
    st.caption(f"Retorno a.a. da regra {pct(st_['CAGR estratégia'])} considera o período inteiro, inclusive o tempo fora do mercado. "
               f"Diferença para o buy & hold: {pct(st_['CAGR estratégia'] - st_['CAGR buy & hold'])} ao ano.")

    eq = pd.DataFrame({"Estratégia": (1 + bt.daily).cumprod(), "Buy & hold": (1 + bt.bh).cumprod()})
    with ds.chart_container(f"{tk} · estratégia vs buy & hold (US$ 1 investido, escala log)", src, f"{asof:%d/%m/%Y}"):
        st.plotly_chart(charts.equity_vs({c: eq[c] for c in eq}, ""), width="stretch", key="lab_eq")
        st.plotly_chart(charts.drawdown_fig({c: eq[c] for c in eq}), width="stretch", key="lab_dd")
    g1, g2 = st.columns(2)
    with g1, ds.chart_container("Distribuição dos resultados por operação", src, f"{asof:%d/%m/%Y}"):
        if len(bt.trades):
            st.plotly_chart(charts.histogram(bt.trades["Retorno"], ""), width="stretch", key="lab_hist")
        else:
            ds.empty_state("Sem operações", "A regra não gerou sinais neste ativo.")
    with g2, ds.chart_container("Retorno por ano (regra vs buy & hold)", src, f"{asof:%d/%m/%Y}"):
        st.plotly_chart(charts.bars_by_year({"Estratégia": lab.retorno_por_ano(bt.daily), "Buy & hold": lab.retorno_por_ano(bt.bh)}, ""),
                        width="stretch", key="lab_ano")
    if len(bt.trades):
        ds.data_table(bt.trades.iloc[::-1], key="lab_trades", export_name=f"trades_{tk}_{sid}",
                      column_config={"Retorno": st.column_config.NumberColumn(format="percent"),
                                     "Preço entrada": st.column_config.NumberColumn(format="%.2f"),
                                     "Preço saída": st.column_config.NumberColumn(format="%.2f")},
                      source="Backtest (simulado)", asof=f"{asof:%d/%m/%Y}")

    # ---- operações reais neste ativo (diário), separadas do backtest
    try:
        reais = [o for o in cache.store().list("diario") if o["ticker"] == tk and o["estrategia"] == sid]
    except Exception:  # noqa: BLE001
        reais = []
    st.markdown(f'#### Operações reais em {tk} {ds.origin_tag("real")}', unsafe_allow_html=True)
    if reais:
        ds.data_table(pd.DataFrame([{"Entrada": o["entrada_data"], "Preço entrada": o["entrada_preco"], "Saída": o["saida_data"] or "aberta",
                                     "Preço saída": o.get("saida_preco"), "Resultado (bruto)": (o["saida_preco"] / o["entrada_preco"] - 1) if o.get("saida_preco") else None,
                                     "Motivo": o.get("motivo") or ""} for o in sorted(reais, key=lambda o: o["entrada_data"], reverse=True)]),
                      key="lab_reais", source="Diário (real, sem custos) — comparação completa em Diário de operações",
                      column_config={"Resultado (bruto)": st.column_config.NumberColumn(format="percent")})
    else:
        ds.empty_state("Nenhuma operação real registrada neste ativo e regra", "Registre no Diário de operações para comparar com o backtest acima.")

# ------------------------------------------------------------------ comparar
with tab_cmp:
    with st.spinner("Comparando as 3 estratégias no universo..."):
        tab, curvas = lab.comparar(data, sw)
    ds.chips([f"Universo: {len(data)} ativos", "Diário", f"Custo {risk['custo_por_lado'] * 100:.2f}% por lado"])
    show = tab.drop(columns=["id"])
    ds.data_table(show, key="lab_cmp", export_name="comparacao_estrategias",
                  column_config={"Taxa de acerto": st.column_config.NumberColumn(format="percent"),
                                 "Profit factor": st.column_config.NumberColumn(format="%.2f"),
                                 "Resultado médio": st.column_config.NumberColumn(format="percent"),
                                 "Ganho médio": st.column_config.NumberColumn(format="percent"),
                                 "Perda média": st.column_config.NumberColumn(format="percent"),
                                 "Exposição média": st.column_config.NumberColumn(format="percent"),
                                 "a.a. regra (média dos ativos)": st.column_config.NumberColumn(format="percent"),
                                 "a.a. buy & hold (média dos ativos)": st.column_config.NumberColumn(format="percent"),
                                 "Pior queda (média dos ativos)": st.column_config.NumberColumn(format="percent")},
                  source=src, asof=f"{asof:%d/%m/%Y}")
    with ds.chart_container("Curvas de capital: média simples dos ativos (escala log)", src, f"{asof:%d/%m/%Y}",
                            legend="Capital repartido igualmente entre os ativos disponíveis e rebalanceado todo dia: régua de "
                                   "comparação, não uma carteira executável."):
        st.plotly_chart(charts.equity_vs(curvas, "", height=340), width="stretch", key="lab_cmp_eq")
        st.plotly_chart(charts.drawdown_fig(curvas, "Queda a partir do topo", 220), width="stretch", key="lab_cmp_dd")
