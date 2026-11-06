"""Gráfico estilo TradingView com Lightweight Charts v5 (biblioteca oficial da TradingView,
licença Apache-2.0 — o logo de atribuição no canto do gráfico deve permanecer).

Painéis: preço (candles + MM20/50/200 + Bollinger + níveis), volume e RSI.
Ferramentas de desenho são feitas por código: Fibonacci do último swing,
máxima/mínima de 20 dias e o plano da operação (entrada, stop, alvos).
"""
from __future__ import annotations

import math

import pandas as pd

from pwass.engine import indicators
from pwass.ui import theme, tokens

try:
    from lightweight_charts_v5 import lightweight_charts_v5_component as _lwc
except Exception:  # noqa: BLE001 — sem o componente, a página cai no gráfico Plotly
    _lwc = None

AVAILABLE = _lwc is not None
FIB = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf == "1S":
        return df.resample("W-FRI").agg({"Open": "first", "High": "max", "Low": "min",
                                         "Close": "last", "Volume": "sum"}).dropna(subset=["Close"])
    return df


def _t(d) -> str:
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def _line(s: pd.Series) -> list[dict]:
    return [{"time": _t(i), "value": float(v)} for i, v in s.items() if v is not None and not math.isnan(v)]


def _hline(idx: pd.DatetimeIndex, value: float, bars: int = 60) -> list[dict]:
    return [{"time": _t(i), "value": float(value)} for i in idx[-bars:]]


def _lineseries(data, color, width=1, style=0, title="", last=False):
    return {"type": "Line", "data": data,
            "options": {"color": color, "lineWidth": width, "lineStyle": style, "title": title,
                        "priceLineVisible": False, "lastValueVisible": last, "crosshairMarkerVisible": False}}


def fib_levels(df: pd.DataFrame, lookback: int = 120) -> dict[float, float]:
    """Retração de Fibonacci entre o fundo e o topo dos últimos `lookback` candles."""
    w = df.iloc[-lookback:]
    hi, lo = float(w["High"].max()), float(w["Low"].min())
    up = w["High"].idxmax() > w["Low"].idxmin()  # topo depois do fundo = swing de alta
    return {f: (hi - (hi - lo) * f) if up else (lo + (hi - lo) * f) for f in FIB}


