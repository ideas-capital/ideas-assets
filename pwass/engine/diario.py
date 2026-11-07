"""Diário de operações reais × o que a regra mandava (funções puras).

Operação real: {"ticker", "estrategia", "entrada_data", "entrada_preco", "saida_data"?, "saida_preco"?, "motivo"}.
Não guarda saldo, quantidade em carteira nem conta: só preços e datas da operação.
`regra` = DataFrame de operações do backtest (`swing.backtest(...).trades`: Entrada, Saída, Retorno...).
"""
from __future__ import annotations

import math

import pandas as pd


def resultado(t: dict) -> float | None:
    """Retorno bruto da operação real (sem custos); None se ainda aberta."""
    if not t.get("saida_preco") or not t.get("entrada_preco"):
        return None
    return float(t["saida_preco"]) / float(t["entrada_preco"]) - 1


def par_da_regra(t: dict, regra: pd.DataFrame, tolerancia_dias: int = 5) -> dict | None:
    """Operação do backtest com entrada mais próxima da real (até `tolerancia_dias` corridos); None se não há."""
    if regra is None or regra.empty:
        return None
    e = pd.Timestamp(t["entrada_data"])
    dif = (regra["Entrada"] - e).abs()
    i = dif.idxmin()
    if dif[i] > pd.Timedelta(days=tolerancia_dias):
        return None
    r = regra.loc[i]
    return {"regra_entrada": r["Entrada"], "regra_saida": r["Saída"], "regra_retorno": float(r["Retorno"]),
            "dif_entrada_dias": int((e - r["Entrada"]).days),
            "dif_saida_dias": int((pd.Timestamp(t["saida_data"]) - r["Saída"]).days) if t.get("saida_data") else None}


def resumo(linhas: list[dict]) -> dict:
    """Resumo das operações FECHADAS. `linhas` = [{'real': float, 'par': dict|None}].
    Compara o retorno médio real com o da regra apenas nas operações pareadas."""
    fech = [x for x in linhas if x["real"] is not None]
    pareadas = [x for x in fech if x["par"]]
    nan = math.nan
    return {"operacoes": len(fech),
            "acerto_real": sum(x["real"] > 0 for x in fech) / len(fech) if fech else nan,
            "retorno_medio_real": sum(x["real"] for x in fech) / len(fech) if fech else nan,
            "seguiu_regra": len(pareadas) / len(fech) if fech else nan,
            "retorno_medio_real_pareadas": sum(x["real"] for x in pareadas) / len(pareadas) if pareadas else nan,
            "retorno_medio_regra_pareadas": sum(x["par"]["regra_retorno"] for x in pareadas) / len(pareadas) if pareadas else nan}
