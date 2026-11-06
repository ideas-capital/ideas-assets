"""Scanner QVM: Qualidade + Valor + Momento sobre um universo global de ações."""
import io

import pandas as pd
import streamlit as st

from pwass.ai import prompts
from pwass.engine import factors, screener, swing as S
from pwass.ui import cache, components as ds, settings, theme

ds.page_header("Scanner", "Triagem por fatores com evidência acadêmica e filtros técnicos. A lista mostra onde "
               "vale gastar tempo estudando — não é lista de compras.", source="Yahoo Finance")

cfg = cache.config("universe")
groups = cfg["grupos"]
weights = cfg.get("pesos")

with st.expander("Como a nota é calculada", expanded=False):
    st.markdown(f"""
Cada ação recebe uma posição de **0 a 100** dentro do universo em três fatores:

| Fator | Peso | O que mede | Base acadêmica |
|---|---|---|---|
| **Qualidade** | {weights['quality']:.0%} | ROE, margens bruta e operacional, dívida/patrimônio | Novy-Marx (2013); Asness et al., *Quality Minus Junk* |
| **Valor** | {weights['value']:.0%} | Lucro futuro / preço (inverso do P/L) e caixa livre / valor de mercado | Fama & French (1992) |
| **Momento** | {weights['momentum']:.0%} | Retorno de 12 meses, pulando o último mês | Jegadeesh & Titman (1993) |

A coluna **Acima MM200** é o filtro de tendência de Faber: muitos investidores só compram o que está acima da média de 200 dias.
**Atenção a ADRs:** quando o balanço está em outra moeda (ex.: TSM em dólar taiwanês), o caixa livre/preço é ignorado para não distorcer.
Edite o universo e os pesos em `config/universe.yaml`.
""")

c1, c2, c3 = st.columns([2, 1, 1])
chosen = c1.multiselect("Grupos", list(groups), default=list(groups))
only_trend = c2.toggle("Só acima da MM200", value=False)
top_n = c3.number_input("Mostrar top", 5, 120, 25, step=5)
tickers = tuple(dict.fromkeys(t for g in chosen for t in groups[g]))

