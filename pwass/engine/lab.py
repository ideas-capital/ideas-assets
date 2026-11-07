"""Análises do Laboratório de swing sobre backtests já calculados (não altera nenhuma regra).

Todas as funções são puras: recebem os `Backtest` de `swing.py` e devolvem tabelas/séries.
"""
from __future__ import annotations

import math

import pandas as pd

from pwass.engine import swing


def retorno_por_ano(daily: pd.Series) -> pd.Series:
    """Retorno composto por ano civil de uma série de retornos diários. Ano parcial é rotulado pelo próprio ano."""
    return (1 + daily).groupby(daily.index.year).prod() - 1


def curva_media(series: dict[str, pd.Series]) -> pd.Series:
    """Curva (base 1) da média simples dos retornos diários dos ativos disponíveis em cada dia.

    Equivale a repartir o capital igualmente entre os ativos e rebalancear todo dia; serve só de régua
    para comparar estratégias/buy & hold no mesmo universo (não é uma carteira executável).
    """
    if not series:
        return pd.Series(dtype=float)
    r = pd.concat(series, axis=1).mean(axis=1)
    return (1 + r).cumprod()


def drawdown_curva(eq: pd.Series) -> pd.Series:
    return eq / eq.cummax() - 1


def comparar(data: dict[str, pd.DataFrame], sw: dict) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Roda as estratégias do config no universo. Retorna (tabela por estratégia, curvas médias).

    Tabela: operações do universo inteiro (pooled) + médias entre ativos de CAGR da regra, CAGR do
    buy & hold, tempo posicionado e pior queda. Curvas: 'Estratégia' por regra e 'Buy & hold'.
    """
    risk = sw["risco"]
    rows, curvas = [], {}
    bh_ref: dict[str, pd.Series] = {}
    for sid, p in sw["estrategias"].items():
        bts = {t: swing.backtest(df, sid, p, risk["custo_por_lado"], risk["multiplo_atr_stop"])
               for t, df in data.items() if len(df) >= 260}
        sts = {t: swing.stats(b, swing.periods_per_year(data[t].index)) for t, b in bts.items()}
        pool = swing.pooled(list(bts.values()))
        mean = lambda k: float(pd.Series([s[k] for s in sts.values()]).replace([math.inf, -math.inf], math.nan).mean())  # noqa: E731
        rows.append({"Estratégia": p["nome"], "id": sid, "Ativos": len(bts), "Operações": pool.get("Operações", 0),
                     "Taxa de acerto": pool.get("Taxa de acerto"), "Profit factor": pool.get("Profit factor"),
                     "Resultado médio": pool.get("Resultado médio"), "Ganho médio": pool.get("Ganho médio"),
                     "Perda média": pool.get("Perda média"), "Exposição média": mean("Tempo posicionado"),
                     "a.a. regra (média dos ativos)": mean("CAGR estratégia"),
                     "a.a. buy & hold (média dos ativos)": mean("CAGR buy & hold"),
                     "Pior queda (média dos ativos)": mean("Máx. queda estratégia")})
        curvas[p["nome"]] = curva_media({t: b.daily for t, b in bts.items()})
        bh_ref = {t: b.bh for t, b in bts.items()}
    if bh_ref:
        curvas["Buy & hold (mesmo universo)"] = curva_media(bh_ref)
    return pd.DataFrame(rows), curvas
