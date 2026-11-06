"""Radar de entrada: suas faixas-alvo x preço atual x técnica."""
import math

import pandas as pd
import streamlit as st

from pwass.engine import indicators, radar
from pwass.ui import cache, charts, theme

theme.header("Zonas de entrada",
             "Cadastre faixas de preço em config/watchlist.yaml. O radar mostra a distância até a zona "
             "e aplica o filtro anti-hype antes de qualquer veredito.")

cfg = cache.config("watchlist")
strategy = cfg.get("strategy", {})
margin = strategy.get("margin_of_safety_pct", 20)

theme.note(f"Regras do Satélite: no máximo <b>{strategy.get('satellite_max_pct')}%</b> do patrimônio, "
           f"<b>{strategy.get('single_position_max_pct')}%</b> por ativo e <b>{strategy.get('crypto_max_pct')}%</b> "
           f"em cripto. <b>Evitar</b> vence tudo: preço >40% acima da MM200, RSI ≥ 75 ou P/L futuro > 80. "
           f"<b>Forte Compra</b> só com preço justo preenchido e {margin}% de desconto.")


def build(items: list[dict], with_fund: bool) -> tuple[pd.DataFrame, dict]:
    rows, closes = [], {}
    for it in items:
        t = it["ticker"]
        try:
            close = cache.history(t)
        except Exception as e:  # noqa: BLE001
            st.warning(f"{t}: {e}")
            continue
        closes[t] = close
        tech = indicators.snapshot(close)
        fund = cache.fundamentals(t) if with_fund else {}
        row = radar.build_row(it, tech, fund.get("fwd_pe"), margin)
        has_zone = row.zone_min is not None and row.zone_max is not None
        rows.append({
            "Ativo": t, "Preço": fmt(tech["price"], "{:.2f}"),
            "Zona": f"{row.zone_min:g}–{row.zone_max:g}" if has_zone else "—",
            "Status": row.status, "Falta cair %": fmt(row.dist_pct, "{:+.1f}"),
            "vs MM200 %": fmt((tech["price"] / tech["sma200"] - 1) * 100, "{:+.1f}"),
            "RSI 14d": fmt(tech["rsi14"], "{:.0f}"), "Mayer": fmt(tech["mayer"], "{:.2f}"),
            "P/L fwd": fmt(fund.get("fwd_pe"), "{:.1f}"), "Veredito": row.verdict,
            "Motivos": "; ".join(row.reasons),
        })
    return pd.DataFrame(rows), closes


def fmt(x, pattern: str) -> str:
    """Formata número como texto; vazio vira '—' (o Streamlit mostraria 'None')."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    return pattern.format(x)


def style(df: pd.DataFrame):
    def color(row):
        if row["Status"] == "NA ZONA":
            return ["background-color: rgba(34,197,94,.16)"] * len(row)
        if str(row["Veredito"]).startswith("Evitar"):
            return ["background-color: rgba(239,68,68,.08)"] * len(row)
        return [""] * len(row)
    return df.style.apply(color, axis=1)


tab_s, tab_c = st.tabs(["Ações satélite", "Cripto (BTC/ETH)"])
with tab_s:
    items = cfg.get("satellite", [])
    df, closes = build(items, with_fund=True)
    if not df.empty:
        st.dataframe(style(df), width="stretch", hide_index=True)
        pick = st.selectbox("Gráfico", list(closes))
        it = next(i for i in items if i["ticker"] == pick)
        st.plotly_chart(charts.price_chart(closes[pick], pick, (it.get("zone_min"), it.get("zone_max"))),
                        width="stretch")
with tab_c:
    df, _ = build(cfg.get("crypto", []), with_fund=False)
    if not df.empty:
        st.dataframe(style(df[["Ativo", "Preço", "Mayer", "RSI 14d", "vs MM200 %", "Status", "Veredito"]]),
                     width="stretch", hide_index=True)
    theme.note("<b>Múltiplo de Mayer</b> = preço ÷ média de 200 dias. Historicamente no BTC: abaixo de 1,0 foi "
               "zona de acumulação; acima de 2,4, euforia. É referência de ciclo, não sinal de compra.")
