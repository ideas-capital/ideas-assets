"""Backtest mensal simples e honesto.

Regra anti-viés: o peso decidido no fim do mês t só é aplicado ao retorno do
mês t+1 (sem olhar o futuro). Preços ajustados incluem dividendos.
Não inclui custos de corretagem, spread cambial, IOF nem impostos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run(weights: pd.DataFrame, m: pd.DataFrame) -> pd.Series:
    rets = m[weights.columns].pct_change()
    w = weights.shift(1).reindex(rets.index).dropna(how="all")
    port = (w * rets.loc[w.index]).sum(axis=1, min_count=1)
    return port.dropna().rename("retorno")


def buy_hold(m: pd.DataFrame, mix: dict[str, float]) -> pd.Series:
    """Carteira fixa rebalanceada todo mês (ex.: {"SPY": .6, "AGG": .4})."""
    w = pd.DataFrame({t: [v] * len(m) for t, v in mix.items()}, index=m.index)
    return run(w, m)


def to_brl(r_usd: pd.Series, fx_monthly: pd.Series) -> pd.Series:
    """Converte retornos mensais em dólar para reais: (1 + r) × (1 + variação do dólar) − 1."""
    fx_ret = fx_monthly.pct_change().reindex(r_usd.index)
    return ((1 + r_usd) * (1 + fx_ret) - 1).dropna()


def cdi_monthly(cdi_pct_month: pd.Series) -> pd.Series:
    """Série do BCB 'CDI acumulado no mês (%)' -> retornos mensais no fim do mês."""
    s = cdi_pct_month / 100
    s.index = s.index + pd.offsets.MonthEnd(0)
    return s.rename("CDI")


def equity(r: pd.Series, start: float = 100.0) -> pd.Series:
    return start * (1 + r).cumprod()


def drawdown(r: pd.Series) -> pd.Series:
    eq = equity(r)
    return eq / eq.cummax() - 1


def metrics(r: pd.Series, rf: pd.Series | None = None) -> dict:
    r = r.dropna()
    years = len(r) / 12
    cagr = (1 + r).prod() ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std() * np.sqrt(12)
    excess = r - (rf.reindex(r.index).fillna(0) if rf is not None else 0)
    sharpe = excess.mean() / r.std() * np.sqrt(12) if r.std() > 0 else np.nan
    annual = (1 + r).groupby(r.index.year).prod() - 1
    return {
        "Retorno a.a. (CAGR)": cagr,
        "Volatilidade a.a.": vol,
        "Sharpe": sharpe,
        "Pior queda (máx. drawdown)": drawdown(r).min(),
        "Pior ano": annual.min(),
        "Melhor ano": annual.max(),
        "Meses": len(r),
    }
