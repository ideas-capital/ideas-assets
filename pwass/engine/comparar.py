"""Comparação de ativos: alinhamento de datas, base 100, volatilidade, drawdown e correlação (funções puras)."""
from __future__ import annotations

import math

import pandas as pd


def alinhar(closes: dict[str, pd.Series]) -> tuple[pd.DataFrame, dict]:
    """Junta fechamentos nas datas em que TODOS os ativos têm cotação (interseção).

    Cripto negocia 7 dias/semana e ações só em dias úteis: misturar sem alinhar distorce correlação e
    volatilidade. Retorna (DataFrame, info) com info = {'ppy': 252|365, 'descartados': {ticker: n_dias},
    'misto': bool, 'inicio', 'fim'}.
    """
    df = pd.concat({k: v.dropna() for k, v in closes.items()}, axis=1, join="inner")
    desc = {k: int(len(v.dropna()) - len(df)) for k, v in closes.items()}
    fim_semana = float((df.index.dayofweek >= 5).mean()) if len(df) else 0.0
    todos_7d = all((v.dropna().index.dayofweek >= 5).mean() > 0.2 for v in closes.values())
    return df, {"ppy": 365 if todos_7d and fim_semana > 0.2 else 252, "descartados": desc,
                "misto": any(d > 0 for d in desc.values()) and not todos_7d,
                "inicio": df.index[0] if len(df) else None, "fim": df.index[-1] if len(df) else None}


def base100(df: pd.DataFrame) -> pd.DataFrame:
    return df / df.iloc[0] * 100


def metricas(df: pd.DataFrame, ppy: int = 252) -> pd.DataFrame:
    """Uma linha por ativo: Retorno no período, Retorno a.a., Volatilidade a.a., Pior queda."""
    r = df.pct_change().dropna()
    anos = (df.index[-1] - df.index[0]).days / 365.25
    rows = {}
    for c in df.columns:
        tot = float(df[c].iloc[-1] / df[c].iloc[0] - 1)
        rows[c] = {"Retorno no período": tot,
                   "Retorno a.a.": (1 + tot) ** (1 / anos) - 1 if anos > 0 and tot > -1 else math.nan,
                   "Volatilidade a.a.": float(r[c].std() * math.sqrt(ppy)),
                   "Pior queda": float((df[c] / df[c].cummax() - 1).min())}
    return pd.DataFrame(rows).T


def correlacao(df: pd.DataFrame) -> pd.DataFrame:
    """Correlação dos retornos diários (nas datas alinhadas)."""
    return df.pct_change().dropna().corr()
