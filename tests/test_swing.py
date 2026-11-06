import numpy as np
import pandas as pd

from pwass.engine import swing as S

P = {"pullback": {"rsi_periodo": 2, "rsi_entrada": 10, "rsi_perto": 25, "mm_tendencia": 200, "mm_saida": 5},
     "cruzamento": {"rapida": 20, "lenta": 50, "mm_tendencia": 200},
     "rompimento": {"canal_entrada": 55, "canal_saida": 20, "volume_minimo": 1.5}}
RISK = {"capital_laboratorio_usd": 5000, "risco_por_operacao": 0.01, "posicao_maxima": 0.25,
        "custo_por_lado": 0.001, "multiplo_atr_stop": 2.0, "alvos_em_r": [1.5, 3.0]}


def _ohlcv(close, vol=None):
    close = np.asarray(close, dtype=float)
    idx = pd.bdate_range("2015-01-01", periods=len(close))
    o = np.r_[close[0], close[:-1]]
    return pd.DataFrame({"Open": o, "High": np.maximum(o, close) * 1.005, "Low": np.minimum(o, close) * 0.995,
                         "Close": close, "Volume": vol if vol is not None else np.full(len(close), 1e6)}, index=idx)


def test_execution_is_next_open_no_lookahead():
    # Tendência de alta com uma queda forte no dia 400: o sinal sai no fechamento, a compra na abertura seguinte
    c = np.linspace(100, 200, 500)
    c[400:403] = c[399] * np.array([0.95, 0.92, 0.90])
    df = _ohlcv(c)
    bt = S.backtest(df, "pullback", P["pullback"], cost=0)
    first = bt.trades.iloc[0]
    sig = S.signals(df, "pullback", P["pullback"])
    signal_day = sig.index[sig["entry"]][0]
    assert first["Entrada"] > signal_day
    assert first["Preço entrada"] == df.loc[first["Entrada"], "Open"]


def test_costs_reduce_results():
    rng = np.random.default_rng(3)
    df = _ohlcv(100 * np.cumprod(1 + rng.normal(0.0006, 0.015, 1500)))
    r0 = S.backtest(df, "pullback", P["pullback"], cost=0).trades["Retorno"].sum()
    r1 = S.backtest(df, "pullback", P["pullback"], cost=0.002).trades["Retorno"].sum()
    assert r1 < r0


def test_breakout_respects_stop():
    c = np.r_[np.full(300, 100.0), np.linspace(100, 130, 30), np.full(20, 80.0)]
    vol = np.full(len(c), 1e6)
    vol[300:330] = 5e6  # volume forte no rompimento
    df = _ohlcv(c, vol)
    bt = S.backtest(df, "rompimento", P["rompimento"], cost=0, atr_mult=2.0)
    assert len(bt.trades) >= 1
    worst = bt.trades["Retorno"].min()
    assert worst > -0.30  # o stop de 2×ATR corta a perda antes da queda inteira de 130 para 80


def test_all_strategies_run_and_stats_are_consistent():
    rng = np.random.default_rng(7)
    df = _ohlcv(100 * np.cumprod(1 + rng.normal(0.0005, 0.02, 2000)), rng.uniform(1e6, 3e6, 2000))
    for sid, p in P.items():
        bt = S.backtest(df, sid, p)
        st = S.stats(bt)
        assert 0 <= st["Tempo posicionado"] <= 1
        if st["Operações"]:
            assert 0 <= st["Taxa de acerto"] <= 1
        status, _ = S.status_today(df, sid, p, bt)
        assert status in (S.COMPRA, S.SAIR, S.POSICAO, S.PERTO, S.AGUARDAR, S.EVITAR)


def test_plan_risks_one_percent():
    df = _ohlcv(np.linspace(50, 60, 300))
    p = S.plan(df, RISK)
    assert p["stop"] < p["entrada"] < p["alvo1"] < p["alvo2"]
    assert p["risco_usd"] <= 50 + 1e-6 and p["valor"] <= 1250 + 1e-6


def test_quality_labels():
    assert S.quality({"Operações": 3, "Profit factor": 9}) == "Pouco histórico"
    assert S.quality({"Operações": 20, "Profit factor": 2.0, "Resultado médio": 0.01}) == "Bom"
    assert S.quality({"Operações": 20, "Profit factor": 1.2, "Resultado médio": 0.001}) == "Regular"
    assert S.quality({"Operações": 20, "Profit factor": 0.7, "Resultado médio": -0.01}) == "Fraco"
