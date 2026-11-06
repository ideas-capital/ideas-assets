import numpy as np
import pandas as pd

from pwass.engine import screener


def _ohlcv(close, vol=1e6):
    close = np.asarray(close, float)
    idx = pd.bdate_range("2023-01-02", periods=len(close))
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Volume": np.full(len(close), vol)}, index=idx)


def test_technical_colunas_e_valores():
    d = _ohlcv(np.linspace(50, 100, 300))
    d.loc[d.index[-1], "Volume"] = 3e6
    t = screener.technical({"UP": d, "CURTO": _ohlcv(np.linspace(1, 2, 50))})
    assert list(t.index) == ["UP"]                       # histórico curto fica de fora
    r = t.loc["UP"]
    assert abs(r["Vol. relativo"] - 3.0) < 1e-9 and r["vs MM200"] > 0 and r["vs MM50"] > 0
    assert 0 < r["ATR %"] < 0.05 and r["RSI 14"] > 70


def _base():
    return pd.DataFrame({"Grupo": ["A", "A", "B"], "Setor": ["Tec", "Saúde", "Tec"], "Dia": [0.03, -0.01, 0.0],
                         "Vol. relativo": [2.0, 0.5, np.nan], "RSI 14": [75, 25, 50], "vs MM50": [0.1, -0.1, 0.0],
                         "vs MM200": [0.2, -0.2, 0.05], "Valor de mercado": [5e11, 2e9, np.nan],
                         "Situação": ["COMPRA", "EVITAR", "AGUARDAR"], "Profit factor": [2.0, 0.8, np.nan],
                         "ATR %": [0.02, 0.05, 0.03]}, index=["X", "Y", "Z"])


def test_filtros_combinam_e_nan_nao_passa():
    df = _base()
    assert list(screener.apply_filters(df, {}).index) == ["X", "Y", "Z"]
    assert list(screener.apply_filters(df, {"grupos": ["A"], "setores": ["Tec"]}).index) == ["X"]
    assert list(screener.apply_filters(df, {"vol_rel_min": 1.0}).index) == ["X"]          # NaN (Z) não passa
    assert list(screener.apply_filters(df, {"rsi": (20, 30), "mm200": "abaixo"}).index) == ["Y"]
    assert list(screener.apply_filters(df, {"mcap_min": 1e10}).index) == ["X"]
    assert list(screener.apply_filters(df, {"situacao": ["COMPRA"], "pf_min": 1.5, "atr_max": 0.03}).index) == ["X"]
    assert list(screener.apply_filters(df, {"dia": (0.0, 0.05)}).index) == ["X", "Z"]


def test_chips_descrevem_criterios():
    c = screener.chips({"rsi": (20, 30), "mm200": "acima", "pf_min": 1.5, "vol_rel_min": 1.5})
    assert "RSI 20–30" in c and "Preço acima da MM200" in c and "Profit factor ≥ 1,5" in c and "Volume ≥ 1,5× a média" in c
