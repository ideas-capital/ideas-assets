"""Scanner por fatores: Qualidade + Valor + Momento (QVM).

Base acadêmica (fatores com décadas de evidência fora da amostra):
- Valor: Fama & French (1992) — ações baratas vs. lucro tendem a superar.
- Momento: Jegadeesh & Titman (1993) — retorno de 12 meses, pulando o último.
- Qualidade/Rentabilidade: Novy-Marx (2013); Asness, Frazzini & Pedersen,
  "Quality Minus Junk" (2019) — empresas lucrativas e pouco endividadas.
- Filtro de tendência: Faber (2007) — evitar o que está abaixo da média de 200 dias.

Cada ativo recebe a posição percentual (0–100) dentro do próprio universo em
cada fator; a nota final é a média ponderada. É uma TRIAGEM, não um veredito:
o resultado é a lista de onde vale gastar tempo lendo relatórios.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {"quality": 0.4, "value": 0.3, "momentum": 0.3}


def momentum_12_1(close: pd.DataFrame) -> pd.Series:
    """Retorno de ~12 meses atrás até ~1 mês atrás (pula o último mês, que reverte)."""
    if len(close) < 253:
        return pd.Series(np.nan, index=close.columns)
    return close.iloc[-22] / close.iloc[-253] - 1


def above_sma200(close: pd.DataFrame) -> pd.Series:
    sma = close.rolling(200, min_periods=200).mean().iloc[-1]
    return close.iloc[-1] > sma


def rank(s: pd.Series, higher_is_better: bool = True) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return s.rank(pct=True, ascending=higher_is_better) * 100


def _avg(parts: list[pd.Series], min_count: int) -> pd.Series:
    df = pd.concat(parts, axis=1)
    out = df.mean(axis=1)
    return out.where(df.notna().sum(axis=1) >= min_count)


def qvm(fund: pd.DataFrame, close: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """Recebe fundamentos (index=ticker) e preços diários (colunas=ticker)."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    f = fund.copy()
    num = ["fwd_pe", "roe", "gross_margin", "op_margin", "debt_equity", "fcf", "market_cap"]
    f[num] = f[num].apply(pd.to_numeric, errors="coerce")

    # --- Qualidade: alta rentabilidade, margens e baixa alavancagem
    roe = f["roe"].clip(-1, 1)  # ROE de 300% por patrimônio quase zero distorce
    quality = _avg([rank(roe), rank(f["gross_margin"]), rank(f["op_margin"]),
                    rank(f["debt_equity"], higher_is_better=False)], min_count=2)

    # --- Valor: lucro futuro por preço (inverso do P/L) e caixa livre por preço
    earn_yield = np.where(f["fwd_pe"] > 0, 1 / f["fwd_pe"], -1.0)  # prejuízo = pior nota
    earn_yield = pd.Series(earn_yield, index=f.index).where(f["fwd_pe"].notna())
    same_ccy = (f["currency"] == f["fin_currency"]) | f["fin_currency"].isna()
    fcf_yield = (f["fcf"] / f["market_cap"]).where(same_ccy)  # ADR em moeda local: ignora
    value = _avg([rank(earn_yield), rank(fcf_yield)], min_count=1)

    # --- Momento e tendência (só preços, sempre na mesma moeda)
    mom = momentum_12_1(close).reindex(f.index)
    trend = above_sma200(close).reindex(f.index)
    momentum = rank(mom)

    # Média ponderada só dos fatores disponíveis (exige pelo menos 2 dos 3)
    parts = pd.concat([quality * w["quality"], value * w["value"], momentum * w["momentum"]], axis=1)
    total_w = (quality.notna() * w["quality"] + value.notna() * w["value"]
               + momentum.notna() * w["momentum"])
    score = parts.sum(axis=1, min_count=2) / total_w.replace(0, np.nan)

    out = pd.DataFrame({
        "Nome": f["name"], "Setor": f["sector"], "País": f["country"],
        "Nota": score, "Qualidade": quality, "Valor": value, "Momento": momentum,
        "Acima MM200": trend, "P/L fwd": f["fwd_pe"], "ROE": f["roe"],
        "Margem op.": f["op_margin"], "Dív/PL": f["debt_equity"],
        "Retorno 12-1m": mom, "Moeda balanço ≠ preço": ~same_ccy,
    })
    return out.sort_values("Nota", ascending=False)