def render(df: pd.DataFrame, name: str, *, tf: str = "1D", show: dict | None = None,
           plan: dict | None = None, trades: pd.DataFrame | None = None, levels: dict | None = None, bars: int = 180,
           height: int = 560, key: str = "tv") -> None:
    show = {"mm": True, "bb": True, "vol": True, "rsi": True, "fib": False, "hl20": False, "plan": True, "macd": False, "sr": False,
            **(show or {})}
    t = theme.tokens()
    d = resample(df, tf)
    c = d["Close"]
    view = d.iloc[-max(bars, 260):]  # médias precisam de histórico; o zoom mostra `bars`
    idx = view.index

    candles = [{"time": _t(i), "open": float(r.Open), "high": float(r.High), "low": float(r.Low),
                "close": float(r.Close)} for i, r in view.iterrows()]
    price_series = [{"type": "Candlestick", "data": candles,
                     "options": {"upColor": tokens.SERIES["candle_up"], "downColor": tokens.SERIES["candle_down"], "borderVisible": False,
                                 "wickUpColor": tokens.SERIES["candle_up"], "wickDownColor": tokens.SERIES["candle_down"]}}]
    if trades is not None and not trades.empty and tf == "1D":
        mk = []
        start = idx[0]
        for _, r in trades[trades["Entrada"] >= start].iterrows():
            mk.append({"time": _t(r["Entrada"]), "position": "belowBar", "color": t["up"], "shape": "arrowUp", "text": "C"})
            mk.append({"time": _t(r["Saída"]), "position": "aboveBar", "color": t["down"], "shape": "arrowDown",
                       "text": f"{r['Retorno'] * 100:+.1f}%"})
        price_series[0]["markers"] = sorted(mk, key=lambda m: m["time"])
    if show["mm"]:
        for n, col in ((20, tokens.SERIES["mm20"]), (50, tokens.SERIES["mm50"]), (200, tokens.SERIES["mm200"])):
            price_series.append(_lineseries(_line(indicators.sma(c, n).loc[idx]), col, 1, 0, f"MM{n}"))
    if show["bb"]:
        bb = indicators.bollinger(c).loc[idx]
        for col in ("upper", "lower"):
            price_series.append(_lineseries(_line(bb[col]), tokens.SERIES["bollinger"], 1, 2))
    if show["hl20"]:
        hh = d["High"].rolling(20).max().iloc[-1]
        ll = d["Low"].rolling(20).min().iloc[-1]
        price_series.append(_lineseries(_hline(idx, hh, 40), t["muted"], 1, 1, "Máx 20", True))
        price_series.append(_lineseries(_hline(idx, ll, 40), t["muted"], 1, 1, "Mín 20", True))
    if show["fib"]:
        for f, v in fib_levels(d).items():
            price_series.append(_lineseries(_hline(idx, v, 120), "rgba(240,185,11,.75)", 1, 2, f"Fib {f:.3f}".rstrip("0").rstrip("."), True))
    if show["sr"] and levels:  # suportes/resistências por pivôs confirmados (engine.indicators.support_resistance)
        for i, v in enumerate(levels.get("suportes", [])):
            price_series.append(_lineseries(_hline(idx, v, len(idx)), t["up"], 1, 2, f"Suporte {i + 1}", True))
        for i, v in enumerate(levels.get("resistencias", [])):
            price_series.append(_lineseries(_hline(idx, v, len(idx)), t["down"], 1, 2, f"Resist. {i + 1}", True))
    if show["plan"] and plan:
        for lbl, key_, col, sty in (("Entrada", "entrada", t["accent"], 0), ("Stop", "stop", t["down"], 2),
                                    ("Alvo 1", "alvo1", t["up"], 2), ("Alvo 2", "alvo2", t["up"], 2)):
            price_series.append(_lineseries(_hline(idx, plan[key_], 30), col, 2 if lbl == "Entrada" else 1, sty, lbl, True))

    chart_opts = {
        "layout": {"background": {"type": "solid", "color": t["panel"]}, "textColor": t["muted"], "fontSize": 11},
        "grid": {"vertLines": {"color": t["grid"]}, "horzLines": {"color": t["grid"]}},
        "rightPriceScale": {"borderColor": t["border"]}, "timeScale": {"borderColor": t["border"]},
        "priceScaleBorderColor": t["border"], "timeScaleBorderColor": t["border"], "priceScaleTextColor": t["muted"],
        "crosshair": {"mode": 0},
        "titleOptions": {"fontSize": 12, "fontFamily": "sans-serif", "fontStyle": "bold"},
    }
    panes = [{"chart": chart_opts, "series": price_series, "height": 360,
              "title": f"{name} · {'Diário' if tf == '1D' else 'Semanal'}"}]
    if show["vol"]:
        vol = [{"time": _t(i), "value": float(r.Volume),
                "color": (t["up"] if r.Close >= r.Open else t["down"]) + "88"} for i, r in view.iterrows()]
        panes.append({"chart": chart_opts, "height": 80, "title": "Volume",
                      "series": [{"type": "Histogram", "data": vol,
                                  "options": {"priceFormat": {"type": "volume"}, "priceLineVisible": False}}]})
    if show["rsi"]:
        r = indicators.rsi(c).loc[idx]
        panes.append({"chart": chart_opts, "height": 110, "title": "RSI 14",
                      "series": [_lineseries(_line(r), tokens.SERIES["rsi"], 1, 0, "RSI", True),
                                 _lineseries(_hline(idx, 70, len(idx)), t["muted"], 1, 2),
                                 _lineseries(_hline(idx, 30, len(idx)), t["muted"], 1, 2)]})
    if show["macd"]:
        mc = indicators.macd(c).loc[idx]
        hist = [{"time": _t(i), "value": float(v), "color": (tokens.SERIES["candle_up"] if v >= 0 else tokens.SERIES["candle_down"]) + "88"}
                for i, v in mc["hist"].dropna().items()]
        panes.append({"chart": chart_opts, "height": 110, "title": "MACD 12·26·9",
                      "series": [{"type": "Histogram", "data": hist, "options": {"priceLineVisible": False}},
                                 _lineseries(_line(mc["macd"]), tokens.SERIES["macd"], 1, 0, "MACD", True),
                                 _lineseries(_line(mc["signal"]), tokens.SERIES["macd_signal"], 1, 0, "Sinal", True)]})
    total = sum(p["height"] for p in panes)
    _lwc(name=f"{name}-{tf}", charts=panes, height=total, zoom_level=bars,
         key=f"{key}-{theme.mode()}-{tf}-{hash(frozenset(show.items()))}")
