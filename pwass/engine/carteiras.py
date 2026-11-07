"""Pipeline das carteiras-modelo para a página: retornos → conversão para reais → recorte de período.

Só orquestra funções já testadas de `strategies.py` e `backtest.py` (nenhuma regra nova).
"""
from __future__ import annotations

import pandas as pd

from pwass.engine import backtest, strategies as S


def retornos(models: dict[str, dict], m: pd.DataFrame) -> dict[str, pd.Series]:
    """{nome: retorno mensal em USD} de cada carteira (peso decidido no mês t só vale em t+1)."""
    return {d["nome"]: backtest.run(S.model_weights(d, m), m) for d in models.values()}


def converter_brl(results: dict[str, pd.Series], fx_m: pd.Series, cdi: pd.Series | None = None) -> dict[str, pd.Series]:
    """Converte para reais pelo dólar do mês (BRL=X, Yahoo) e, se houver, acrescenta o CDI como régua."""
    out = {k: backtest.to_brl(v, fx_m) for k, v in results.items()}
    if cdi is not None:
        out["CDI (renda fixa BR)"] = cdi
    return out


def recortar(results: dict[str, pd.Series], start: pd.Timestamp) -> tuple[dict[str, pd.Series], pd.Timestamp]:
    """Todas as séries de `start` até o fim comum (a menor data final). Retorna (séries, fim)."""
    end = min(r.index[-1] for r in results.values())
    return {k: v[(v.index >= start) & (v.index <= end)] for k, v in results.items()}, end


def inicio_comum(results: dict[str, pd.Series]) -> pd.Timestamp:
    return max(r.index[0] for r in results.values())


def formatar_metricas(met: pd.DataFrame) -> pd.DataFrame:
    """Métricas de `backtest.metrics` como texto pt-BR (percentuais, Sharpe com 2 casas, contagens inteiras)."""
    pct_rows = ["Retorno a.a. (CAGR)", "Volatilidade a.a.", "Pior queda (máx. drawdown)", "Pior ano", "Melhor ano"]
    out = met.copy().astype(object)
    for row in met.index:
        sign = "" if row == "Volatilidade a.a." else "+"
        out.loc[row] = [(f"{v * 100:{sign}.1f}%" if row in pct_rows else f"{v:.2f}" if row == "Sharpe"
                         else f"{v:.0f}").replace(".", ",") for v in met.loc[row]]
    return out
