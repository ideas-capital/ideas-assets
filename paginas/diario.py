"""Diário de operações reais: o que você fez × o que a regra mandava.

Guarda só ticker, datas, preços e motivo (sem saldo nem conta). Os números reais NÃO incluem custos,
IOF nem impostos; o backtest inclui custo de 0,10% por lado — compare ciente da diferença.
"""
import datetime as dt
import uuid

import pandas as pd
import streamlit as st

from pwass import store as _store
from pwass.engine import diario as D, swing as S
from pwass.ui import cache, components as ds, theme
from pwass.ui.theme import num, pct

sw = cache.config("swing")
risk = sw["risco"]
st_ = cache.store()
ds.page_header("Diário de operações", "Registre o que você fez de verdade e compare com o que a regra mandava.",
               source="registrado por você · regras do Laboratório (backtest simulado)")
st.markdown(f'{ds.origin_tag("real")} <span class="ds-src">operações reais, digitadas por você</span> &nbsp; {ds.origin_tag("simulado")} '
            '<span class="ds-src">o que a regra teria feito (backtest)</span>', unsafe_allow_html=True)
st.caption(f"Armazenamento: **{st_.backend}**" + (" (arquivos locais: somem se o app reiniciar na nuvem)" if st_.backend == "local" else ""))

with st.expander("Registrar operação", icon=":material/add:"):
    c1, c2 = st.columns(2)
    tk = c1.text_input("Ticker", key="dj_tk").strip().upper()
    est = c2.selectbox("Regra que você seguia (ou a mais próxima)", list(sw["estrategias"]),
                       format_func=lambda k: sw["estrategias"][k]["curto"], key="dj_est")
    d1, d2, d3, d4 = st.columns(4)
    e_data = d1.date_input("Data da entrada", value=dt.date.today(), key="dj_ed")
    e_px = d2.number_input("Preço de entrada", min_value=0.0, value=0.0, step=0.01, key="dj_ep")
    fechada = d3.checkbox("Já saí", key="dj_fechada")
    s_data = d3.date_input("Data da saída", value=dt.date.today(), key="dj_sd", disabled=not fechada)
    s_px = d4.number_input("Preço de saída", min_value=0.0, value=0.0, step=0.01, key="dj_sp", disabled=not fechada)
    motivo = st.text_area("Motivo / observações", key="dj_mot", placeholder="Ex.: RSI(2) abaixo de 10 em tendência de alta; segui a regra.")
    ok = bool(tk) and e_px > 0 and (not fechada or (s_px > 0 and s_data >= e_data))
    if st.button("Salvar operação", type="primary", disabled=not ok, key="dj_save"):
        doc = {"ticker": tk, "estrategia": est, "entrada_data": e_data.isoformat(), "entrada_preco": e_px, "motivo": motivo,
               "saida_data": s_data.isoformat() if fechada else None, "saida_preco": s_px if fechada else None}
        try:
            st_.put("diario", f"{tk}-{e_data:%Y%m%d}-{uuid.uuid4().hex[:4]}", doc)
            st.rerun()
        except _store.StoreError as e:
            st.error(str(e))

try:
    ops = sorted(st_.list("diario"), key=lambda d: d["entrada_data"], reverse=True)
except _store.StoreError as e:
    ds.error_state("Não foi possível ler o diário", str(e))
    st.stop()
if not ops:
    ds.empty_state("Nenhuma operação registrada", "Use 'Registrar operação' acima.")
    st.stop()

with st.spinner("Comparando com as regras..."):
    data = cache.ohlcv(tuple(sorted({o["ticker"] for o in ops})), "10y")
bts, linhas, rows = {}, [], []
for o in ops:
    d = data.get(o["ticker"])
    par = None
    if d is not None and len(d) >= 260:
        k = (o["ticker"], o["estrategia"])
        if k not in bts:
            bts[k] = S.backtest(d, o["estrategia"], sw["estrategias"][o["estrategia"]], risk["custo_por_lado"], risk["multiplo_atr_stop"]).trades
        par = D.par_da_regra(o, bts[k])
    real = D.resultado(o)
    linhas.append({"real": real, "par": par})
    rows.append({"Ticker": o["ticker"], "Regra": sw["estrategias"][o["estrategia"]]["curto"], "Entrada": o["entrada_data"],
                 "Preço entrada": o["entrada_preco"], "Saída": o["saida_data"] or "aberta", "Preço saída": o.get("saida_preco"),
                 "Real (bruto)": real,
                 "A regra mandava entrar?": ("sim, em " + f"{par['regra_entrada']:%d/%m/%Y}") if par else ("não encontrei sinal próximo" if d is not None else "sem dados"),
                 "Regra (backtest)": par["regra_retorno"] if par else None, "Motivo": o.get("motivo") or ""})

r = D.resumo(linhas)
ds.kpi_row([ds.kpi("Operações fechadas", str(r["operacoes"]), source="diário (real)"),
            ds.kpi("Acerto real", pct(r["acerto_real"], 0, False), source="operações fechadas, sem custos"),
            ds.kpi("Retorno médio real", pct(r["retorno_medio_real"], 2), source="bruto, sem custos/impostos"),
            ds.kpi("Seguiu a regra", pct(r["seguiu_regra"], 0, False), source="entrada a até 5 dias de um sinal do backtest"),
            ds.kpi("Real × regra (pareadas)", f"{pct(r['retorno_medio_real_pareadas'], 1)} × {pct(r['retorno_medio_regra_pareadas'], 1)}",
                   source="média das operações em que a regra também entrou; regra já com custos")])
if r["operacoes"] < 8:
    st.caption("Poucas operações fechadas: acerto e médias ainda não dizem muito.")
ds.data_table(pd.DataFrame(rows), key="dj_tbl", export_name="diario_operacoes",
              column_config={"Real (bruto)": st.column_config.NumberColumn(format="percent"),
                             "Regra (backtest)": st.column_config.NumberColumn(format="percent"),
                             "Preço entrada": st.column_config.NumberColumn(format="%.2f"),
                             "Preço saída": st.column_config.NumberColumn(format="%.2f"),
                             "Motivo": st.column_config.TextColumn(width="large")},
              source="Diário (real) + backtest das regras (simulado)")
apagar = st.selectbox("Apagar operação", [None] + [o["id"] for o in ops], format_func=lambda i: "—" if i is None else i, key="dj_del")
if apagar and st.button("Apagar", key="dj_del_ok"):
    st_.delete("diario", apagar)
    st.rerun()