if st.button(f"Rodar scanner ({len(tickers)} ações)", type="primary") or "scan" in st.session_state:
    with st.status("Calculando...", expanded=False) as status:
        status.update(label="Baixando preços (1 requisição)...")
        close = cache.prices(tickers, "2y")
        status.update(label="Baixando fundamentos (pode levar ~1 min na primeira vez)...")
        fund = cache.fundamentals_many(tickers)
        res = factors.qvm(fund, close, weights)
        status.update(label=f"Pronto: {res['Nota'].notna().sum()} ações com nota", state="complete")
    st.session_state["scan"] = True

    # ---- junta o lado técnico (Yahoo, diário) e os fundamentos de tamanho
    with st.spinner("Calculando indicadores técnicos..."):
        tech = screener.technical(cache.ohlcv(tickers, "2y"))
    full = res.join(tech).join(fund["market_cap"].rename("Valor de mercado"))
    full.insert(0, "Grupo", [next((g for g in groups if t in groups[g]), "") for t in full.index])
    full["Situação"], full["Profit factor"] = None, float("nan")

    st.markdown("#### Filtros")
    sw = cache.config("swing")
    f1, f2, f3 = st.columns(3)
    flt = {"grupos": f1.multiselect("Grupo", sorted(full["Grupo"].unique())),
           "setores": f2.multiselect("Setor", sorted(full["Setor"].dropna().unique()))}
    if only_trend:
        flt["mm200"] = "acima"
    dia = f3.slider("Variação no dia (%)", -15.0, 15.0, (-15.0, 15.0), 0.5)
    flt["dia"] = None if dia == (-15.0, 15.0) else (dia[0] / 100, dia[1] / 100)
    g1, g2, g3, g4 = st.columns(4)
    vr = g1.number_input("Volume relativo mínimo (×)", 0.0, 10.0, 0.0, 0.5, help="Volume de hoje ÷ média das 20 sessões anteriores.")
    flt["vol_rel_min"] = vr or None
    rsi = g2.slider("RSI 14", 0, 100, (0, 100))
    flt["rsi"] = None if rsi == (0, 100) else rsi
    flt["mm50"] = {"Qualquer": None, "Acima": "acima", "Abaixo": "abaixo"}[g3.selectbox("Preço vs MM50", ["Qualquer", "Acima", "Abaixo"])]
    if not only_trend:
        flt["mm200"] = {"Qualquer": None, "Acima": "acima", "Abaixo": "abaixo"}[g4.selectbox("Preço vs MM200", ["Qualquer", "Acima", "Abaixo"])]
    h1, h2, h3 = st.columns(3)
    mc = h1.number_input("Valor de mercado mínimo (US$ bi)", 0.0, 5000.0, 0.0, 10.0)
    flt["mcap_min"] = mc * 1e9 if mc else None
    atr = h2.number_input("ATR máximo (% do preço)", 0.0, 30.0, 0.0, 0.5, help="Volatilidade diária típica; menor = mais calmo.")
    flt["atr_max"] = atr / 100 if atr else None
    use_sw = h3.toggle("Filtrar por sinal de estratégia (baixa 10 anos de candles; mais lento)", value=False)
    if use_sw:
        sid = st.segmented_control("Estratégia", list(sw["estrategias"]), default=sw.get("padrao"),
                                   format_func=lambda k: sw["estrategias"][k]["curto"], key="scan_sid") or sw.get("padrao")
        with st.spinner("Rodando a estratégia e o backtest em cada ação..."):
            names_ = {t: (str(full.loc[t, "Nome"]), full.loc[t, "Grupo"]) for t in full.index}
            tab_sw, _ = S.scan(cache.ohlcv(tickers, "10y"), names_, sid, sw["estrategias"][sid], sw["risco"])
        tab_sw = tab_sw.set_index("Ticker")
        full["Situação"] = tab_sw["Situação"].reindex(full.index)
        full["Profit factor"] = tab_sw["Profit factor"].reindex(full.index)
        i1, i2 = st.columns(2)
        flt["situacao"] = i1.multiselect("Situação do sinal", [S.COMPRA, S.PERTO, S.POSICAO, S.SAIR, S.AGUARDAR, S.EVITAR],
                                         default=[S.COMPRA, S.PERTO])
        pf = i2.number_input("Profit factor mínimo da regra", 0.0, 10.0, 0.0, 0.1)
        flt["pf_min"] = pf or None

    view = screener.apply_filters(full, flt).head(int(top_n))
    ds.chips(screener.chips(flt) or ["Sem filtros extras"])
    st.caption(f"{len(view)} de {len(full)} ações · filtros removem quem não tem o dado (sem dado = não passa).")

    shown = view.drop(columns=["Acima MM200"]).reset_index(names="Ticker")
    for c in ["ROE", "Margem op.", "Retorno 12-1m", "Dia", "vs MM50", "vs MM200", "ATR %"]:
        shown[c] = shown[c] * 100
    shown["Valor de mercado"] = shown["Valor de mercado"] / 1e9
    if not use_sw:
        shown = shown.drop(columns=["Situação", "Profit factor"])
    prog = lambda label: st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%.0f")  # noqa: E731
    pct1 = lambda lbl, fmt="%+.1f%%": st.column_config.NumberColumn(lbl, format=fmt)  # noqa: E731
    ds.data_table(shown, key="scan_tbl", on_select_open_asset="Ticker", height=min(38 * (len(shown) + 1), 900),
                  source="Yahoo Finance (preços e fundamentos) · notas calculadas pelo app",
                  asof=f"{tech.shape[0]} ações com dados · cache de até 12 h",
                  column_order=[c for c in ["Ticker", "Nome", "Grupo", "Setor", "Nota", "Qualidade", "Valor", "Momento", "Situação",
                                            "Profit factor", "Dia", "Vol. relativo", "RSI 14", "vs MM50", "vs MM200", "ATR %",
                                            "Valor de mercado", "P/L fwd", "ROE", "Margem op.", "Dív/PL", "Retorno 12-1m"]
                                if c in shown.columns],
                  column_config={"Nota": prog("Nota"), "Qualidade": prog("Qualidade"), "Valor": prog("Valor"),
                                 "Momento": prog("Momento"), "Dia": pct1("Dia"), "vs MM50": pct1("vs MM50"),
                                 "vs MM200": pct1("vs MM200"), "ATR %": pct1("ATR %", "%.1f%%"),
                                 "Vol. relativo": st.column_config.NumberColumn("Vol. rel.", format="%.1f×"),
                                 "RSI 14": st.column_config.NumberColumn(format="%.0f"),
                                 "Valor de mercado": st.column_config.NumberColumn("Valor de mercado (US$ bi)", format="%.0f"),
                                 "Profit factor": st.column_config.NumberColumn("PF da regra", format="%.2f"),
                                 "P/L fwd": pct1("P/L fwd", "%.1f"), "ROE": pct1("ROE", "%.0f%%"),
                                 "Margem op.": pct1("Margem op.", "%.0f%%"), "Dív/PL": pct1("Dív/PL", "%.0f"),
                                 "Retorno 12-1m": pct1("Retorno 12-1m", "%+.0f%%")})
    st.caption("Clique numa linha para abrir o ativo.")
    ex1, ex2, _ = st.columns([1, 1, 4])
    ex1.download_button("Baixar CSV", shown.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                        "scanner.csv", "text/csv")
    buf = io.BytesIO()
    shown.to_excel(buf, index=False, sheet_name="Scanner")
    ex2.download_button("Baixar Excel", buf.getvalue(), "scanner.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander("Pedir à IA uma crítica do Top 10"):
        model = settings.model_picker("scan_modelo")
        if st.button("Criticar Top 10"):
            top = res.head(10).drop(columns=["Nome"]).round(3).to_csv()
            ask = ("Abaixo está o Top 10 de um scanner Qualidade+Valor+Momento. Para cada ação, em uma linha: "
                   "o que provavelmente explica a nota alta, e um risco que o scanner não capta. "
                   "Depois aponte concentrações (setor/país/fator) e o que checar antes de estudar a fundo.\n\n" + top)
            r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                 {"role": "user", "content": ask}], model=model)
            if r:
                settings.show_result(r, "critica-top10.md")
else:
    theme.note("Clique em <b>Rodar scanner</b>. A primeira execução baixa ~100 fichas no Yahoo e leva "
               "cerca de 1 minuto; depois fica guardada por 12 horas.")
