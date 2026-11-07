"""Helpers puros da página Ativo: classe do ativo e performance por janelas de calendário."""
from __future__ import annotations

import pandas as pd

JANELAS = {"1M": {"months": 1}, "3M": {"months": 3}, "6M": {"months": 6}, "1A": {"years": 1}, "5A": {"years": 5}}


def classe(quote_type: str | None, ticker: str) -> str:
    """'Ação', 'ETF', 'Cripto', 'Índice', 'Câmbio', 'Futuro' ou 'Desconhecida'.

    Usa o `quoteType` do Yahoo; se faltar (Yahoo instável), cai em pistas pelo ticker.
    Nunca assume 'Ação' sem evidência — fundamentos de empresa só aparecem para 'Ação'.
    """
    q = (quote_type or "").upper()
    m = {"EQUITY": "Ação", "ETF": "ETF", "MUTUALFUND": "ETF", "CRYPTOCURRENCY": "Cripto", "INDEX": "Índice",
         "CURRENCY": "Câmbio", "FUTURE": "Futuro"}
    if q in m:
        return m[q]
    t = ticker.upper()
    if t.endswith("-USD"):
        return "Cripto"
    if t.startswith("^"):
        return "Índice"
    if t.endswith("=X"):
        return "Câmbio"
    if t.endswith("=F"):
        return "Futuro"
    return "Desconhecida"


def performance(close: pd.Series) -> dict[str, float | None]:
    """Retorno por janela de CALENDÁRIO (1M, 3M, 6M, 1A, 5A) — igual para ações e cripto (7 dias/semana).

    Sem histórico suficiente para a janela → None (a tela mostra '—').
    """
    s = close.dropna()
    end, last = s.index[-1], float(s.iloc[-1])
    out: dict[str, float | None] = {}
    for nome, off in JANELAS.items():
        ini = end - pd.DateOffset(**off)
        past = s[s.index <= ini]
        out[nome] = last / float(past.iloc[-1]) - 1 if len(past) else None
    return out
