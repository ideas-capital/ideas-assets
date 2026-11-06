"""Radar de ativos: semáforo de prudência de cripto, ações, ETFs, juros EUA e renda fixa Brasil."""
import pandas as pd
import streamlit as st

from pwass import radar
from pwass.radar import _br
from pwass.ai import prompts
from pwass.engine.health import AMARELO, AZUL, VERDE, VERMELHO
from pwass.ui import cache, charts, settings, theme
from pwass.ui.theme import card, num

theme.header("Radar de ativos",
             "Uma leitura prudente e sem emoção dos principais ativos — cripto, ações, ETFs, Treasuries, "
             "renda fixa brasileira e câmbio. Regras fixas, atualizadas a cada abertura.")

cfg = cache.config("radar")
with st.spinner("Atualizando o radar (cotações, juros EUA, Banco Central e Tesouro Direto)..."):
    df, px = radar.assets(cfg, cache.LOADERS)
    us = radar.us_rates(cache.LOADERS)
    tb = us.loc[us["Indicador"] == "T-Bill 3 meses", "Valor"]
    fx_t = next(iter(cfg.get("cambio", {})), None)
    br = radar.brazil(cache.LOADERS, fx=px[fx_t] if fx_t in px else None,
                      tbill=float(tb.iloc[0]) if len(tb) else None)

theme.signal_box(f"Painel de prudência · {px.index[-1]:%d/%m/%Y}",
                 "O que o mercado está pagando e onde está o risco",
                 "<br>".join(f"• {line}" for line in radar.summary(df, us, br)))

ROW_COLORS = {VERDE: "rgba(34,197,94,.10)", AZUL: "rgba(37,99,235,.06)",
              AMARELO: "rgba(245,158,11,.12)", VERMELHO: "rgba(239,68,68,.10)"}


def show_assets(d: pd.DataFrame, height: int | str = "auto") -> None:
    """Tabela do semáforo com cor por linha e números formatados."""
    cols = ["Ativo", "Ticker", "Leitura", "Preço", "1 mês", "12 meses", "vs MM200", "RSI",
            "Vol. 3m", "Queda do topo"] + (["P/L futuro"] if "P/L futuro" in d and d["P/L futuro"].notna().any() else []) \
        + ["Postura prudente", "Motivos"]
    view = d[cols].copy()
    for c in ["1 mês", "12 meses", "vs MM200", "Vol. 3m", "Queda do topo"]:
        view[c] = view[c] * 100
    colors = d["_cor"].map(ROW_COLORS).tolist()
    styled = view.style.apply(lambda r: [f"background-color: {colors[r.name]}"] * len(r), axis=1)
    st.dataframe(styled.format({"Preço": "{:,.2f}", "1 mês": "{:+.1f}%", "12 meses": "{:+.1f}%",
                                "vs MM200": "{:+.1f}%", "RSI": "{:.0f}", "Vol. 3m": "{:.0f}%",
                                "Queda do topo": "{:.0f}%", "P/L futuro": "{:.1f}"}, na_rep="—"),
                 width="stretch", hide_index=True, height=height)


groups = list(cfg["grupos"])
tabs = st.tabs(["Visão geral"] + groups + ["Juros EUA", "Renda fixa Brasil e câmbio", "Como ler"])

# ------------------------------------------------------------------ Visão geral
with tabs[0]:
    counts = df["_cor"].value_counts()
    st.caption(f"Todos os {len(df)} ativos, incluindo renda fixa e ouro.")
    theme.cards([
        card("🟢 Alta saudável", str(counts.get(VERDE, 0)), "tendência confirmada, sem exagero"),
        card("🔵 Correção / recuperando", str(counts.get(AZUL, 0)), "só aportes parcelados"),
        card("🟡 Esticado", str(counts.get(AMARELO, 0)), "não perseguir"),
        card("🔴 Tendência de baixa", str(counts.get(VERMELHO, 0)), "não aumentar"),
    ])
    order = {VERDE: 0, AZUL: 1, AMARELO: 2, VERMELHO: 3}
    compact = df.assign(_o=df["_cor"].map(order)).sort_values(["_o", "Grupo"]).reset_index(drop=True)
    view = compact[["Ativo", "Grupo", "Leitura", "12 meses", "vs MM200", "Postura prudente"]].copy()
    view[["12 meses", "vs MM200"]] = view[["12 meses", "vs MM200"]] * 100
    colors = compact["_cor"].map(ROW_COLORS).tolist()
    st.dataframe(view.style.apply(lambda r: [f"background-color: {colors[r.name]}"] * len(r), axis=1)
                 .format({"12 meses": "{:+.1f}%", "vs MM200": "{:+.1f}%"}, na_rep="—"),
                 width="stretch", hide_index=True, height=38 * (len(view) + 1))

