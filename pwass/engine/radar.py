"""Radar de zona de compra + veredito do Audit Mode (versão Fase 1).

Fase 1 usa zona-alvo + técnica. Fase 2 adiciona fair_value calculado
(Graham, DCF simplificado, múltiplos vs. média de 5 anos). Até lá,
"Forte Compra" só sai quando você preencher fair_value manualmente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

FORTE_COMPRA = "Forte Compra (Abaixo da Margem de Segurança)"
AGUARDAR = "Aguardar Zona de Entrada"
NEUTRO = "Neutro/Caro"
EVITAR = "Evitar (Risco Fundamentalista/Esticado)"

# Limiares de "esticado". Ajuste aqui, não espalhe números pelo código.
STRETCH_SMA200 = 1.40   # preço 40% acima da SMA200 diária
RSI_OVERBOUGHT = 75
FWD_PE_CEILING = 80     # acima disso o preço depende de anos de execução perfeita


@dataclass
class RadarRow:
    ticker: str
    price: float
    zone_min: float | None
    zone_max: float | None
    status: str           # NA ZONA / ACIMA / ABAIXO / SEM ZONA
    dist_pct: float       # % que o preço precisa cair (+) ou subir (-) até a zona
    verdict: str
    reasons: list[str]


def zone_status(price: float, zmin: float | None, zmax: float | None) -> tuple[str, float]:
    if zmin is None or zmax is None:
        return "SEM ZONA", math.nan
    lo, hi = sorted((zmin, zmax))
    if lo <= price <= hi:
        return "NA ZONA", 0.0
    if price > hi:
        return "ACIMA", (price - hi) / price * 100      # queda necessária
    return "ABAIXO", (price - lo) / price * 100          # negativo: abaixo da faixa


def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def verdict(tech: dict, status: str, fair_value: float | None = None,
            fwd_pe: float | None = None, margin_pct: float = 20) -> tuple[str, list[str]]:
    price = tech["price"]
    reasons: list[str] = []

    stretched = False
    if _ok(tech.get("sma200")) and price > tech["sma200"] * STRETCH_SMA200:
        stretched = True
        reasons.append(f"{price / tech['sma200'] - 1:+.0%} vs SMA200")
    if _ok(tech.get("rsi14")) and tech["rsi14"] >= RSI_OVERBOUGHT:
        stretched = True
        reasons.append(f"RSI {tech['rsi14']:.0f} (sobrecompra)")
    if _ok(fwd_pe) and fwd_pe > FWD_PE_CEILING:
        stretched = True
        reasons.append(f"P/L fwd {fwd_pe:.0f}x")
    if stretched:
        return EVITAR, reasons

    if _ok(fair_value):
        ceiling = fair_value * (1 - margin_pct / 100)
        if price <= ceiling:
            reasons.append(f"preço ≤ {ceiling:.2f} (justo {fair_value:.2f} − {margin_pct}%)")
            return FORTE_COMPRA, reasons
        if price > fair_value:
            reasons.append(f"acima do preço justo {fair_value:.2f}")
            return NEUTRO, reasons

    if status == "NA ZONA":
        reasons.append("na faixa-alvo; sem preço justo, não confirma margem")
        return AGUARDAR, reasons
    if status == "ACIMA":
        reasons.append("acima da faixa-alvo")
        return AGUARDAR, reasons
    reasons.append("sem zona/preço justo definidos" if status == "SEM ZONA" else "abaixo da faixa — revisar tese")
    return NEUTRO, reasons


def build_row(item: dict, tech: dict, fwd_pe: float | None, margin_pct: float) -> RadarRow:
    status, dist = zone_status(tech["price"], item.get("zone_min"), item.get("zone_max"))
    v, why = verdict(tech, status, item.get("fair_value"), fwd_pe, margin_pct)
    return RadarRow(item["ticker"], tech["price"], item.get("zone_min"),
                    item.get("zone_max"), status, dist, v, why)
