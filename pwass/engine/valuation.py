"""Valuation: Piotroski F-Score, número de Graham e DCF (direto e reverso).

- Piotroski (2000), "Value Investing: The Use of Historical Financial Statement
  Information": 9 testes binários de saúde financeira. 8–9 = forte; 0–2 = fraco.
- Graham: preço máximo "defensivo" = √(22,5 × LPA × VPA). Útil para empresas
  maduras; quase sempre "caro" para tecnologia — leia com esse filtro.
- DCF reverso (Mauboussin & Rappaport, "Expectations Investing"): em vez de
  adivinhar o crescimento, pergunta QUANTO crescimento o preço atual embute.
"""
from __future__ import annotations

import math

import pandas as pd


def _row(df: pd.DataFrame, *names: str) -> pd.Series | None:
    for n in names:
        if df is not None and n in df.index:
            return pd.to_numeric(df.loc[n], errors="coerce")
    return None


def piotroski(st: dict[str, pd.DataFrame]) -> dict:
    """Recebe demonstrativos anuais (colunas: ano mais recente primeiro)."""
    inc, bs, cf = st.get("income"), st.get("balance"), st.get("cashflow")
    ni = _row(inc, "Net Income", "Net Income Common Stockholders")
    rev = _row(inc, "Total Revenue", "Operating Revenue")
    gp = _row(inc, "Gross Profit")
    ta = _row(bs, "Total Assets")
    ltd = _row(bs, "Long Term Debt", "Long Term Debt And Capital Lease Obligation")
    ca = _row(bs, "Current Assets")
    cl = _row(bs, "Current Liabilities")
    sh = _row(bs, "Ordinary Shares Number", "Share Issued")
    cfo = _row(cf, "Operating Cash Flow")

    def v(s, i):
        try:
            x = float(s.iloc[i])
            return None if math.isnan(x) else x
        except (AttributeError, IndexError, TypeError, ValueError):
            return None

    def div(a, b):
        return a / b if a is not None and b not in (None, 0) else None

    tests = []

    def add(name, ok, explain):
        tests.append({"Teste": name, "Passou": None if ok is None else bool(ok), "Como ler": explain})

    roa0, roa1 = div(v(ni, 0), v(ta, 0)), div(v(ni, 1), v(ta, 1))
    add("Lucro positivo (ROA > 0)", None if roa0 is None else roa0 > 0, "Dá lucro sobre os ativos.")
    add("Caixa operacional positivo", None if v(cfo, 0) is None else v(cfo, 0) > 0, "Gera caixa de verdade.")
    add("ROA melhorou", None if None in (roa0, roa1) else roa0 > roa1, "Rentabilidade subindo.")
    add("Caixa > lucro (qualidade)", None if None in (v(cfo, 0), v(ni, 0)) else v(cfo, 0) > v(ni, 0),
        "Lucro lastreado em caixa, não em contabilidade.")
    lev0, lev1 = div(v(ltd, 0), v(ta, 0)), div(v(ltd, 1), v(ta, 1))
    add("Endividamento caiu", None if None in (lev0, lev1) else lev0 <= lev1, "Dívida longa / ativos menor.")
    cr0, cr1 = div(v(ca, 0), v(cl, 0)), div(v(ca, 1), v(cl, 1))
    add("Liquidez corrente melhorou", None if None in (cr0, cr1) else cr0 > cr1, "Mais folga de curto prazo.")
    add("Sem emissão de ações", None if None in (v(sh, 0), v(sh, 1)) else v(sh, 0) <= v(sh, 1) * 1.005,
        "Não diluiu o acionista.")
    gm0, gm1 = div(v(gp, 0), v(rev, 0)), div(v(gp, 1), v(rev, 1))
    add("Margem bruta melhorou", None if None in (gm0, gm1) else gm0 > gm1, "Poder de preço/custos.")
    at0, at1 = div(v(rev, 0), v(ta, 0)), div(v(rev, 1), v(ta, 1))
    add("Giro do ativo melhorou", None if None in (at0, at1) else at0 > at1, "Usa melhor os ativos.")

    valid = [t for t in tests if t["Passou"] is not None]
    score = sum(t["Passou"] for t in valid)
    return {"score": score, "max": len(valid), "tests": pd.DataFrame(tests)}


def graham_number(eps: float | None, bvps: float | None) -> float | None:
    if not eps or not bvps or eps <= 0 or bvps <= 0:
        return None
    return math.sqrt(22.5 * eps * bvps)


def dcf_value(fcf_ps: float, growth: float, discount: float = 0.09,
              terminal: float = 0.025, years: int = 10) -> float:
    """DCF em 2 estágios: crescimento `growth` nos 5 primeiros anos, depois
    desacelera linearmente até `terminal` no ano 10; perpetuidade de Gordon."""
    if discount <= terminal:
        raise ValueError("Taxa de desconto deve ser maior que o crescimento terminal")
    value, cash = 0.0, fcf_ps
    for y in range(1, years + 1):
        g = growth if y <= 5 else growth + (terminal - growth) * (y - 5) / (years - 5)
        cash *= 1 + g
        value += cash / (1 + discount) ** y
    tv = cash * (1 + terminal) / (discount - terminal)
    return value + tv / (1 + discount) ** years


def reverse_dcf(price: float, fcf_ps: float, discount: float = 0.09,
                terminal: float = 0.025) -> float | None:
    """Crescimento anual (anos 1–5) que faz o DCF igualar o preço atual."""
    if fcf_ps is None or fcf_ps <= 0 or price <= 0:
        return None
    lo, hi = -0.5, 1.5
    if dcf_value(fcf_ps, hi, discount, terminal) < price:
        return hi  # exige mais de 150% a.a. — fora do razoável
    for _ in range(100):
        mid = (lo + hi) / 2
        if dcf_value(fcf_ps, mid, discount, terminal) < price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