# ------------------------------------------------------------------ Grupos com preço
for tab, g in zip(tabs[1:1 + len(groups)], groups):
    with tab:
        sub = df[df["Grupo"] == g].reset_index(drop=True)
        if sub.empty:
            st.info("Sem dados para este grupo agora.")
            continue
        show_assets(sub)
        names = dict(zip(sub["Ticker"], sub["Ativo"]))
        pick = st.selectbox("Gráfico", list(names), format_func=lambda t: f"{names[t]} ({t})", key=f"g_{g}")
        st.plotly_chart(charts.price_chart(px[pick].dropna(), names[pick]), width="stretch", key=f"c_{g}")
        if g == "Cripto":
            theme.note("Cripto usa limites mais largos (esticado = +50% sobre a MM200; RSI quente = 80). "
                       "<b>Múltiplo de Mayer</b> = preço ÷ MM200: abaixo de 1,0 historicamente foi acumulação; "
                       "acima de 2,4, euforia. Teto sugerido no seu plano: 5% do patrimônio.")

# ------------------------------------------------------------------ Juros EUA
with tabs[1 + len(groups)]:
    theme.note("Para quem compra título, <b>taxa alta é bom</b>: trava rendimento maior. O <b>percentil</b> diz "
               "onde o valor de hoje está na história (99 = entre os mais altos). Fonte: FRED/Federal Reserve. "
               "Os spreads de crédito no FRED só têm os últimos ~3 anos.")
    view = us.drop(columns="_cor")
    st.dataframe(view, width="stretch", hide_index=True, column_config={
        "Valor": st.column_config.NumberColumn(format="%.2f"),
        "Percentil": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        "Histórico desde": st.column_config.NumberColumn(format="%d")})
    curve = {}
    for sid, name in (("DGS3MO", "3 meses"), ("DGS2", "2 anos"), ("DGS10", "10 anos"), ("DGS30", "30 anos")):
        try:
            curve[name] = cache.fred(sid)
        except Exception:  # noqa: BLE001
            pass
    if curve:
        hist = pd.DataFrame(curve).ffill()
        st.plotly_chart(charts.lines(hist[hist.index >= "2006"], "Juros dos Treasuries (% a.a.)"), width="stretch")

# ------------------------------------------------------------------ Brasil
with tabs[2 + len(groups)]:
    ind = br.get("indicadores", {})
    theme.cards([card(k, f"{num(v, 2)}%", str(when)) for k, (v, when) in ind.items()], per_row=5)
    if "juro_real" in br:
        rr = br["juro_real"]
        txt = ("muito alto — a renda fixa pós-fixada e atrelada à inflação paga bem acima da inflação"
               if rr > 6 else "alto" if rr > 4 else "moderado" if rr > 2 else "baixo")
        theme.note(f"Juro real ex-ante de <b>{_br(rr)}%</b>: {txt}. A reserva de emergência e o caixa em reais "
                   "(Tesouro Selic / CDB com liquidez diária) rendem bem acima da inflação.")
    if "tesouro" in br:
        st.subheader(f"Tesouro Direto · taxas de {br['data_tesouro']:%d/%m/%Y}")
        td = br["tesouro"].copy()
        td["Vencimento"] = td["Vencimento"].dt.strftime("%m/%Y")
        td["Taxa"] = [f"Selic + {_br(t, 2)}%" if ti == "Tesouro Selic" else
                      f"IPCA + {_br(t, 2)}%" if "IPCA" in ti or "Renda+" in ti else f"{_br(t, 2)}% a.a."
                      for ti, t in zip(td["Titulo"], td["Taxa"])]
        st.dataframe(td[["Titulo", "Vencimento", "Taxa", "Preco"]].rename(columns={"Titulo": "Título", "Preco": "Preço (R$)"}),
                     width="stretch", hide_index=True, column_config={"Preço (R$)": st.column_config.NumberColumn(format="%.2f")})
        if "ipca_hist" in br and len(br["ipca_hist"]):
            theme.note(f"<b>IPCA+ longo</b> pagando <b>{_br(br['ipca_atual'], 2)}% acima da inflação</b>, percentil "
                       f"<b>{br['ipca_pct']:.0f}</b> desde 2010. Taxas assim foram raras e, historicamente, bons "
                       "pontos para travar — mas o preço oscila muito antes do vencimento (marcação a mercado). "
                       "Para quem leva até o vencimento, a taxa contratada é garantida.")
            st.plotly_chart(charts.lines(br["ipca_hist"].to_frame(), "Taxa real dos títulos IPCA+ longos (%)"),
                            width="stretch")
        if isinstance(br.get("implicita"), pd.DataFrame) and not br["implicita"].empty:
            st.markdown("**Inflação implícita** — o que o mercado embute ao comparar prefixado com IPCA+")
            st.dataframe(br["implicita"].style.format({"Prefixado %": "{:.2f}", "IPCA+ %": "{:.2f}",
                                                       "Inflação implícita %": "{:.2f}"}),
                         width="content", hide_index=True)
            foc = ind.get("IPCA esperado 12m (Focus)", (None,))[0]
            if foc:
                theme.note(f"Se você acredita que a inflação média ficará abaixo da implícita (o Focus espera "
                           f"{_br(foc)}% para 12 meses), o prefixado tende a render mais que o IPCA+; acima, o IPCA+ "
                           "protege melhor. Na dúvida, o IPCA+ é a escolha defensiva.")
    st.subheader("Dólar e remessas")
    d = br.get("dolar")
    if d:
        theme.cards([
            card("USD/BRL", num(d["preco"], 4), f"12 meses {d['ret_12m'] * 100:+.1f}%".replace(".", ",")),
            card("Leitura", f"{radar.EMOJI[d['cor']]} {d['status']}", d["motivos"]),
            card("Diferencial de juros", f"{num(br.get('breakeven'), 1)}% a.a.",
                 "quanto o dólar precisa subir/ano para o T-Bill empatar com o CDI (líquidos)"),
        ], per_row=3)
        theme.note("Postura prudente para remessas: <b>parcelar</b> (todo mês, valor parecido) em vez de tentar "
                   "acertar o melhor dia. O exterior entra pela diversificação e proteção cambial de longo prazo, "
                   "não para ganhar do CDI no curto prazo.")
    if br.get("erros"):
        st.caption("Algumas fontes falharam agora: " + " | ".join(br["erros"]))

