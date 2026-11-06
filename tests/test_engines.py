import numpy as np
import pandas as pd

from pwass.engine import backtest, factors, strategies, valuation


def _monthly(cols, n=60, seed=0, drift=None):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-31", periods=n, freq="ME")
    data = {}
    for i, c in enumerate(cols):
        mu = (drift or {}).get(c, 0.005)
        data[c] = 100 * np.cumprod(1 + rng.normal(mu, 0.03, n))
    return pd.DataFrame(data, index=idx)


def test_gem_picks_us_when_us_leads():
    m = _monthly(["SPY", "VEU", "BIL", "AGG"], drift={"SPY": 0.03, "VEU": 0.0, "BIL": 0.001})
    w = strategies.gem_weights(m)
    assert (w.sum(axis=1).round(6) == 1).all()
    assert strategies.gem_explain(m)["pick"] == "SPY"


def test_gem_goes_defensive_when_stocks_lose_to_cash():
    m = _monthly(["SPY", "VEU", "BIL", "AGG"], drift={"SPY": -0.03, "VEU": -0.03, "BIL": 0.002})
    assert strategies.gem_explain(m)["pick"] == "AGG"


def test_gtaa_weights_sum_to_one():
    m = _monthly(strategies.GTAA_ASSETS + ["BIL"])
    w = strategies.gtaa_weights(m)
    assert np.allclose(w.sum(axis=1), 1)


def test_backtest_has_no_lookahead():
    m = _monthly(["A", "B"], n=4)
    # peso 100% em A decidido no mês 1 -> retorno do portfólio no mês 2 = retorno de A no mês 2
    w = pd.DataFrame({"A": [1.0, 1.0, 0.0, 0.0], "B": [0.0, 0.0, 1.0, 1.0]}, index=m.index)
    r = backtest.run(w, m)
    rets = m.pct_change()
    assert np.isclose(r.iloc[0], rets["A"].iloc[1])
    assert np.isclose(r.iloc[2], rets["B"].iloc[3])


def test_metrics_cagr():
    r = pd.Series([0.01] * 24, index=pd.date_range("2020-01-31", periods=24, freq="ME"))
    m = backtest.metrics(r)
    assert np.isclose(m["Retorno a.a. (CAGR)"], 1.01 ** 12 - 1)
    assert m["Pior queda (máx. drawdown)"] == 0


def test_reverse_dcf_inverts_dcf():
    price = valuation.dcf_value(5.0, 0.12)
    g = valuation.reverse_dcf(price, 5.0)
    assert abs(g - 0.12) < 1e-6


def test_graham():
    assert round(valuation.graham_number(4, 25), 2) == round((22.5 * 100) ** 0.5, 2)
    assert valuation.graham_number(-1, 10) is None


def test_piotroski_counts_available_tests():
    years = [pd.Timestamp("2025-12-31"), pd.Timestamp("2024-12-31")]
    inc = pd.DataFrame({years[0]: [120, 1000, 500], years[1]: [100, 900, 430]},
                       index=["Net Income", "Total Revenue", "Gross Profit"])
    bs = pd.DataFrame({years[0]: [2000, 300, 800, 400, 100], years[1]: [1900, 350, 700, 400, 100]},
                      index=["Total Assets", "Long Term Debt", "Current Assets",
                             "Current Liabilities", "Ordinary Shares Number"])
    cf = pd.DataFrame({years[0]: [200], years[1]: [150]}, index=["Operating Cash Flow"])
    out = valuation.piotroski({"income": inc, "balance": bs, "cashflow": cf})
    assert out["max"] == 9 and out["score"] == 9


def test_qvm_ranks_and_skips_currency_mismatch():
    idx = ["A", "B", "C"]
    fund = pd.DataFrame({
        "name": idx, "sector": "x", "country": "y",
        "fwd_pe": [10, 30, -5], "roe": [0.3, 0.1, -0.2], "gross_margin": [0.6, 0.4, 0.2],
        "op_margin": [0.3, 0.1, -0.1], "debt_equity": [20, 80, 200],
        "fcf": [10, 5, -1], "market_cap": [100, 100, 100],
        "currency": ["USD", "USD", "USD"], "fin_currency": ["USD", "EUR", "USD"],
    }, index=idx)
    days = pd.bdate_range("2024-01-01", periods=300)
    close = pd.DataFrame({"A": np.linspace(50, 100, 300), "B": np.linspace(100, 90, 300),
                          "C": np.linspace(100, 50, 300)}, index=days)
    out = factors.qvm(fund, close)
    assert out.index[0] == "A" and out.index[-1] == "C"
    assert bool(out.loc["B", "Moeda balanço ≠ preço"])


def test_macd_formula_e_historico():
    import numpy as np
    import pandas as pd
    from pwass.engine import indicators as I
    c = pd.Series(np.linspace(100, 150, 120) + np.sin(np.arange(120)))
    m = I.macd(c)
    ref = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    assert np.allclose(m["macd"].dropna(), ref.loc[m["macd"].dropna().index])
    assert np.allclose(m["hist"].dropna(), (m["macd"] - m["signal"]).dropna())
    assert m["macd"].iloc[:25].isna().all()      # sem valores antes da janela lenta


def test_pivot_points_classicos():
    from pwass.engine import indicators as I
    p = I.pivot_points(110, 90, 100)
    assert p["P"] == 100 and p["R1"] == 110 and p["S1"] == 90 and p["R2"] == 120 and p["S2"] == 80


def test_swing_pivots_e_suporte_resistencia():
    import numpy as np
    import pandas as pd
    from pwass.engine import indicators as I
    c = np.array([10, 11, 12, 13, 14, 13, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 13], float)
    idx = pd.bdate_range("2024-01-01", periods=len(c))
    df = pd.DataFrame({"High": c + .1, "Low": c - .1, "Close": c}, index=idx)
    pv = I.swing_pivots(df, 3, 3)
    assert list(pv.tipo) == ["topo", "fundo", "topo"] and pv.preco.iloc[0] == 14.1 and pv.preco.iloc[1] == 9.9
    assert (pv.confirmado_em > pv.data).all()      # nunca usa o futuro
    sr = I.support_resistance(df, 3, 3, lookback=100)
    assert sr["suportes"] == [9.9] and sr["resistencias"] == [14.1, 15.1]
