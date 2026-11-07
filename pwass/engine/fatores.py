"""Checklist de fatores a favor e contra de um sinal — regras determinísticas, sem IA.

Cada fator é (texto, lado) com lado ∈ {"favor", "contra", "neutro"} e carrega o número que o justifica.
A IA pode reescrever em linguagem natural, mas os fatores vêm deste código.
"""
from __future__ import annotations

import math

import pandas as pd

from pwass.engine import indicators, swing

Fator = tuple[str, str]


def fatores(df: pd.DataFrame, sid: str, p: dict, *, regime: str | None = None, historico: str | None = None,
            outras_estrategias: dict[str, str] | None = None) -> list[Fator]:
    """Fatores do último fechamento de `df` para a estratégia `sid`.

    `regime`: 'FAVORÁVEL' | 'MISTO' | 'DEFENSIVO' (Painel). `historico`: qualidade da regra NESTE ativo
    ('Bom'|'Regular'|'Pouco histórico'|'Fraco'). `outras_estrategias`: {nome: situação hoje}.
    """
    c = df["Close"]
    out: list[Fator] = []
    last = float(c.iloc[-1])
    s200 = indicators.sma(c, 200)
    if not math.isnan(s200.iloc[-1]):
        d = last / float(s200.iloc[-1]) - 1
        sobe = len(s200.dropna()) > 22 and s200.iloc[-1] > s200.iloc[-22]
        out.append((f"Preço {d:+.1%} vs MM200 ({'subindo' if sobe else 'caindo'})",
                    "favor" if d > 0 and sobe else "contra" if d < 0 else "neutro"))
    sig = swing.signals(df, sid, p).iloc[-1]
    if sid == "pullback":
        r2 = float(sig["rsi"])
        out.append((f"RSI({p['rsi_periodo']}) em {r2:.0f} (gatilho < {p['rsi_entrada']})",
                    "favor" if r2 < p["rsi_entrada"] else "neutro"))
    elif sid == "cruzamento":
        out.append((f"EMA{p['rapida']} {'acima' if sig['fast'] > sig['slow'] else 'abaixo'} da EMA{p['lenta']}",
                    "favor" if sig["fast"] > sig["slow"] else "contra"))
    elif sid == "rompimento":
        hh = sig["hh"]
        if not math.isnan(hh):
            out.append((f"Preço {last / hh - 1:+.1%} vs máxima de {p['canal_entrada']} dias",
                        "favor" if last > hh else "neutro"))
    if len(df) > 21:
        vr = float(df["Volume"].iloc[-1] / df["Volume"].iloc[-21:-1].mean())
        out.append((f"Volume {vr:.1f}× a média de 20 sessões", "favor" if vr >= 1.2 else "contra" if vr < 0.7 else "neutro"))
    atr_pct = float(sig["atr"] / last)
    out.append((f"ATR de {atr_pct:.1%} do preço", "contra" if atr_pct > 0.04 else "neutro"))
    r14 = float(indicators.rsi(c).iloc[-1])
    if r14 > 75:
        out.append((f"RSI(14) em {r14:.0f}: esticado", "contra"))
    if regime:
        out.append((f"Regime de mercado {regime}", {"FAVORÁVEL": "favor", "DEFENSIVO": "contra"}.get(regime, "neutro")))
    if historico:
        out.append((f"Histórico da regra neste ativo: {historico.lower()}",
                    {"Bom": "favor", "Regular": "neutro", "Fraco": "contra"}.get(historico, "neutro")))
    for nome, sit in (outras_estrategias or {}).items():
        if sit in ("COMPRA", "EM POSIÇÃO"):
            out.append((f"{nome} também em {sit}", "favor"))
        elif sit == "EVITAR":
            out.append((f"{nome}: ativo fora do filtro de tendência", "contra"))
    return [(t.replace(".", ","), l) for t, l in out]    # formato brasileiro


def resumo(fs: list[Fator]) -> tuple[int, int]:
    """(nº a favor, nº contra)."""
    return sum(l == "favor" for _, l in fs), sum(l == "contra" for _, l in fs)
