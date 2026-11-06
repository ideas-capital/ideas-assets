"""Dados macroeconômicos do FRED (Federal Reserve de St. Louis).

Usa o download público em CSV, que não exige chave de API.
"""
from __future__ import annotations

import io

import pandas as pd
import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

# Séries que o painel acompanha: id -> (nome, unidade, como ler)
SERIES = {
    "DGS10": ("Treasury 10 anos", "%", "Custo do dinheiro de longo prazo nos EUA."),
    "T10Y2Y": ("Curva 10a − 2a", "p.p.", "Negativa (invertida) costuma anteceder recessões."),
    "DFF": ("Fed Funds", "%", "Juro básico definido pelo Fed."),
    "CPIAUCSL": ("Inflação CPI (12m)", "%", "Inflação ao consumidor; meta do Fed é 2%."),
    "BAMLH0A0HYM2": ("Spread High Yield", "p.p.", "Prêmio do crédito arriscado; sobe em estresse."),
    "UNRATE": ("Desemprego EUA", "%", "Alta rápida é sinal clássico de recessão."),
}


# Juros e crédito dos EUA usados no Radar de ativos
YIELDS = {
    "DGS3MO": "T-Bill 3 meses",
    "DGS2": "Treasury 2 anos",
    "DGS10": "Treasury 10 anos",
    "DGS30": "Treasury 30 anos",
    "DFII10": "Juro real 10 anos (TIPS)",
    "BAMLC0A0CM": "Spread crédito grau de investimento",
    "BAMLH0A0HYM2": "Spread High Yield",
}


def series(sid: str, timeout: int = 30) -> pd.Series:
    r = requests.get(FRED_CSV.format(sid=sid), timeout=timeout)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), na_values=".")
    s = pd.Series(df.iloc[:, 1].values, index=pd.to_datetime(df.iloc[:, 0]), name=sid).dropna()
    if sid == "CPIAUCSL":  # índice -> variação em 12 meses
        s = (s.pct_change(12) * 100).dropna()
    return s
