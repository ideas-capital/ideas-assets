"""Dados de mercado via Yahoo Finance (biblioteca yfinance, gratuita).

Toda chamada de rede de cotações e fundamentos fica neste arquivo.
O Yahoo não é uma fonte oficial: os números são bons para triagem,
mas confira no relatório da empresa antes de decidir.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

# Nome interno -> campo do Yahoo (.info)
INFO_KEYS = {
    "name": "longName",
    "sector": "sector",
    "industry": "industry",
    "country": "country",
    "currency": "currency",
    "fin_currency": "financialCurrency",
    "quote_type": "quoteType",
    "price": "currentPrice",
    "market_cap": "marketCap",
    "fwd_pe": "forwardPE",
    "pe": "trailingPE",
    "peg": "trailingPegRatio",
    "ps": "priceToSalesTrailing12Months",
    "pb": "priceToBook",
    "ev_ebitda": "enterpriseToEbitda",
    "roe": "returnOnEquity",
    "roa": "returnOnAssets",
    "gross_margin": "grossMargins",
    "op_margin": "operatingMargins",
    "net_margin": "profitMargins",
    "debt_equity": "debtToEquity",
    "current_ratio": "currentRatio",
    "fcf": "freeCashflow",
    "shares": "sharesOutstanding",
    "rev_growth": "revenueGrowth",
    "eps_growth": "earningsGrowth",
    "div_yield": "dividendYield",
    "beta": "beta",
    "eps_ttm": "trailingEps",
    "eps_fwd": "forwardEps",
    "book_value": "bookValue",
    "target_mean": "targetMeanPrice",
    "n_analysts": "numberOfAnalystOpinions",
    "rec": "recommendationKey",
    "aum": "totalAssets",
    "expense_ratio": "netExpenseRatio",
    "summary": "longBusinessSummary",
}


def history(ticker: str, period: str = "5y") -> pd.Series:
    """Fechamentos diários ajustados por dividendos e desdobramentos."""
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if df.empty:
        raise ValueError(f"Sem dados para {ticker}")
    s = df["Close"].rename(ticker)
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s


def prices(tickers: list[str], period: str = "max") -> pd.DataFrame:
    """Fechamentos ajustados de vários tickers de uma vez (colunas = tickers)."""
    tickers = list(dict.fromkeys(tickers))  # remove duplicados mantendo a ordem
    df = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True)
    if df.empty:
        raise ValueError("Yahoo não retornou cotações")
    if isinstance(df.columns, pd.MultiIndex):
        close = df["Close"]
    else:  # versões antigas do yfinance com um único ticker
        close = df[["Close"]].rename(columns={"Close": tickers[0]})
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close.reindex(columns=[t for t in tickers if t in close.columns]).dropna(how="all")


def ohlcv(tickers: list[str], period: str = "10y") -> dict[str, pd.DataFrame]:
    """Candles diários (Open, High, Low, Close, Volume) ajustados, um DataFrame por ticker."""
    tickers = list(dict.fromkeys(tickers))
    df = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True,
                     group_by="ticker")
    if df.empty:
        raise ValueError("Yahoo não retornou cotações")
    out = {}
    for t in tickers:
        try:
            d = df[t] if isinstance(df.columns, pd.MultiIndex) else df
        except KeyError:
            continue
        d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        if len(d) < 60:
            continue
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        out[t] = d
    return out


def _info_one(ticker: str, retries: int = 3) -> dict:
    """Fundamentos de um ticker. Falha de rede vira campos vazios, nunca exceção."""
    info: dict = {}
    for attempt in range(retries):
        try:
            info = yf.Ticker(ticker).info or {}
            if info.get("quoteType"):
                break
        except Exception:  # noqa: BLE001 — o Yahoo falha de formas variadas
            pass
        time.sleep(1.5 * (attempt + 1))  # espera crescente se houver limite de requisições
    out = {k: info.get(v) for k, v in INFO_KEYS.items()}
    if out["price"] is None:
        out["price"] = info.get("regularMarketPrice")
    out["ticker"] = ticker
    return out


def fundamentals(ticker: str) -> dict:
    return _info_one(ticker)


def fundamentals_many(tickers: list[str], workers: int = 6) -> pd.DataFrame:
    """Fundamentos em paralelo (6 por vez, para não ser bloqueado pelo Yahoo)."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_info_one, tickers))
    return pd.DataFrame(rows).set_index("ticker")


def statements(ticker: str) -> dict[str, pd.DataFrame]:
    """Demonstrativos anuais (colunas = anos, mais recente primeiro)."""
    tk = yf.Ticker(ticker)
    return {"income": tk.income_stmt, "balance": tk.balance_sheet, "cashflow": tk.cashflow}


def same_currency(f: dict) -> bool:
    """ADRs costumam ter balanço em moeda local e preço em USD.

    Nesse caso, métricas que misturam preço e balanço (FCF yield, EV/EBITDA,
    DCF, número de Graham) saem distorcidas e devem ser ignoradas.
    """
    cur, fin = f.get("currency"), f.get("fin_currency")
    return bool(cur) and (fin is None or cur == fin)


def earnings_calendar(tickers: list[str]) -> pd.DataFrame:
    """Próxima data de resultados por ticker (Yahoo `calendar`). Melhor esforço: falha → linha ausente.

    Retorna colunas Ticker, Data (sem horário; o Yahoo não garante hora). Vazio se o Yahoo não responder.
    """
    rows = []
    for t in tickers:
        try:
            cal = yf.Ticker(t).calendar or {}
            ds = cal.get("Earnings Date") or []
            if ds:
                rows.append({"Ticker": t, "Data": pd.Timestamp(min(ds))})
        except Exception:  # noqa: BLE001 — Yahoo instável
            continue
    return pd.DataFrame(rows, columns=["Ticker", "Data"])


def news(ticker: str, limit: int = 10) -> list[dict]:
    """Notícias do Yahoo Finance: lista de {titulo, fonte, link, data}. Só itens com link; falha → lista vazia."""
    out = []
    try:
        for n in (yf.Ticker(ticker).news or [])[:limit * 2]:
            c = n.get("content") or n
            link = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
                    or c.get("link"))
            if not (c.get("title") and link):
                continue
            out.append({"titulo": c["title"], "fonte": (c.get("provider") or {}).get("displayName") or c.get("publisher") or "Yahoo Finance",
                        "link": link, "data": c.get("pubDate") or c.get("providerPublishTime")})
    except Exception:  # noqa: BLE001
        return []
    return out[:limit]
