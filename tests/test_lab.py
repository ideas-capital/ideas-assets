import numpy as np
import pandas as pd

from pwass.engine import lab


def test_retorno_por_ano_composto():
    idx = pd.to_datetime(["2023-06-01", "2023-06-02", "2024-01-02"])
    r = pd.Series([0.10, 0.10, -0.50], index=idx)
    out = lab.retorno_por_ano(r)
    assert abs(out[2023] - 0.21) < 1e-12 and abs(out[2024] + 0.5) < 1e-12


def test_curva_media_e_drawdown():
    idx = pd.bdate_range("2024-01-01", periods=3)
    a = pd.Series([0.10, 0.0, 0.0], index=idx)
    b = pd.Series([0.0, 0.0, -0.10], index=idx)
    eq = lab.curva_media({"a": a, "b": b})
    assert np.allclose(eq.values, [1.05, 1.05, 1.05 * 0.95])
    assert abs(lab.drawdown_curva(eq).iloc[-1] + 0.05) < 1e-12
    assert lab.curva_media({}).empty


def test_comparar_usa_mesmas_regras_do_swing():
    """A tabela do laboratório tem de bater com swing.stats/pooled (regra não mudou)."""
    import yaml
    from pwass.engine import swing as S
    from tests import regressao
    sw = yaml.safe_load((regressao.ROOT / "config/swing.yaml").read_text(encoding="utf-8"))
    raw = pd.read_parquet(regressao.FIX / "ohlcv_swing.parquet")
    data = {t: g.drop(columns="Ticker").set_index("Date") for t, g in raw.groupby("Ticker")}
    tab, curvas = lab.comparar(data, sw)
    assert len(tab) == 3 and "Buy & hold (mesmo universo)" in curvas
    sid = "pullback"
    bts = [S.backtest(df, sid, sw["estrategias"][sid], sw["risco"]["custo_por_lado"], sw["risco"]["multiplo_atr_stop"])
           for df in data.values()]
    pool = S.pooled(bts)
    row = tab[tab.id == sid].iloc[0]
    assert row["Operações"] == pool["Operações"] and abs(row["Profit factor"] - pool["Profit factor"]) < 1e-12
