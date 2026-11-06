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


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD clássico (Appel): EMA(fast) − EMA(slow), linha de sinal e histograma."""
    line = close.ewm(span=fast, adjust=False, min_periods=slow).mean() - close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def pivot_points(high: float, low: float, close: float) -> dict[str, float]:
    """Pivôs clássicos a partir da máxima, mínima e fechamento do período ANTERIOR (ex.: mês passado)."""
    p = (high + low + close) / 3
    return {"S2": p - (high - low), "S1": 2 * p - high, "P": p, "R1": 2 * p - low, "R2": p + (high - low)}


def swing_pivots(df: pd.DataFrame, left: int = 5, right: int = 5) -> pd.DataFrame:
    """Topos e fundos locais (fractais): a máxima é pivô se for a maior das `left` barras antes e `right` depois.

    Atenção: o pivô só é CONFIRMADO `right` barras depois; a coluna `confirmado_em` traz essa data
    (sem ela, usar o pivô no gráfico passado seria olhar o futuro). Retorna colunas tipo ('topo'/'fundo'),
    preço, data e confirmado_em.
    """
    rows = []
    idx = df.index
    for col, tipo, fn in (("High", "topo", max), ("Low", "fundo", min)):
        s = df[col].to_numpy()
        for i in range(left, len(s) - right):
            w = s[i - left:i + right + 1]
            if s[i] == fn(w) and list(w).count(s[i]) == 1:
                rows.append({"tipo": tipo, "preco": float(s[i]), "data": idx[i], "confirmado_em": idx[i + right]})
    return pd.DataFrame(rows, columns=["tipo", "preco", "data", "confirmado_em"]).sort_values("data").reset_index(drop=True)


def support_resistance(df: pd.DataFrame, left: int = 5, right: int = 5, lookback: int = 250, n: int = 3) -> dict[str, list[float]]:
    """Suportes (fundos abaixo do preço) e resistências (topos acima) mais próximos do último fechamento,
    usando pivôs confirmados nos últimos `lookback` pregões."""
    d = df.iloc[-lookback:]
    last = float(d["Close"].iloc[-1])
    pv = swing_pivots(d, left, right)
    sup = sorted((p for p in pv.loc[pv.tipo == "fundo", "preco"] if p < last), reverse=True)[:n]
    res = sorted(p for p in pv.loc[pv.tipo == "topo", "preco"] if p > last)[:n]
    return {"suportes": sup, "resistencias": res}
