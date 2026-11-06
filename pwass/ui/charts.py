"""Gráficos Plotly com o mesmo visual em todo o app."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pwass.engine import indicators
from pwass.ui import theme, tokens

S = tokens.SERIES
COLORS = [S["mm20"], S["mm50"], S["candle_up"], S["candle_down"], S["mm200"], "#0EA5E9", "#64748B", "#EC4899"]


def layout() -> dict:
    """Layout Plotly que acompanha o tema claro/escuro do app."""
    t = theme.tokens()
    return dict(template="plotly_dark" if theme.mode() == "dark" else "plotly_white",
                paper_bgcolor=t["surface"], plot_bgcolor=t["surface"], font=dict(family=tokens.FONT_FAMILY, size=12, color=t["text"]),
                margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.08, x=0), hovermode="x unified",
                xaxis=dict(gridcolor=t["grid"]), yaxis=dict(gridcolor=t["grid"]))


def price_chart(close: pd.Series, name: str, zone: tuple | None = None, days: int = 400) -> go.Figure:
    """Preço + médias + Bollinger em cima; RSI embaixo."""
    c = close.iloc[-days:]
    bb = indicators.bollinger(close).loc[c.index]
    rsi = indicators.rsi(close).loc[c.index]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.04)
    fig.add_scatter(x=c.index, y=bb["upper"], line=dict(width=0), showlegend=False, hoverinfo="skip", row=1, col=1)
    fig.add_scatter(x=c.index, y=bb["lower"], line=dict(width=0), fill="tonexty",
                    fillcolor="rgba(148,163,184,.12)", name="Bandas de Bollinger", hoverinfo="skip", row=1, col=1)
    fig.add_scatter(x=c.index, y=c, name=name, line=dict(color=COLORS[0], width=2), row=1, col=1)
    fig.add_scatter(x=c.index, y=indicators.sma(close, 50).loc[c.index], name="MM50",
                    line=dict(color=S["mm50"], width=1.3), row=1, col=1)
    fig.add_scatter(x=c.index, y=indicators.sma(close, 200).loc[c.index], name="MM200",
                    line=dict(color=S["mm200"], width=1.3), row=1, col=1)
    if zone and all(zone):
        fig.add_hrect(y0=min(zone), y1=max(zone), fillcolor="#10B981", opacity=0.12, line_width=0,
                      annotation_text="zona-alvo", row=1, col=1)
    fig.add_scatter(x=c.index, y=rsi, name="RSI 14", line=dict(color=S["rsi"], width=1.2), row=2, col=1)
    for lvl in (30, 70):
        fig.add_hline(y=lvl, line=dict(color="#94A3B8", dash="dot", width=1), row=2, col=1)
    fig.update_layout(height=520, **layout())
    fig.update_yaxes(range=[0, 100], row=2, col=1)
    return fig


def lines(df: pd.DataFrame, title: str = "", log: bool = False, pct_axis: bool = False,
          height: int = 380) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        fig.add_scatter(x=df.index, y=df[col], name=str(col), line=dict(color=COLORS[i % len(COLORS)], width=1.8))
    fig.update_layout(title=title, height=height, **layout())
    if log:
        fig.update_yaxes(type="log")
    if pct_axis:
        fig.update_yaxes(tickformat=".0%")
    return fig


def normalized(df: pd.DataFrame, title: str = "") -> go.Figure:
    base = df.apply(lambda s: s / s.dropna().iloc[0] - 1)
    return lines(base, title, pct_axis=True)


# ------------------------------------------------------------------ gráficos do Laboratório / carteiras
def _fig(height: int, title: str = "", **kw) -> go.Figure:
    fig = go.Figure()
    lay = layout()
    lay["legend"] = dict(orientation="h", y=-0.2, x=0, font=dict(size=11))
    lay["margin"] = dict(l=8, r=8, t=34 if title else 10, b=8)
    fig.update_layout(height=height, title=dict(text=title, font=dict(size=13)) if title else None, **lay, **kw)
    return fig


def _serie_cor(i: int, n: int, t: dict) -> str:
    """1ª série (a estratégia) = 'up'; com 2 séries, a 2ª (buy & hold) = cinza; com mais, paleta."""
    return t["up"] if i == 0 else t["muted"] if (i == 1 and n == 2) else COLORS[(i + 1) % len(COLORS)]


def equity_vs(curves: dict[str, pd.Series], title: str, height: int = 300, log: bool = True) -> go.Figure:
    """Curvas de capital (base 1). A primeira usa a cor 'up'; as demais, a paleta de séries."""
    t = theme.tokens()
    fig = _fig(height, title)
    for i, (name, s) in enumerate(curves.items()):
        fig.add_scatter(x=s.index, y=s.values, name=name, line=dict(color=_serie_cor(i, len(curves), t), width=1.8 if i == 0 else 1.3))
    if log:
        fig.update_yaxes(type="log", tickformat=".1f")
    return fig


def drawdown_fig(curves: dict[str, pd.Series], title: str = "Queda a partir do topo", height: int = 200) -> go.Figure:
    t = theme.tokens()
    fig = _fig(height, title)
    for i, (name, s) in enumerate(curves.items()):
        dd = s / s.cummax() - 1
        fig.add_scatter(x=dd.index, y=dd.values, name=name, line=dict(color=_serie_cor(i, len(curves), t), width=1.2),
                        fill="tozeroy" if i == 0 else None, fillcolor="rgba(148,163,184,.14)")
    fig.update_yaxes(tickformat=".0%")
    return fig


def histogram(returns: pd.Series, title: str = "Resultado por operação", height: int = 220) -> go.Figure:
    t = theme.tokens()
    fig = _fig(height, title)
    r = returns.dropna()
    fig.add_histogram(x=r[r > 0], name="Ganhos", marker_color=t["up"], xbins=dict(size=0.02))
    fig.add_histogram(x=r[r <= 0], name="Perdas", marker_color=t["down"], xbins=dict(size=0.02))
    fig.update_layout(barmode="overlay", bargap=0.05)
    fig.update_xaxes(tickformat=".0%")
    return fig


def bars_by_year(series: dict[str, pd.Series], title: str = "Retorno por ano", height: int = 240) -> go.Figure:
    fig = _fig(height, title)
    for i, (name, s) in enumerate(series.items()):
        fig.add_bar(x=s.index.astype(str), y=s.values, name=name, marker_color=COLORS[i % len(COLORS)] if i else theme.tokens()["up"])
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickformat=".0%")
    return fig
