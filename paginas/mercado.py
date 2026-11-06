"""Mercado hoje: tendência das grandes classes de ativos + macro dos EUA."""
import pandas as pd
import streamlit as st

from pwass.ai import prompts
from pwass.data.fred import SERIES
from pwass.engine import indicators
from pwass.ui import cache, charts, settings, theme
from pwass.ui.theme import badge, card, colored_pct, num

# ticker -> nome. Só ETFs/índices globais; nada de Brasil além do câmbio.
CLASSES = {
    "SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Small caps EUA", "VEU": "Mundo ex-EUA",
    "EEM": "Emergentes", "VNQ": "Imóveis (REITs)", "DBC": "Commodities", "GLD": "Ouro",
    "TLT": "Treasury 20+ anos", "IEF": "Treasury 7–10 anos", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
}
INDICADORES = {"^VIX": "VIX (medo)", "^TNX": "Juro 10a EUA (%)", "DX-Y.NYB": "Índice do dólar",
               "BRL=X": "USD/BRL"}
RISCO = ["SPY", "QQQ", "IWM", "VEU", "EEM", "VNQ", "DBC"]

theme.header("Mercado hoje", "Tendência das grandes classes de ativos globais e o pulso da economia americana.")

with st.spinner("Atualizando cotações..."):
    px = cache.prices(tuple(CLASSES) + tuple(INDICADORES), "2y")


def stats(s: pd.Series) -> dict:
    """Retornos por data de calendário (funciona igual para ações e cripto, que negocia no fim de semana)."""
    s = s.dropna()
    last, end = s.iloc[-1], s.index[-1]

    def ret(months: int):
        past = s[s.index <= end - pd.DateOffset(months=months)]
        return last / past.iloc[-1] - 1 if len(past) else None

    prev_year = s[s.index.year < end.year]
    sma200 = indicators.sma(s, 200).iloc[-1]
    return {
        "último": last,
        "1 mês": ret(1),
        "3 meses": ret(3),
        "no ano": last / prev_year.iloc[-1] - 1 if len(prev_year) else None,
        "12 meses": ret(12),
        "acima_mm200": bool(last > sma200),
        "dist_mm200": last / sma200 - 1,
    }


rows = {t: stats(px[t]) for t in px.columns}
up = sum(rows[t]["acima_mm200"] for t in RISCO if t in rows)
vix = rows.get("^VIX", {}).get("último")

# ---------- Leitura do regime ----------
if up >= 5:
    regime, kind = "Favorável a risco", "ok"
elif up >= 3:
    regime, kind = "Misto", "warn"
else:
    regime, kind = "Defensivo", "bad"
vix_txt = "calmo" if vix and vix < 15 else "normal" if vix and vix < 25 else "estressado"
theme.signal_box(
    f"Leitura do regime · {px.index[-1]:%d/%m/%Y}",
    f"{badge(regime, kind)}  {up} de {len(RISCO)} classes de risco acima da média de 200 dias",
    f"Volatilidade (VIX {num(vix, 1)}): mercado <b>{vix_txt}</b>. "
    "A média de 200 dias (≈10 meses) é o filtro de tendência usado por Faber (2007): "
    "acima dela, a tendência de longo prazo é de alta.",
)

# ---------- Cartões ----------
destaque = ["SPY", "QQQ", "VEU", "EEM", "TLT", "GLD", "BTC-USD", "BRL=X"]
items = []
for t in destaque:
    r = rows[t]
    name = CLASSES.get(t) or INDICADORES.get(t)
    trend = badge("▲ tendência de alta", "ok") if r["acima_mm200"] else badge("▼ abaixo da MM200", "bad")
    if t == "BRL=X":
        trend = badge("dólar subindo" if r["acima_mm200"] else "dólar caindo", "info")
    items.append(card(name, num(r["último"], 2), f"1 mês {colored_pct(r['1 mês'])}", trend))
theme.cards(items, per_row=4)

# ---------- Tabela completa ----------
st.subheader("Todas as classes")
tab = pd.DataFrame(rows).T
tab.insert(0, "Ativo", [CLASSES.get(t) or INDICADORES.get(t) for t in tab.index])
tab["Tendência"] = ["▲ Alta" if v else "▼ Baixa" for v in tab["acima_mm200"]]
show = tab.drop(columns=["acima_mm200"]).rename(columns={"último": "Último", "dist_mm200": "vs MM200"})
pct_cols = ["1 mês", "3 meses", "no ano", "12 meses", "vs MM200"]
show[pct_cols] = show[pct_cols].astype(float) * 100
st.dataframe(
    show, width="stretch",
    column_config={c: st.column_config.NumberColumn(c, format="%+.1f%%") for c in pct_cols}
    | {"Último": st.column_config.NumberColumn(format="%.2f")},
)

# ---------- Desempenho comparado ----------
st.subheader("Desempenho comparado")
sel = st.multiselect("Ativos", list(CLASSES), default=["SPY", "VEU", "EEM", "TLT", "GLD"],
                     format_func=lambda t: CLASSES[t])
period = st.segmented_control("Período", ["3 meses", "6 meses", "1 ano", "2 anos"], default="1 ano")
days = {"3 meses": 64, "6 meses": 127, "1 ano": 253, "2 anos": 504}[period or "1 ano"]
if sel:
    st.plotly_chart(charts.normalized(px[sel].iloc[-days:].rename(columns=CLASSES)), width="stretch")

# ---------- Macro EUA ----------
st.subheader("Macro dos EUA (FRED)")
macro, macro_txt = {}, []
cols = st.columns(3)
for i, (sid, (name, unit, how)) in enumerate(SERIES.items()):
    try:
        s = cache.fred(sid)
    except Exception as e:  # noqa: BLE001
        cols[i % 3].warning(f"{name}: indisponível ({e})")
        continue
    macro[name] = s
    last, year_ago = s.iloc[-1], s[s.index <= s.index[-1] - pd.DateOffset(years=1)]
    delta = last - year_ago.iloc[-1] if len(year_ago) else None
    cap = f"{s.index[-1]:%m/%Y} · 12m: {num(delta, 2, '+' if delta and delta > 0 else '')} {unit}"
    cols[i % 3].markdown(card(name, f"{num(last, 2)} {unit}", cap) + f'<div class="c" style="font-size:.78rem;color:var(--muted);margin:-.3rem 0 .8rem 0">{how}</div>',
                         unsafe_allow_html=True)
    macro_txt.append(f"{name}: {last:.2f} {unit} ({s.index[-1]:%Y-%m}); variação 12m {delta}")

if macro:
    pick = st.selectbox("Ver histórico", list(macro))
    st.plotly_chart(charts.lines(macro[pick].iloc[-2600:].to_frame(pick)), width="stretch")

# ---------- Resumo por IA ----------
st.subheader("Resumo do dia com IA")
theme.note("A IA recebe a tabela acima e busca notícias recentes na web. Custo típico: menos de US$ 0,02.")
model = settings.model_picker("mercado_modelo", default_preset="noticias")
if st.button("Gerar resumo do mercado", type="primary"):
    table_txt = show[["Ativo", "Último", "1 mês", "12 meses", "Tendência"]].round(2).to_csv()
    msg = [{"role": "system", "content": prompts.SYSTEM},
           {"role": "user", "content": prompts.market_brief(table_txt, "\n".join(macro_txt))}]
    # Perplexity já busca na web sozinha; nos outros modelos ligamos o plugin de busca
    res = settings.ask_ai(msg, model=model, web=not model.startswith("perplexity/"))
    if res:
        settings.show_result(res, "resumo-mercado.md")
