"""Carteiras do Núcleo: carteiras-modelo trocáveis, sinais mensais, comparação lado a lado e backtest em USD ou BRL."""
import tempfile

import pandas as pd
import streamlit as st

from pwass.data import brasil
from pwass.engine import backtest, carteiras as C, strategies as S
from pwass.ui import cache, charts, components as ds, theme
from pwass.ui.theme import badge

ds.page_header("Carteiras do Núcleo", "Carteiras-modelo publicadas, com regras fixas. Escolha a sua, compare com as outras "
               "e veja o resultado em dólar ou em reais contra o CDI.", source="Yahoo Finance (ETFs ajustados), BCB (CDI)")

cfg = cache.config("estrategias")
models = {k: {**v, "id": k} for k, v in cfg["carteiras"].items()}

with st.spinner("Baixando histórico desde 2007..."):
    px = cache.prices(S.MODEL_TICKERS, "max")
    fx = cache.prices(("BRL=X",), "max")["BRL=X"]
m_all = S.monthly(px)
m = S.completed_months(m_all)               # só meses fechados = sinal oficial
partial = len(m_all) > len(m)
next_month = (m.index[-1] + pd.offsets.MonthEnd(1)).strftime("%m/%Y")

tab_models, tab_side, tab_gem, tab_gtaa, tab_exec = st.tabs(
    ["Carteiras-modelo", "Lado a lado", "Dual Momentum (GEM)", "GTAA · Ivy 5 (Faber)", "Como executar (UCITS)"])
fx_m = S.monthly(fx.to_frame())["BRL=X"]

# ------------------------------------------------------------------ Carteiras-modelo
with tab_models:
    keys = list(models)
    default = st.session_state.get("estrategia_ativa", cfg.get("padrao", keys[0]))
    active = st.selectbox("Minha estratégia do Núcleo", keys, index=keys.index(default),
                          format_func=lambda k: models[k]["nome"], key="estrategia_ativa",
                          help="Para fixar como padrão, altere 'padrao' em config/estrategias.yaml.")
    d = models[active]
    theme.note(f"<b>{d['nome']}</b> — {d['resumo']}<br><span style='color:var(--muted)'>Fonte: {d['fonte']}</span>")

    c1, c2 = st.columns([1, 2])
    core = c1.slider("Núcleo (% do patrimônio)", 70, 95, 85, 5,
                     help="O restante é o Satélite (ações individuais e cripto).")
    alloc = S.current_allocation(d, m)
    alloc["% do patrimônio"] = alloc["Peso"] * core
    c1.markdown(f"Satélite: **{100 - core}%** · máx. 5% por ação · máx. 5% em cripto")
    with c2:
        st.caption(f"Alocação-alvo para {next_month}" + (" (sinal do mês fechado)" if d["tipo"] == "tatica" else ""))
        st.dataframe(alloc, width="stretch", column_config={
            "Peso": st.column_config.ProgressColumn("Peso no Núcleo", min_value=0, max_value=1, format="percent"),
            "% do patrimônio": st.column_config.NumberColumn(format="%.1f%%")})

    st.markdown("#### Comparar")
    a, b, c = st.columns([3, 1, 1])
    pick = a.multiselect("Carteiras", keys, default=list(dict.fromkeys([active, "global_60_40", "gem", "sp500"])),
                         format_func=lambda k: models[k]["nome"])
    in_brl = b.toggle("Em reais (vs CDI)", value=True,
                      help="Converte pelo dólar do mês e compara com o CDI. É o que importa para quem vive no Brasil.")
    results = C.retornos({k: models[k] for k in pick}, m)
    if results:
        first = C.inicio_comum(results)
        years = list(range(first.year, m.index[-1].year))
        start_year = c.selectbox("Desde", years, index=0)
        start = max(first, pd.Timestamp(f"{start_year}-01-31"))
        rf = m["BIL"].pct_change()
        if in_brl:
            cdi = None
            try:
                cdi = backtest.cdi_monthly(cache.sgs(brasil.SGS["cdi_mes"], start="01/01/2007"))
                rf = cdi
            except Exception as e:  # noqa: BLE001
                st.caption(f"CDI indisponível agora: {e}")
            results = C.converter_brl(results, fx_m, cdi)
        results, end = C.recortar(results, start)
        met = pd.DataFrame({k: backtest.metrics(v, rf) for k, v in results.items()})
        fmt = C.formatar_metricas(met)
        st.dataframe(fmt, width="stretch")
        ccy = "R$" if in_brl else "US$"
        theme.note(f"Resultados em <b>{'reais' if in_brl else 'dólares'}</b>, de {start:%m/%Y} a {end:%m/%Y}, com "
                   "dividendos reinvestidos e rebalanceamento mensal. <b>Não inclui</b> custos, spread cambial, IOF nem "
                   "impostos (no Brasil, 15% ao ano sobre rendimentos no exterior pela Lei 14.754). "
                   + ("Em reais, a alta do dólar ajuda; o CDI é a régua honesta para quem mora aqui." if in_brl else ""))
        eq = pd.DataFrame({k: backtest.equity(v) for k, v in results.items()})
        st.plotly_chart(charts.lines(eq, f"Crescimento de {ccy} 100 (escala log)", log=True), width="stretch")
        dd = pd.DataFrame({k: backtest.drawdown(v) for k, v in results.items()})
        st.plotly_chart(charts.lines(dd, "Quedas a partir do topo", pct_axis=True, height=300), width="stretch")

        with st.expander("Relatório completo (QuantStats)"):
            st.caption("Gera um relatório HTML com dezenas de métricas, mapa de retornos mensais e comparação "
                       "com a referência. Abra o arquivo baixado no navegador.")
            name = st.selectbox("Carteira", list(results))
            bench = "CDI (renda fixa BR)" if in_brl and "CDI (renda fixa BR)" in results else None
            if st.button("Gerar relatório"):
                try:
                    import quantstats as qs  # import local: pacote pesado, só carrega se usar
                    bm = results[bench] if bench and bench != name else None
                    with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
                        qs.reports.html(results[name], benchmark=bm, output=tmp.name, title=f"PWASS · {name}",
                                        periods_per_year=12)
                        html = open(tmp.name, "rb").read()
                    st.download_button("Baixar relatório (.html)", html, file_name="relatorio-quantstats.html",
                                       mime="text/html")
                except Exception as e:  # noqa: BLE001
                    st.error(f"QuantStats falhou: {e}")

