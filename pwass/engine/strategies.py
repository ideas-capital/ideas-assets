"""Estratégias de alocação publicadas e testadas por décadas de dados.

1. Dual Momentum / GEM — Gary Antonacci, "Dual Momentum Investing" (2014).
   Momento absoluto (ações x renda fixa curta) + relativo (EUA x resto do mundo).
2. GTAA / Ivy 5 — Mebane Faber, "A Quantitative Approach to Tactical Asset
   Allocation" (2007), um dos artigos mais baixados do SSRN.
   Cada classe só fica na carteira se estiver acima da média de 10 meses.

Ambas são revisadas 1 vez por mês, no último pregão — pouca operação, regras
fixas, nada de "achismo". Funções puras: recebem preços, devolvem pesos.
"""
from __future__ import annotations

import pandas as pd

GEM_ASSETS = {"us": "SPY", "exus": "VEU", "tbill": "BIL", "bonds": "AGG"}
GTAA_ASSETS = ["VTI", "VEU", "IEF", "VNQ", "DBC"]
GTAA_CASH = "BIL"

# Equivalentes UCITS (Irlanda, listados em Londres): mesma exposição, sem
# Estate Tax americano e com menos imposto retido em dividendos.
UCITS = {
    "SPY": "CSPX.L", "VTI": "CSPX.L", "VEU": "EXUS.L", "EFA": "EXUS.L",
    "EEM": "EIMI.L", "BIL": "IB01.L", "AGG": "AGGU.L", "IEF": "IBTM.L",
    "TLT": "IDTL.L", "VNQ": "IUSP.L", "DBC": "CMOD.L", "GLD": "IGLN.L",
    "VT": "VWRA.L",
}

NAMES = {
    "SPY": "Ações EUA (S&P 500)", "VTI": "Ações EUA (mercado total)",
    "VEU": "Ações mundo ex-EUA", "BIL": "T-Bills (caixa em dólar)",
    "AGG": "Renda fixa agregada EUA", "IEF": "Treasury 7–10 anos",
    "VNQ": "Imóveis (REITs)", "DBC": "Commodities",
    "TLT": "Treasury 20+ anos", "GLD": "Ouro",
}

# Todos os ETFs que as carteiras-modelo podem usar
MODEL_TICKERS = ("SPY", "VEU", "BIL", "AGG", "VTI", "IEF", "VNQ", "DBC", "TLT", "GLD")


def model_weights(defn: dict, m: pd.DataFrame) -> pd.DataFrame:
    """Pesos mensais de uma carteira-modelo definida em config/estrategias.yaml."""
    if defn["tipo"] == "tatica":
        return {"gem": gem_weights, "gtaa": gtaa_weights}[defn["id"]](m)
    w = pd.DataFrame({t: float(v) for t, v in defn["pesos"].items()}, index=m.index)
    return w[m[list(defn["pesos"])].notna().all(axis=1)]


def current_allocation(defn: dict, m: pd.DataFrame) -> pd.DataFrame:
    """Alocação-alvo de hoje (último mês fechado), com equivalente UCITS."""
    w = model_weights(defn, m).iloc[-1]
    w = w[w > 0].sort_values(ascending=False)
    return pd.DataFrame({"Classe": [NAMES.get(t, t) for t in w.index], "Peso": w.values,
                         "UCITS": [UCITS.get(t, "—") for t in w.index]}, index=w.index)


def monthly(close: pd.DataFrame) -> pd.DataFrame:
    """Último fechamento de cada mês."""
    return close.resample("ME").last()


def completed_months(m: pd.DataFrame, today: pd.Timestamp | None = None) -> pd.DataFrame:
    """Remove o mês corrente se ele ainda não fechou (sinal oficial = mês fechado)."""
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    if len(m) and m.index[-1] >= today:
        return m.iloc[:-1]
    return m


def gem_weights(m: pd.DataFrame, lookback: int = 12, a: dict = GEM_ASSETS) -> pd.DataFrame:
    """Pesos mensais do GEM (100% em um único ativo por mês)."""
    ret = m[[a["us"], a["exus"], a["tbill"]]].pct_change(lookback)
    w = pd.DataFrame(0.0, index=m.index, columns=[a["us"], a["exus"], a["bonds"]])
    us_beats_cash = ret[a["us"]] > ret[a["tbill"]]
    us_beats_exus = ret[a["us"]] >= ret[a["exus"]]
    w.loc[us_beats_cash & us_beats_exus, a["us"]] = 1.0
    w.loc[us_beats_cash & ~us_beats_exus, a["exus"]] = 1.0
    w.loc[~us_beats_cash, a["bonds"]] = 1.0
    return w[ret.notna().all(axis=1)]


def gtaa_weights(m: pd.DataFrame, assets=GTAA_ASSETS, cash: str = GTAA_CASH,
                 sma_months: int = 10) -> pd.DataFrame:
    """Pesos mensais do GTAA: 1/N por classe se acima da média de 10 meses, senão caixa."""
    px = m[assets]
    sma = px.rolling(sma_months).mean()
    above = px > sma
    each = 1.0 / len(assets)
    w = above.astype(float) * each
    w[cash] = (~above).sum(axis=1) * each
    return w[sma.notna().all(axis=1)]


def gem_explain(m: pd.DataFrame, lookback: int = 12, a: dict = GEM_ASSETS) -> dict:
    """Sinal do último mês disponível, com os números que o justificam."""
    ret = m[[a["us"], a["exus"], a["tbill"]]].pct_change(lookback).iloc[-1]
    w = gem_weights(m, lookback, a).iloc[-1]
    pick = w.idxmax()
    if ret[a["us"]] <= ret[a["tbill"]]:
        why = (f"Ações EUA ({ret[a['us']]:+.1%}) renderam menos que T-Bills "
               f"({ret[a['tbill']]:+.1%}) em 12 meses: momento absoluto negativo → defesa em renda fixa.")
    elif pick == a["us"]:
        why = (f"EUA ({ret[a['us']]:+.1%}) > T-Bills ({ret[a['tbill']]:+.1%}) e > ex-EUA "
               f"({ret[a['exus']]:+.1%}): momento absoluto e relativo favorecem os EUA.")
    else:
        why = (f"EUA ({ret[a['us']]:+.1%}) > T-Bills, mas ex-EUA ({ret[a['exus']]:+.1%}) foi melhor: "
               "momento relativo favorece o resto do mundo.")
    return {"date": m.index[-1], "pick": pick, "ucits": UCITS.get(pick), "returns": ret, "why": why}


def gtaa_explain(m: pd.DataFrame, assets=GTAA_ASSETS, cash: str = GTAA_CASH,
                 sma_months: int = 10) -> pd.DataFrame:
    px = m[assets].iloc[-1]
    sma = m[assets].rolling(sma_months).mean().iloc[-1]
    df = pd.DataFrame({
        "Classe": [NAMES.get(t, t) for t in assets],
        "Preço": px.values,
        "Média 10m": sma.values,
        "Distância": (px / sma - 1).values,
    }, index=assets)
    df["Sinal"] = ["Manter" if d > 0 else f"Caixa ({cash})" for d in df["Distância"]]
    df["Peso"] = 1 / len(assets)
    df["UCITS"] = [UCITS.get(t, "—") for t in assets]
    return df
