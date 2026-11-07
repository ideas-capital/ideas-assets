import numpy as np
import pandas as pd
import yaml

from pwass.engine import fatores as F
from tests import regressao

SW = yaml.safe_load((regressao.ROOT / "config/swing.yaml").read_text(encoding="utf-8"))


def _spy():
    raw = pd.read_parquet(regressao.FIX / "ohlcv_swing.parquet")
    return raw[raw.Ticker == "SPY"].drop(columns="Ticker").set_index("Date")


def test_fatores_de_cada_estrategia_tem_lado_valido_e_numero():
    df = _spy()
    for sid, p in SW["estrategias"].items():
        fs = F.fatores(df, sid, p, regime="DEFENSIVO", historico="Fraco", outras_estrategias={"X": "COMPRA", "Y": "EVITAR"})
        assert fs and all(l in ("favor", "contra", "neutro") for t, l in fs)
        assert all("." not in t for t, _ in fs) and any(ch.isdigit() for ch in fs[0][0])
        assert ("Regime de mercado DEFENSIVO", "contra") in fs and ("Histórico da regra neste ativo: fraco", "contra") in fs
        assert ("X também em COMPRA", "favor") in fs and ("Y: ativo fora do filtro de tendência", "contra") in fs


def test_tendencia_de_alta_e_favor_e_queda_e_contra():
    idx = pd.bdate_range("2023-01-02", periods=400)
    up = np.linspace(50, 150, 400)
    mk = lambda c: pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6}, index=idx)
    p = SW["estrategias"]["pullback"]
    assert F.fatores(mk(up), "pullback", p)[0][1] == "favor"
    assert F.fatores(mk(up[::-1].copy()), "pullback", p)[0][1] == "contra"
    assert F.resumo([("a", "favor"), ("b", "contra"), ("c", "contra"), ("d", "neutro")]) == (1, 2)
