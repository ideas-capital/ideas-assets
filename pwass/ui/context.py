"""Monta o pacote de dados de um ativo — usado na tela e enviado à IA."""
from __future__ import annotations

import math

from pwass.data import market
from pwass.engine import indicators, valuation
from pwass.ui import cache


def _clean(d: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in d.items()}


def asset_bundle(ticker: str) -> dict:
    """Fundamentos + técnica + Piotroski + DCF reverso de um ticker."""
    f = cache.fundamentals(ticker)
    close = cache.history(ticker)
    tech = indicators.snapshot(close)
    try:
        pio = valuation.piotroski(cache.statements(ticker))
    except Exception:  # noqa: BLE001
        pio = {"score": None, "max": 0, "tests": None}

    dcf = {"moedas_iguais": market.same_currency(f)}
    if dcf["moedas_iguais"] and f.get("fcf") and f.get("shares") and tech["price"]:
        fcf_ps = f["fcf"] / f["shares"]
        dcf.update({"fcf_por_acao": fcf_ps,
                    "crescimento_implicito_5a": valuation.reverse_dcf(tech["price"], fcf_ps),
                    "premissas": "desconto 9% a.a., terminal 2,5%"})
        dcf["graham"] = valuation.graham_number(f.get("eps_ttm"), f.get("book_value"))

    rets = {f"retorno_{k}": (close.iloc[-1] / close.iloc[-n] - 1) if len(close) > n else None
            for k, n in {"1m": 22, "3m": 64, "12m": 253, "3a": 757}.items()}
    fund = {k: v for k, v in f.items() if k != "summary"}
    return {
        "ticker": ticker,
        "fundamentos": _clean(fund),
        "descricao": (f.get("summary") or "")[:900],
        "tecnica": _clean(tech),
        "retornos": rets,
        "piotroski": {"pontos": pio["score"], "de": pio["max"]},
        "dcf": _clean(dcf),
        "_close": close,          # uso interno (gráficos) — removido antes de ir para a IA
        "_piotroski_tests": pio["tests"],
        "_fund_raw": f,
    }


def for_ai(bundle: dict) -> dict:
    return {k: v for k, v in bundle.items() if not k.startswith("_")}
