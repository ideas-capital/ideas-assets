"""Scanner QVM: Qualidade + Valor + Momento sobre um universo global de ações."""
import pandas as pd
import streamlit as st

from pwass.ai import prompts
from pwass.engine import factors
from pwass.ui import cache, settings, theme

theme.header("Scanner de ações",
             "Triagem por fatores com evidência acadêmica. A lista mostra onde vale gastar tempo "
             "estudando — não é lista de compras.")

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

    view = res.copy()
    if only_trend:
        view = view[view["Acima MM200"] == True]  # noqa: E712 — pode ter NaN
    sectors = sorted(view["Setor"].dropna().unique())
    pick_sec = st.multiselect("Filtrar setor", sectors)
    if pick_sec:
        view = view[view["Setor"].isin(pick_sec)]
    view = view.head(int(top_n))

    shown = view.copy()
    for c in ["ROE", "Margem op.", "Retorno 12-1m"]:
        shown[c] = shown[c] * 100
    prog = lambda label: st.column_config.ProgressColumn(label, min_value=0, max_value=100, format="%.0f")  # noqa: E731
    st.dataframe(shown, width="stretch", height=min(38 * (len(shown) + 1), 900), column_config={
        "Nota": prog("Nota"), "Qualidade": prog("Qualidade"), "Valor": prog("Valor"), "Momento": prog("Momento"),
        "Acima MM200": st.column_config.CheckboxColumn("Acima MM200"),
        "P/L fwd": st.column_config.NumberColumn(format="%.1f"),
        "ROE": st.column_config.NumberColumn(format="%.0f%%"),
        "Margem op.": st.column_config.NumberColumn(format="%.0f%%"),
        "Dív/PL": st.column_config.NumberColumn(format="%.0f"),
        "Retorno 12-1m": st.column_config.NumberColumn(format="%+.0f%%"),
        "Moeda balanço ≠ preço": st.column_config.CheckboxColumn("ADR moeda local"),
    })
    st.download_button("Baixar resultado (.csv)", res.to_csv().encode("utf-8"), "scanner_qvm.csv", "text/csv")

    st.markdown("#### Próximo passo")
    a, b = st.columns([2, 1])
    t = a.selectbox("Abrir no Raio-X", list(view.index))
    if b.button("Abrir Raio-X →", width="stretch"):
        st.session_state["ticker"] = t
        st.switch_page("paginas/ativo.py")

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
