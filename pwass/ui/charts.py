"""Gráficos Plotly com o mesmo visual em todo o app."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pwass.engine import indicators
from pwass.ui import theme

COLORS = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#0EA5E9", "#64748B", "#EC4899"]


def layout() -> dict:
    """Layout Plotly que acompanha o tema claro/escuro do app."""
    t = theme.tokens()
    return dict(template="plotly_dark" if theme.mode() == "dark" else "plotly_white",
                paper_bgcolor=t["panel"], plot_bgcolor=t["panel"], font=dict(family="sans-serif", size=12, color=t["text"]),
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
                    fillcolor="rgba(37,99,235,.07)", name="Bandas de Bollinger", hoverinfo="skip", row=1, col=1)
    fig.add_scatter(x=c.index, y=c, name=name, line=dict(color=COLORS[0], width=2), row=1, col=1)
    fig.add_scatter(x=c.index, y=indicators.sma(close, 50).loc[c.index], name="MM50",
                    line=dict(color=COLORS[1], width=1.3), row=1, col=1)
    fig.add_scatter(x=c.index, y=indicators.sma(close, 200).loc[c.index], name="MM200",
                    line=dict(color=COLORS[3], width=1.3), row=1, col=1)
    if zone and all(zone):
        fig.add_hrect(y0=min(zone), y1=max(zone), fillcolor="#10B981", opacity=0.12, line_width=0,
                      annotation_text="zona-alvo", row=1, col=1)
    fig.add_scatter(x=c.index, y=rsi, name="RSI 14", line=dict(color=COLORS[4], width=1.2), row=2, col=1)
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
