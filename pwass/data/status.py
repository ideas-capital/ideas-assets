"""Status das fontes de dados: testa cada uma com uma chamada curta e informa ok/falha, latência e última data.

`checar(testes)` recebe {nome: função} (cada função devolve a data/rótulo do dado mais recente ou levanta erro),
o que permite testar sem rede. `testes_padrao(user_agent)` monta os testes reais.
"""
from __future__ import annotations

import time
from typing import Callable


def checar(testes: dict[str, Callable[[], str]]) -> list[dict]:
    """[{fonte, ok, latencia_s, ultimo_dado, erro}] — uma falha nunca interrompe as outras."""
    out = []
    for nome, fn in testes.items():
        t0 = time.perf_counter()
        try:
            ultimo = str(fn())
            out.append({"fonte": nome, "ok": True, "latencia_s": round(time.perf_counter() - t0, 2), "ultimo_dado": ultimo, "erro": ""})
        except Exception as e:  # noqa: BLE001
            out.append({"fonte": nome, "ok": False, "latencia_s": round(time.perf_counter() - t0, 2), "ultimo_dado": "—", "erro": str(e)[:160]})
    return out


def testes_padrao(user_agent: str) -> dict[str, Callable[[], str]]:
    from pwass.data import brasil, fred, market, sec

    def yahoo():
        s = market.history("SPY", "1mo")
        return f"{s.index[-1]:%d/%m/%Y} (SPY)"

    def fred_():
        s = fred.series("DGS10")
        return f"{s.index[-1]:%d/%m/%Y} (juro 10a EUA)"

    def bcb():
        s = brasil.sgs(brasil.SGS["cdi_mes"], last=1)
        return f"{s.index[-1]:%m/%Y} (CDI mensal)"

    def focus():
        v, d = brasil.focus_ipca_12m()
        return f"{d} (IPCA 12m esperado)"

    def tesouro():
        df = brasil.tesouro()
        return f"{df.iloc[:, 0].size} linhas"

    def sec_():
        m = sec.cik_map(user_agent)
        return f"{len(m)} empresas mapeadas"

    return {"Yahoo Finance (preços)": yahoo, "FRED (macro EUA)": fred_, "Banco Central — SGS": bcb,
            "Banco Central — Focus": focus, "Tesouro Transparente": tesouro, "SEC EDGAR": sec_}