# ------------------------------------------------------------------ Como ler
with tabs[3 + len(groups)]:
    st.markdown("""
| Leitura | Regra | Postura prudente |
|---|---|---|
| 🟢 **Alta saudável** | Preço acima da média de 200 dias, média subindo, retorno de 12 meses positivo, sem exagero | Manter; aportes regulares dentro dos limites |
| 🟡 **Esticado** | Muito acima da média (ações +30%, ETFs +15%, cripto +50%) ou RSI quente | Não perseguir; rebalancear se passou do limite |
| 🔵 **Recuperando** | Acima da média, mas ela ainda cai ou o retorno de 12 meses é negativo | Tendência não confirmada: aportar em parcelas |
| 🔵 **Correção** | Abaixo da média, mas ela ainda sobe | Queda dentro da alta: só aportes parcelados (DCA) |
| 🔴 **Tendência de baixa** | Abaixo da média e ela caindo | Não aumentar; esperar voltar acima da MM200 |

**Por que essas regras?** A média de 200 dias como filtro de tendência vem de Faber (2007) e de décadas de
dados: evitar ativos em tendência de baixa reduziu muito as grandes quedas, ao custo de alguns alarmes falsos.
O limite de "esticado" existe para conter o erro mais caro do investidor pessoa física: comprar depois de uma
alta forte, por medo de ficar de fora.

**O que o radar NÃO faz:** prever preço, avaliar se a empresa é boa (para isso use o Raio-X) ou dizer quanto
comprar. Limites e faixas ficam em `config/radar.yaml` e `config/watchlist.yaml`.
""")

# ------------------------------------------------------------------ IA
with st.expander("Pedir uma leitura do radar à IA"):
    model = settings.model_picker("radar_modelo")
    if st.button("Gerar leitura", type="primary"):
        table = df[["Ativo", "Leitura", "12 meses", "vs MM200", "RSI"]].round(3).to_csv(index=False)
        rates = us.drop(columns="_cor").round(2).to_csv(index=False)
        brtxt = "; ".join(f"{k}: {v:.2f}" for k, (v, _) in br.get("indicadores", {}).items())
        ask = ("Com base no radar abaixo (regras fixas de tendência e juros), escreva em até 250 palavras: "
               "1) o quadro geral em 2 frases; 2) onde está a prudência hoje para um investidor Núcleo-Satélite "
               "brasileiro (renda fixa BR, Treasuries, ações globais, cripto); 3) dois riscos a vigiar. "
               "Termine com recomendações diretas por classe (aumentar, manter, reduzir).\n\nATIVOS:\n" + table + "\nJUROS EUA:\n" + rates
               + "\nBRASIL: " + brtxt + "\nRESUMO:\n" + "\n".join(radar.summary(df, us, br)))
        r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": ask}],
                            model=model)
        if r:
            settings.show_result(r, "leitura-radar.md")
