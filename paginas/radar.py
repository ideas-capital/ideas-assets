"""Radar de entrada: suas faixas-alvo x preço atual x técnica."""
import math

import pandas as pd
import streamlit as st

from pwass.engine import indicators, radar, zonas
from pwass.ui import cache, charts, components as ds, theme, tvchart

ds.page_header("Zonas de entrada",
               "Cadastre faixas de preço em config/watchlist.yaml. O radar mostra a distância até a zona, o plano de risco "
               "e aplica o filtro anti-hype antes de qualquer veredito.", source="Yahoo Finance", asof="diário")
sw_risk = cache.config("swing")["risco"]

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
    return pattern.format(x).replace(".", ",")


def zone_detail(items: list[dict], closes: dict) -> None:
    """Gráfico com a zona, plano de risco e justificativa técnica do ativo escolhido."""
    pick = st.selectbox("Ver zona no gráfico", list(closes), key=f"zona_{items[0]['ticker']}")
    it = next(i for i in items if i["ticker"] == pick)
    zmin, zmax = it.get("zone_min"), it.get("zone_max")
    try:
        ohl = cache.ohlcv((pick,), "10y").get(pick)
    except Exception:  # noqa: BLE001
        ohl = None
    if zmin is None or zmax is None:
        ds.empty_state(f"{pick} sem zona cadastrada", "Preencha zone_min e zone_max em config/watchlist.yaml.")
        st.plotly_chart(charts.price_chart(closes[pick], pick), width="stretch")
        return
    if ohl is None or len(ohl) < 260:
        ds.empty_state("Candles indisponíveis", "O Yahoo não retornou OHLC; mostrando o gráfico de linha.")
        st.plotly_chart(charts.price_chart(closes[pick], pick, (zmin, zmax)), width="stretch")
        return
    pl = zonas.plano_zona(ohl, zmin, zmax, sw_risk)
    sr = indicators.support_resistance(ohl, n=2)
    with ds.chart_container(f"{pick} · zona {zmin:g}–{zmax:g}", "Yahoo Finance (preços ajustados)", f"{ohl.index[-1]:%d/%m/%Y}",
                            legend="Azul = zona de compra · vermelho tracejado = stop · verde tracejado = alvos 1 e 2 · "
                                   "suportes/resistências por pivôs"):
        tvchart.render(ohl, pick, tf="1D", show={"mm": True, "bb": False, "vol": False, "rsi": False, "plan": True, "sr": True},
                       plan=pl, levels=sr, zone=(zmin, zmax), bars=252, key=f"zona_chart_{pick}")
    ds.kpi_row([ds.kpi("Entrada (meio da zona)", theme.num(pl["entrada"]), source="calculado: média de zone_min e zone_max"),
                ds.kpi("Stop", theme.num(pl["stop"]), source=f"calculado: entrada − {sw_risk['multiplo_atr_stop']:g}×ATR(14)"),
                ds.kpi("Alvo 1 / Alvo 2", f"{theme.num(pl['alvo1'])} / {theme.num(pl['alvo2'])}",
                       source=f"calculado: {sw_risk['alvos_em_r'][0]:g}R e {sw_risk['alvos_em_r'][1]:g}R"),
                ds.kpi("R/R até a resistência", f"{pl['rr_resistencia']:.1f}:1".replace(".", ",") if pl["rr_resistencia"] else "—",
                       source="calculado; — se não há resistência acima da entrada nos últimos 12 meses"),
                ds.kpi("Tamanho (pela regra de risco)", f"US$ {theme.num(pl['valor'], 0)}",
                       source=f"{sw_risk['risco_por_operacao'] * 100:g}% do laboratório de US$ {theme.num(sw_risk['capital_laboratorio_usd'], 0)}")])
    ds.insight_card("<br>".join(f"{ds.origin_tag(o)} {esc_(t)}" for t, o in pl["justificativas"]),
                    "Regras determinísticas; a IA não participa desta leitura.",
                    "A zona é uma hipótese sua (config), não uma previsão. O stop por ATR pode ser maior que o suporte mais próximo.",
                    origin="calculado")


esc_ = theme.esc


tab_s, tab_c = st.tabs(["Ações satélite", "Cripto (BTC/ETH)"])
with tab_s:
    items = cfg.get("satellite", [])
    df, closes = build(items, with_fund=True)
    if not df.empty:
        ds.data_table(df, key="zonas_sat", on_select_open_asset="Ativo", export_name="zonas_satelite",
                      column_config={"Motivos": st.column_config.TextColumn(width="large")},
                      source="Yahoo Finance · zonas definidas por você em config/watchlist.yaml")
        zone_detail(items, closes)
with tab_c:
    df, _ = build(cfg.get("crypto", []), with_fund=False)
    if not df.empty:
        ds.data_table(df[["Ativo", "Preço", "Mayer", "RSI 14d", "vs MM200 %", "Status", "Veredito"]], key="zonas_cripto",
                      on_select_open_asset="Ativo", source="Yahoo Finance")
    theme.note("<b>Múltiplo de Mayer</b> = preço ÷ média de 200 dias. Historicamente no BTC: abaixo de 1,0 foi "
               "zona de acumulação; acima de 2,4, euforia. É referência de ciclo, não sinal de compra.")
