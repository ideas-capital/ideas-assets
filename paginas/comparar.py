"""Comparar ativos: 2 a 4 ativos, mesma janela, base 100, datas alinhadas (cripto × bolsa)."""
import pandas as pd
import streamlit as st

from pwass.engine import comparar as C
from pwass.ui import cache, charts, components as ds, theme

ds.page_header("Comparar ativos", "Desempenho normalizado (base 100), volatilidade, queda e correlação no mesmo período.",
               source="Yahoo Finance (preços ajustados, diário)")

opts = ds.universe_options()
default = [t for t in ("SPY", "QQQ", "GLD") if t in opts]
pick = st.multiselect("Ativos (2 a 4)", list(opts), default=default, max_selections=4, accept_new_options=True,
                      format_func=lambda k: opts.get(k, k), key="cmp_pick")
pick = [str(p).strip().upper() for p in pick]
per = st.segmented_control("Período", ["6M", "1A", "3A", "5A", "10A"], default="3A", key="cmp_per") or "3A"

if len(pick) < 2:
    ds.empty_state("Escolha pelo menos 2 ativos", "A comparação precisa de 2 a 4 ativos.")
    st.stop()

with st.spinner("Carregando cotações..."):
    try:
        raw = cache.ohlcv(tuple(pick), "10y")
    except Exception as e:  # noqa: BLE001
        ds.error_state("Não consegui baixar as cotações", str(e), "Tente de novo em instantes.")
        st.stop()
faltam = [t for t in pick if t not in raw]
if faltam:
    ds.error_state("Sem cotações para: " + ", ".join(faltam), "O Yahoo não retornou dados (confira o ticker; B3 usa .SA).")
    st.stop()

closes = {t: raw[t]["Close"] for t in pick}
fim = min(s.index[-1] for s in closes.values())
anos = {"6M": 0.5, "1A": 1, "3A": 3, "5A": 5, "10A": 10}[per]
ini = fim - pd.DateOffset(months=int(anos * 12))
closes = {t: s[(s.index >= ini) & (s.index <= fim)] for t, s in closes.items()}
df, info = C.alinhar(closes)
if len(df) < 30:
    ds.error_state("Histórico em comum curto demais", f"Só {len(df)} datas em comum no período escolhido.", "Escolha um período maior ou outros ativos.")
    st.stop()

ds.chips([f"{len(df)} datas em comum", f"{info['inicio']:%d/%m/%Y} a {info['fim']:%d/%m/%Y}", f"Volatilidade anualizada com {info['ppy']} períodos/ano"])
if info["misto"]:
    theme.note("Os ativos têm calendários diferentes (por exemplo, cripto negocia 7 dias por semana e ações só em dias úteis). "
               "Para não distorcer correlação e volatilidade, só entram as datas em que <b>todos</b> negociaram: "
               + ", ".join(f"{t}: {n} dias descartados" for t, n in info["descartados"].items() if n) + ".", warn=True)

b100 = C.base100(df)
with ds.chart_container("Desempenho (base 100)", "Yahoo Finance (preços ajustados)", f"{info['fim']:%d/%m/%Y}",
                        legend="Todos começam em 100 na primeira data em comum."):
    st.plotly_chart(charts.lines(b100, "", height=340), width="stretch", key="cmp_b100")
    st.plotly_chart(charts.drawdown_fig({c: df[c] for c in df}, "Queda a partir do topo", 200, paleta=True), width="stretch", key="cmp_dd")

met = C.metricas(df, info["ppy"]).reset_index(names="Ativo")
ds.data_table(met, key="cmp_met", export_name="comparacao_ativos", source="Calculado pelo app", asof=f"{info['fim']:%d/%m/%Y}",
              column_config={c: st.column_config.NumberColumn(format="percent") for c in met.columns if c != "Ativo"})
st.markdown("##### Correlação dos retornos diários")
cor = C.correlacao(df)
ds.data_table(cor.reset_index(names="Ativo"), key="cmp_cor", source="Calculado pelo app (retornos diários nas datas em comum)",
              column_config={c: st.column_config.NumberColumn(format="%.2f") for c in cor.columns})
st.caption("Correlação perto de 1 = andam juntos (pouca diversificação); perto de 0 = independentes; negativa = tendem a se opor. "
           "Muda com o período: não é constante.")
