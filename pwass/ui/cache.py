"""Cache das chamadas de rede. Evita bater no Yahoo/SEC a cada clique.

ttl = segundos que o dado fica guardado antes de buscar de novo.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import streamlit as st
import yaml

from pwass.ai import openrouter
from pwass.data import brasil, market, sec
from pwass.data import fred as _fred

ROOT = Path(__file__).resolve().parents[2]


@st.cache_data(ttl=60)
def config(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))


@st.cache_data(ttl=3600, show_spinner=False)
def prices(tickers: tuple[str, ...], period: str = "max") -> pd.DataFrame:
    return market.prices(list(tickers), period)


@st.cache_data(ttl=3600, show_spinner=False)
def ohlcv(tickers: tuple[str, ...], period: str = "10y") -> dict:
    return market.ohlcv(list(tickers), period)


@st.cache_data(ttl=900, show_spinner=False)
def history(ticker: str, period: str = "5y") -> pd.Series:
    return market.history(ticker, period)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fundamentals(ticker: str) -> dict:
    return market.fundamentals(ticker)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def fundamentals_many(tickers: tuple[str, ...]) -> pd.DataFrame:
    return market.fundamentals_many(list(tickers))


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def statements(ticker: str) -> dict:
    return market.statements(ticker)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def fred(sid: str) -> pd.Series:
    return _fred.series(sid)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def sgs(sid: int, start: str | None = None, last: int | None = None) -> pd.Series:
    return brasil.sgs(sid, start=start, last=last)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def focus() -> tuple[float, str]:
    return brasil.focus_ipca_12m()


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def tesouro() -> pd.DataFrame:
    return brasil.tesouro()


# Pacote de funções com cache, no formato que pwass.radar espera
LOADERS = SimpleNamespace(
    prices=lambda t, p: prices(tuple(t), p),
    fundamentals=lambda t: fundamentals_many(tuple(t)),
    fred=lambda sid: fred(sid),
    sgs=lambda sid, start=None, last=None: sgs(sid, start, last),
    focus=lambda: focus(),
    tesouro=lambda: tesouro(),
)


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def sec_ciks(user_agent: str) -> dict:
    return sec.cik_map(user_agent)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def sec_filings(ticker: str, user_agent: str) -> pd.DataFrame:
    return sec.filings(ticker, user_agent, ciks=sec_ciks(user_agent))


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def sec_text(url: str, user_agent: str) -> str:
    return sec.filing_text(url, user_agent)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def ai_models() -> list[dict]:
    try:
        return openrouter.list_models()
    except Exception:  # noqa: BLE001 — sem internet, a lista fica vazia e usamos os presets
        return []
