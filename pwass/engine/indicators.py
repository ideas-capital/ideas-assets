"""Indicadores técnicos puros (sem I/O) — fáceis de testar."""
from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """RSI de Wilder (média exponencial com alpha = 1/window)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    out = 100 - 100 / (1 + rs)
    return out.where(avg_loss != 0, 100.0)


def bollinger(close: pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    std = close.rolling(window, min_periods=window).std()
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


def weekly(close: pd.Series) -> pd.Series:
    """Reamostra fechamentos diários para semanais (sexta-feira)."""
    return close.resample("W-FRI").last().dropna()


def snapshot(close: pd.Series) -> dict:
    """Leitura técnica do último pregão. Requer ~1 ano de dados diários."""
    close = close.dropna()
    last = float(close.iloc[-1])
    s50, s200 = sma(close, 50).iloc[-1], sma(close, 200).iloc[-1]
    wk = weekly(close)
    bb = bollinger(close).iloc[-1]
    return {
        "price": last,
        "sma50": float(s50),
        "sma200": float(s200),
        "sma200_w": float(sma(wk, 200).iloc[-1]) if len(wk) >= 200 else float("nan"),
        "rsi14": float(rsi(close).iloc[-1]),
        "rsi14_w": float(rsi(wk).iloc[-1]) if len(wk) >= 15 else float("nan"),
        "bb_lower": float(bb["lower"]),
        "bb_upper": float(bb["upper"]),
        # Múltiplo de Mayer = preço / SMA200 diária (usado no módulo cripto)
        "mayer": last / float(s200) if pd.notna(s200) else float("nan"),
    }