# ------------------------------------------------------------------ Lado a lado
with tab_side:
    pick2 = st.multiselect("Escolha 2 ou 3 carteiras", keys, default=["nucleo_conservador", "global_60_40", "gem"][:3],
                           max_selections=3, format_func=lambda k: models[k]["nome"], key="side_pick")
    brl2 = st.toggle("Em reais (vs CDI)", value=True, key="side_brl")
    if len(pick2) < 2:
        ds.empty_state("Escolha pelo menos 2 carteiras", "A comparação lado a lado precisa de 2 ou 3.")
    else:
        res2 = C.retornos({k: models[k] for k in pick2}, m)
        rf2 = m["BIL"].pct_change()
        if brl2:
            cdi2 = None
            try:
                cdi2 = backtest.cdi_monthly(cache.sgs(brasil.SGS["cdi_mes"], start="01/01/2007"))
                rf2 = cdi2
            except Exception as e:  # noqa: BLE001
                st.caption(f"CDI indisponível agora: {e}")
            res2 = C.converter_brl(res2, fx_m, cdi2)
        res2, end2 = C.recortar(res2, C.inicio_comum(res2))
        st.caption(f"Mesmo período para todas: {C.inicio_comum(res2):%m/%Y} a {end2:%m/%Y}, em {'reais' if brl2 else 'dólares'}.")
        cols = st.columns(len(pick2))
        for col, k in zip(cols, pick2):
            d = models[k]
            nm = d["nome"]
            with col, st.container(border=True):
                st.markdown(f"**{nm}**")
                st.caption(d["resumo"])
                al = S.current_allocation({**d, "id": k}, m)
                al = al.assign(Ativo=[S.NAMES.get(t, t) for t in al.index]).reset_index(names="ETF")
                ds.data_table(al[["ETF", "Ativo", "Peso"]], key=f"side_al_{k}",
                              column_config={"Peso": st.column_config.ProgressColumn("Peso", min_value=0, max_value=1, format="percent")})
                mt = backtest.metrics(res2[nm], rf2)
                ds.kpi_row([ds.kpi("Retorno a.a.", theme.pct(mt["Retorno a.a. (CAGR)"]), source="backtest (simulado)")])
                ds.kpi_row([ds.kpi("Pior queda", theme.pct(mt["Pior queda (máx. drawdown)"], 0), source="backtest (simulado)")])
                ds.kpi_row([ds.kpi("Sharpe", theme.num(mt["Sharpe"], 2), source="vs CDI" if brl2 else "vs T-Bills")])
        with ds.chart_container("Crescimento de 100 (escala log)", "Yahoo Finance, BCB · backtest mensal simulado", f"até {end2:%m/%Y}",
                                legend="Dividendos reinvestidos, rebalanceamento mensal; sem custos, spread cambial, IOF ou impostos."):
            st.plotly_chart(charts.lines(pd.DataFrame({k: backtest.equity(v) for k, v in res2.items()}), "", log=True),
                            width="stretch", key="side_eq")

