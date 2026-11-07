"""Relatórios: PDF e Excel com resumo, regime, oportunidades, estratégias, Núcleo, riscos e fontes.

Os arquivos são gerados a partir do MESMO dicionário mostrado na tela (`engine/relatorio.montar`), então os
números coincidem. Nada é gravado no servidor: o arquivo é entregue para download.
"""
import datetime as dt

import pandas as pd
import streamlit as st

from pwass import export
from pwass.engine import lab, mercado, relatorio, strategies as ST, swing as S
from pwass.ui import cache, components as ds, theme

sw = cache.config("swing")
pcfg = cache.config("painel")
ds.page_header("Relatórios", "Gere um PDF ou Excel com o retrato de hoje: regime, oportunidades, estratégias, Núcleo e riscos.",
               source="Yahoo Finance, BCB; cálculos do app")

sid = st.session_state.get("estrategia_swing", sw.get("padrao"))
st.caption(f"Estratégia ativa no relatório: **{sw['estrategias'][sid]['nome']}** (troque no Painel). "
           "O relatório usa os mesmos dados e regras do app; o backtest é simulado e tem viés de sobrevivência.")

if st.button("Gerar relatório de hoje", type="primary", icon=":material/description:", key="rel_go"):
    names = {t: (n, g) for g, d in sw["universo"].items() for t, n in d.items()}
    with st.spinner("Calculando (candles de 10 anos, backtests e carteiras)..."):
        data = cache.ohlcv(tuple(names), "10y")
        classes = tuple(pcfg["classes_risco"])
        strip = cache.prices(classes + ("^VIX",), "2y")
        table, bts = S.scan(data, names, sid, sw["estrategias"][sid], sw["risco"])
        rg = mercado.regime(strip, classes)
        amp = mercado.amplitude(data)
        vix_s = strip["^VIX"].dropna() if "^VIX" in strip else None
        nov = mercado.novidades(data, {t: S.signals(data[t], sid, sw["estrategias"][sid]) for t in bts}, {})
        nov["cruzou_mm200_acima"] = sorted(nov["cruzou_mm200_acima"])
        opp = table[table["Situação"].isin([S.COMPRA, S.PERTO, S.POSICAO, S.SAIR])]
        comp, curvas = lab.comparar(data, sw)
        m = ST.completed_months(ST.monthly(cache.prices(ST.MODEL_TICKERS, "max")))
        gem, gtaa = ST.gem_explain(m), ST.gtaa_explain(m)
        asof = data["SPY"].index[-1] if "SPY" in data else max(d.index[-1] for d in data.values())   # referência: bolsa (cripto negocia 7 dias)
        rel = relatorio.montar(
            gerado_em=dt.datetime.now(ds.BRT).strftime("%d/%m/%Y %H:%M BRT"), data_dados=f"{asof:%d/%m/%Y}",
            estrategia=sw["estrategias"][sid]["nome"], regime=rg, amplitude=amp,
            vix=float(vix_s.iloc[-1]) if vix_s is not None else None, vix_percentil=mercado.percentil(vix_s) if vix_s is not None else None,
            oportunidades=opp, comparacao=comp, gem={"pick": gem["pick"], "ucits": gem["ucits"], "why": gem["why"]}, gtaa=gtaa,
            risco=sw["risco"], satelite=cache.config("watchlist").get("strategy", {}), novidades=nov, curvas=curvas)
        st.session_state["relatorio"] = {"dados": rel, "pdf": export.para_pdf(rel), "xlsx": export.para_excel(rel)}

rel = (st.session_state.get("relatorio") or {}).get("dados")
if not rel:
    ds.empty_state("Nenhum relatório gerado nesta sessão", "Clique em 'Gerar relatório de hoje'. Leva cerca de 1 minuto.")
    st.stop()

a = st.session_state["relatorio"]
d1, d2, _ = st.columns([1, 1, 4])
stamp = rel["meta"]["data_dados"].replace("/", "-")
d1.download_button("Baixar PDF", a["pdf"], f"relatorio-{stamp}.pdf", "application/pdf", icon=":material/picture_as_pdf:")
d2.download_button("Baixar Excel", a["xlsx"], f"relatorio-{stamp}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/table_view:")
st.markdown(ds.source_note("Calculado pelo app", f"gerado em {rel['meta']['gerado_em']} · dados de {rel['meta']['data_dados']}"), unsafe_allow_html=True)
st.markdown("#### Resumo")
for k, v in export.linhas_resumo(rel):
    st.markdown(f"- **{k}:** {v}")
st.markdown("#### Oportunidades")
ds.data_table(export.opp_tabela(rel), key="rel_opp", source="Yahoo Finance · regra ativa (simulado no histórico)",
              column_config={"Dia": st.column_config.NumberColumn(format="percent"), "Acerto": st.column_config.NumberColumn(format="percent"),
                             "Resultado médio": st.column_config.NumberColumn(format="percent"), "Último": st.column_config.NumberColumn(format="%.2f"),
                             "Profit factor": st.column_config.NumberColumn(format="%.2f")})
st.markdown("#### Estratégias do Laboratório (backtest simulado)")
ds.data_table(rel["estrategias"], key="rel_est", source="Backtest simulado no universo do Laboratório",
              column_config={c: st.column_config.NumberColumn(format="percent") for c in export.PCT_COLS if c in rel["estrategias"].columns})
st.markdown("#### Riscos e limites")
for t in rel["riscos"]:
    st.markdown(f"- {t}")
