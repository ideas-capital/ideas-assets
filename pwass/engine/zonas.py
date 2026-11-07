"""Plano de uma zona de entrada: stop por ATR, alvos em R, risco/retorno e justificativa técnica.

Usa as mesmas regras de risco do laboratório (`config/swing.yaml → risco`), sem criar regra nova:
a entrada de referência é o MEIO da zona; stop = entrada − múltiplo × ATR(14); alvos = entrada + m × R.
Cada justificativa vem com a origem do dado (observado/calculado) para a tela rotular.
"""
from __future__ import annotations

import math

import pandas as pd

from pwass.engine import indicators, swing


def plano_zona(df: pd.DataFrame, zone_min: float, zone_max: float, risk: dict, n_sr: int = 3) -> dict:
    """Plano e justificativas para comprar dentro de [zone_min, zone_max].

    Retorna: entrada, stop, alvo1, alvo2, R, atr, quantidade, valor, risco_usd, rr_resistencia (ou None),
    suportes, resistencias, status ('NA ZONA' | 'ABAIXO DA ZONA' | 'ACIMA DA ZONA'), dist_pct (% de queda
    necessária até a borda superior; 0 se já está na zona ou abaixo), e `justificativas`: lista de (texto, origem).
    """
    if zone_min > zone_max:
        zone_min, zone_max = zone_max, zone_min
    close = float(df["Close"].iloc[-1])
    entrada = (zone_min + zone_max) / 2
    a = float(swing.atr(df, 14).iloc[-1])
    R = risk["multiplo_atr_stop"] * a
    cap = risk["capital_laboratorio_usd"]
    qty = cap * risk["risco_por_operacao"] / R if R > 0 else 0.0
    qty = min(qty, cap * risk["posicao_maxima"] / entrada)
    t1, t2 = (entrada + m * R for m in risk["alvos_em_r"])
    sr = indicators.support_resistance(df)
    res_acima = [r for r in sr["resistencias"] if r > entrada]
    rr_res = (res_acima[0] - entrada) / R if res_acima and R > 0 else None
    status = "NA ZONA" if zone_min <= close <= zone_max else "ABAIXO DA ZONA" if close < zone_min else "ACIMA DA ZONA"
    dist = (1 - zone_max / close) * 100 if close > zone_max else 0.0  # % de queda necessária para tocar a zona

    just: list[tuple[str, str]] = []
    just.append((f"Preço {close:,.2f} está {status.lower()} ({zone_min:g}–{zone_max:g})"
                 + (f"; precisa cair {dist:.1f}% para tocá-la" if dist > 0 else ""), "observado"))
    sma200 = indicators.sma(df["Close"], 200).iloc[-1]
    if not math.isnan(sma200):
        just.append((f"Preço {(close / sma200 - 1) * 100:+.1f}% vs MM200 — "
                     f"{'tendência de longo prazo de alta' if close > sma200 else 'abaixo da tendência de longo prazo'}", "calculado"))
    r14 = indicators.rsi(df["Close"]).iloc[-1]
    if not math.isnan(r14):
        just.append((f"RSI 14 em {r14:.0f}" + (" (sobrevendido)" if r14 < 30 else " (sobrecomprado)" if r14 > 70 else ""), "calculado"))
    dentro = [s for s in sr["suportes"] + [x for x in sr["resistencias"]] if zone_min <= s <= zone_max]
    if dentro:
        just.append((f"A zona contém pivô(s) de preço dos últimos 12 meses ({', '.join(f'{x:.2f}' for x in dentro)}): nível já respeitado antes", "calculado"))
    else:
        just.append(("Nenhum pivô dos últimos 12 meses dentro da zona: ela não se apoia em suporte/resistência recente", "calculado"))
    just.append((f"Stop de {risk['multiplo_atr_stop']:g}×ATR = {R:,.2f} ({R / entrada * 100:.1f}% da entrada); "
                 f"tamanho pela regra de risco: {qty:,.2f} cotas", "calculado"))
    if rr_res is not None:
        just.append((f"Próxima resistência {res_acima[0]:.2f} dá R/R de {rr_res:.1f}:1 em relação ao stop", "calculado"))
    return {"entrada": entrada, "stop": entrada - R, "alvo1": t1, "alvo2": t2, "R": R, "atr": a, "quantidade": qty,
            "valor": qty * entrada, "risco_usd": qty * R, "rr_resistencia": rr_res, "suportes": sr["suportes"],
            "resistencias": sr["resistencias"], "status": status, "dist_pct": dist, "justificativas": just}