# ------------------------------------------------------------------ GEM
with tab_gem:
    theme.note("<b>Gary Antonacci, <i>Dual Momentum Investing</i> (2014).</b> Uma vez por mês, compare o "
               "retorno de 12 meses de: ações EUA (SPY), ações ex-EUA (VEU) e T-Bills (BIL). "
               "<br>1) Se EUA rendeu menos que T-Bills → fique em renda fixa (AGG). "
               "<br>2) Senão → fique 100% no melhor entre EUA e ex-EUA.")
    g = S.gem_explain(m)
    theme.signal_box(f"Sinal oficial (mês fechado {g['date']:%m/%Y}) · vale para {next_month}",
                     f"{S.NAMES[g['pick']]} — {g['pick']} {badge('UCITS ' + g['ucits'], 'info')}",
                     g["why"])
    if partial:
        p = S.gem_explain(m_all)
        same = "igual ao oficial" if p["pick"] == g["pick"] else f"<b>mudaria para {p['pick']}</b>"
        theme.note(f"Prévia com preços de hoje: {same}. Só vale no fechamento do mês.", warn=p["pick"] != g["pick"])
    r = (g["returns"] * 100).rename(index=S.NAMES).to_frame("Retorno 12 meses (%)")
    st.dataframe(r.style.format("{:+.1f}"), width="content")
    hist = S.gem_weights(m).iloc[-12:].idxmax(axis=1).rename("Posição")
    st.caption("Últimos 12 sinais (troca de posição = 1 operação)")
    st.dataframe(hist.to_frame().T.rename(columns=lambda d: d.strftime("%m/%y")), width="stretch")

# ------------------------------------------------------------------ GTAA
with tab_gtaa:
    theme.note("<b>Mebane Faber, <i>A Quantitative Approach to Tactical Asset Allocation</i> (2007).</b> "
               "Cinco classes com 20% cada: ações EUA, ações ex-EUA, Treasuries 7–10 anos, imóveis e "
               "commodities. No fim de cada mês, a classe abaixo da sua média de 10 meses vai para caixa (T-Bills).")
    ex = S.gtaa_explain(m)
    invested = (ex["Sinal"] == "Manter").sum()
    theme.signal_box(f"Sinal oficial (mês fechado {m.index[-1]:%m/%Y}) · vale para {next_month}",
                     f"{invested} de 5 classes investidas · {5 - invested} em caixa",
                     "Cada classe = 20% da parte da carteira que segue o GTAA.")
    show = ex.copy()
    show["Distância"] = show["Distância"] * 100
    st.dataframe(show, width="stretch", column_config={
        "Preço": st.column_config.NumberColumn(format="%.2f"),
        "Média 10m": st.column_config.NumberColumn(format="%.2f"),
        "Distância": st.column_config.NumberColumn("Distância da média", format="%+.1f%%"),
        "Peso": st.column_config.NumberColumn(format="percent"),
    })
    if partial:
        prev = S.gtaa_explain(m_all)["Sinal"]
        changes = [t for t in ex.index if prev[t] != ex.loc[t, "Sinal"]]
        txt = ", ".join(changes) if changes else "nenhuma"
        theme.note(f"Prévia com preços de hoje — classes que mudariam de sinal: <b>{txt}</b>.", warn=bool(changes))

# ------------------------------------------------------------------ Execução
with tab_exec:
    theme.note("<b>Por que UCITS?</b> Para residentes no Brasil, ETFs domiciliados nos EUA (SPY, VTI, BIL...) "
               "contam para o <i>Estate Tax</i> americano (herança) acima de US$ 60 mil, com alíquota de até 40%, e "
               "sofrem 30% de retenção nos dividendos. ETFs irlandeses (UCITS, listados em Londres) dão a mesma "
               "exposição sem Estate Tax e com 15% de retenção dentro do fundo. Os sinais e backtests usam os ETFs "
               "americanos (histórico mais longo); a execução pode ser no equivalente UCITS.", warn=True)
    rows = [{"Sinal (EUA)": t, "Classe": S.NAMES.get(t, t), "Equivalente UCITS": u}
            for t, u in S.UCITS.items()]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Confira na sua corretora a linha em USD e a versão de acumulação (Acc). "
               "Alguns ETFs têm linhas em GBP/GBp na mesma bolsa.")
