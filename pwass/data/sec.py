"""Relatórios oficiais na SEC (EDGAR), gratuitos.

A SEC exige um User-Agent com nome e e-mail de contato em cada requisição
e limita a 10 requisições por segundo. Configure o seu em Configurações.

Formulários úteis:
- 10-K / 20-F: relatório anual (empresas americanas / estrangeiras)
- 10-Q / 6-K: trimestral (americanas / estrangeiras)
- 8-K: fatos relevantes, inclusive o release de resultados
"""
from __future__ import annotations

import pandas as pd
import requests

from pwass.ai.documents import html_to_text

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
DEFAULT_FORMS = ("10-K", "10-Q", "8-K", "20-F", "6-K")


def _get(url: str, user_agent: str) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
    r.raise_for_status()
    return r


def cik_map(user_agent: str) -> dict[str, int]:
    data = _get(TICKERS_URL, user_agent).json()
    return {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}


def filings(ticker: str, user_agent: str, forms=DEFAULT_FORMS, limit: int = 20,
            ciks: dict[str, int] | None = None) -> pd.DataFrame:
    """Lista os últimos relatórios de um ticker, com link para o documento."""
    ciks = ciks or cik_map(user_agent)
    cik = ciks.get(ticker.upper().replace(".", "-"))
    if cik is None:
        raise ValueError(f"{ticker} não encontrado na SEC (só empresas listadas nos EUA/ADRs)")
    recent = _get(SUBMISSIONS_URL.format(cik=cik), user_agent).json()["filings"]["recent"]
    df = pd.DataFrame({k: recent[k] for k in ("form", "filingDate", "reportDate",
                                               "accessionNumber", "primaryDocument")})
    df = df[df["form"].isin(forms)].head(limit).copy()
    df["url"] = [ARCHIVE_URL.format(cik=cik, acc=a.replace("-", ""), doc=d)
                 for a, d in zip(df["accessionNumber"], df["primaryDocument"])]
    return df.rename(columns={"form": "Tipo", "filingDate": "Entregue em",
                              "reportDate": "Período"})[["Tipo", "Entregue em", "Período", "url"]]


def filing_text(url: str, user_agent: str) -> str:
    """Baixa o documento principal do relatório e devolve texto limpo."""
    return html_to_text(_get(url, user_agent).text)
