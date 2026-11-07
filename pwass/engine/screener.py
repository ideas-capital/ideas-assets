"""Indicadores técnicos por ativo e filtros combináveis do Scanner (funções puras, sem rede).

`technical(data)` recebe {ticker: OHLCV diário} e devolve uma linha por ticker. `apply_filters` aplica
um dicionário de critérios; critério ausente/None = não filtra. Dado ausente (NaN) NUNCA passa num filtro
que o usa — o ativo some em vez de ser tratado como "ok".
"""
from __future__ import annotations

import pandas as pd

from pwass.engine import indicators, swing


def technical(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Colunas: Dia, Vol. relativo (hoje ÷ média das 20 sessões anteriores), RSI 14, vs MM50, vs MM200, ATR %."""
    rows = []
    for t, d in data.items():
        if len(d) < 205:
            continue
        c = d["Close"]
        vol_media = d["Volume"].iloc[-21:-1].mean()
        rows.append({"Ticker": t, "Dia": float(c.iloc[-1] / c.iloc[-2] - 1),
                     "Vol. relativo": float(d["Volume"].iloc[-1] / vol_media) if vol_media else float("nan"),
                     "RSI 14": float(indicators.rsi(c).iloc[-1]),
                     "vs MM50": float(c.iloc[-1] / indicators.sma(c, 50).iloc[-1] - 1),
                     "vs MM200": float(c.iloc[-1] / indicators.sma(c, 200).iloc[-1] - 1),
                     "ATR %": float(swing.atr(d, 14).iloc[-1] / c.iloc[-1])})
    return pd.DataFrame(rows, columns=["Ticker", "Dia", "Vol. relativo", "RSI 14", "vs MM50", "vs MM200", "ATR %"]).set_index("Ticker")


def _rng(s: pd.Series, lo, hi) -> pd.Series:
    ok = pd.Series(True, index=s.index)
    if lo is not None:
        ok &= s >= lo
    if hi is not None:
        ok &= s <= hi
    return ok


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """Critérios (todos opcionais): grupos, setores, dia=(min,max), vol_rel_min, rsi=(min,max),
    mm50 ('acima'|'abaixo'), mm200 ('acima'|'abaixo'), mcap_min, situacao (lista), pf_min, atr_max.
    Variações em fração (0.02 = 2%)."""
    ok = pd.Series(True, index=df.index)
    if f.get("grupos"):
        ok &= df["Grupo"].isin(f["grupos"])
    if f.get("setores"):
        ok &= df["Setor"].isin(f["setores"])
    if f.get("dia"):
        ok &= _rng(df["Dia"], *f["dia"])
    if f.get("vol_rel_min") is not None:
        ok &= df["Vol. relativo"] >= f["vol_rel_min"]
    if f.get("rsi"):
        ok &= _rng(df["RSI 14"], *f["rsi"])
    for chave, col in (("mm50", "vs MM50"), ("mm200", "vs MM200")):
        if f.get(chave) == "acima":
            ok &= df[col] > 0
        elif f.get(chave) == "abaixo":
            ok &= df[col] < 0
    if f.get("mcap_min") is not None:
        ok &= df["Valor de mercado"] >= f["mcap_min"]
    if f.get("situacao"):
        ok &= df["Situação"].isin(f["situacao"])
    if f.get("pf_min") is not None:
        ok &= df["Profit factor"] >= f["pf_min"]
    if f.get("atr_max") is not None:
        ok &= df["ATR %"] <= f["atr_max"]
    return df[ok.fillna(False)]


def chips(f: dict) -> list[str]:
    """Descrição legível dos critérios aplicados (mostrada em chips na tela)."""
    out = []
    if f.get("grupos"):
        out.append("Grupos: " + ", ".join(f["grupos"]))
    if f.get("setores"):
        out.append("Setor: " + ", ".join(f["setores"]))
    if f.get("dia"):
        out.append(f"Variação dia {f['dia'][0] * 100:+.1f}% a {f['dia'][1] * 100:+.1f}%".replace(".", ","))
    if f.get("vol_rel_min") is not None:
        out.append(f"Volume ≥ {f['vol_rel_min']:g}× a média".replace(".", ","))
    if f.get("rsi"):
        out.append(f"RSI {f['rsi'][0]:g}–{f['rsi'][1]:g}")
    for chave, nome in (("mm50", "MM50"), ("mm200", "MM200")):
        if f.get(chave):
            out.append(f"Preço {f[chave]} da {nome}")
    if f.get("mcap_min") is not None:
        out.append(f"Valor de mercado ≥ US$ {f['mcap_min'] / 1e9:g} bi".replace(".", ","))
    if f.get("situacao"):
        out.append("Sinal: " + ", ".join(f["situacao"]))
    if f.get("pf_min") is not None:
        out.append(f"Profit factor ≥ {f['pf_min']:g}".replace(".", ","))
    if f.get("atr_max") is not None:
        out.append(f"ATR ≤ {f['atr_max'] * 100:g}% do preço".replace(".", ","))
    return out
