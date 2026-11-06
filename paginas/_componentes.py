"""Página oculta (/componentes): catálogo visual do Design System em todos os estados.

Os números abaixo são EXEMPLOS DE LAYOUT, rotulados como tal — nunca dados de mercado.
"""
import pandas as pd
import streamlit as st

from pwass.ui import components as ds
from pwass.ui import theme, tokens
from pwass.ui.theme import money, num, pct

ds.page_header("Design System · componentes", "Checagem visual dos dois temas e dos estados de cada componente.",
               source="exemplo de layout (sem dados reais)", asof="v5")
st.caption(f"Tema ativo: **{theme.mode()}**. Troque pelo menu ⋮ → Settings → Theme.")

EX = [100, 101, 99.5, 102, 103.5, 102.8, 105]  # série fictícia só para desenhar a sparkline

st.subheader("Tokens")
t = tokens.THEMES[theme.mode()]
st.markdown('<div style="display:flex;flex-wrap:wrap;gap:8px">' + "".join(
    f'<div style="width:110px"><div style="height:32px;border-radius:6px;border:1px solid var(--border);background:{v}"></div>'
    f'<div class="ds-src">{k}<br>{v}</div></div>' for k, v in t.items()) + "</div>", unsafe_allow_html=True)

st.subheader("kpi · ticker_strip")
for state in ds.STATES:
    st.caption(f"estado: {state}")
    if state == "normal":
        ds.kpi_row([ds.kpi("Exemplo A", "US$ 1.234,50", 0.0123, EX, "exemplo"),
                    ds.kpi("Exemplo B", "56,7", -0.021, EX[::-1], "exemplo"),
                    ds.kpi("Sem variação", "—", None, None, "indisponível: sem fonte")])
    else:
        ds.kpi_row([ds.kpi("Exemplo", "", state=state)])
    ds.ticker_strip([{"nome": "EX1", "valor": num(1234.5), "var": 0.004, "spark": EX},
                     {"nome": "EX2", "valor": num(56.7), "var": -0.012, "spark": EX[::-1]},
                     {"nome": "EX3", "valor": "—", "var": None}], state=state, source="exemplo", asof="layout")

st.subheader("asset_header")
ds.asset_header("EXEMPLO", "Empresa de exemplo", "NYSE", "Ação", 123.45, 0.0123, "US$", "layout")
ds.asset_header("EXEMPLO", "", "", "", None, None, state="empty")

st.subheader("badge (semântica fixa)")
st.markdown(" ".join(ds.badge(s) for s in tokens.BADGE_KIND), unsafe_allow_html=True)
st.markdown(" ".join(ds.origin_tag(k) for k in ds.ORIGEM), unsafe_allow_html=True)

st.subheader("data_table")
df = pd.DataFrame({"Ticker": ["EX1", "EX2", "EX3"], "Preço": [10.5, 20.25, None], "Var.": [0.012, -0.034, 0.0],
                   "Tendência": [EX, EX[::-1], EX]})
ds.data_table(df, key="demo_tbl", export_name="exemplo", source="exemplo", asof="layout", column_config={
    "Preço": st.column_config.NumberColumn(format="%.2f"),
    "Var.": st.column_config.NumberColumn(format="percent"),
    "Tendência": st.column_config.LineChartColumn()})
ds.data_table(df.iloc[0:0], key="demo_tbl_vazio")
ds.data_table(df, key="demo_tbl_err", state="error")

st.subheader("chart_container · insight_card · chips · estados")
with ds.chart_container("Gráfico de exemplo", "exemplo", "layout", legend="Linha azul = série fictícia"):
    st.line_chart(pd.DataFrame({"ex": EX}), height=140)
with ds.chart_container("Gráfico carregando", "exemplo", state="loading"):
    pass
ds.insight_card("RSI(2) = 8 · abaixo da MM200", "Setup de pullback sem tendência de fundo.",
                "Histórico do ativo com 9 operações: amostra pequena.")
ds.chips(["Classe: Ação", "RSI < 30", "Acima da MM200"])
ds.empty_state("Nenhum ativo passou nos filtros", "Relaxe algum critério.", "Ação sugerida: limpar filtros.")
ds.error_state("Falha ao consultar a fonte", "Yahoo Finance não respondeu.", "Tente novamente em instantes.")
st.markdown(ds.source_note("Yahoo Finance", "06/11/2026 18:05 BRT", "diário"), unsafe_allow_html=True)
st.caption(f"Formatação: {money(1234.5)} · {pct(0.0123)} · {num(1234567.891)} · ausente → {num(None)}")
