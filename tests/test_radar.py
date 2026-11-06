import numpy as np
import pandas as pd

from pwass.engine import indicators, radar


def _series(values):
    idx = pd.bdate_range("2021-01-01", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def test_zone_status():
    assert radar.zone_status(190, 180, 195) == ("NA ZONA", 0.0)
    st, d = radar.zone_status(200, 180, 195)
    assert st == "ACIMA" and round(d, 1) == 2.5
    st, d = radar.zone_status(170, 180, 195)
    assert st == "ABAIXO" and d < 0
    assert radar.zone_status(190, None, None)[0] == "SEM ZONA"


def test_rsi_bounds_and_trend():
    up = _series(np.linspace(100, 200, 300))
    assert indicators.rsi(up).iloc[-1] == 100.0
    noise = _series(100 + np.random.default_rng(0).normal(0, 1, 300).cumsum())
    r = indicators.rsi(noise).dropna()
    assert r.between(0, 100).all()


def test_verdict_stretched_wins():
    tech = {"price": 150, "sma200": 100, "rsi14": 60}
    v, _ = radar.verdict(tech, "NA ZONA")
    assert v == radar.EVITAR


def test_verdict_forte_compra_needs_fair_value():
    tech = {"price": 80, "sma200": 90, "rsi14": 40}
    assert radar.verdict(tech, "NA ZONA")[0] == radar.AGUARDAR
    assert radar.verdict(tech, "NA ZONA", fair_value=110, margin_pct=20)[0] == radar.FORTE_COMPRA


def test_snapshot_runs_on_5y():
    s = _series(100 + np.random.default_rng(1).normal(0, 1, 1300).cumsum() + 200)
    snap = indicators.snapshot(s)
    assert {"price", "sma200", "rsi14", "mayer"} <= snap.keys()
    assert not np.isnan(snap["sma200_w"])
