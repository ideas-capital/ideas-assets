import numpy as np
import pandas as pd

from pwass.ai import openrouter
from pwass.data import brasil
from pwass.engine import backtest, health, strategies


def _daily(values, weekends=False):
    idx = pd.date_range("2022-01-03", periods=len(values), freq="D" if weekends else "B")
    return pd.Series(values, index=idx, dtype=float)


def test_health_states():
    up = _daily(100 * np.exp(np.linspace(0, 0.3, 600)) * (1 + 0.003 * np.sin(np.arange(600))))
    assert health.price_health(up, stretch=0.25, rsi_hot=101)["status"] == "Alta saudável"
    down = _daily(100 * np.exp(np.linspace(0, -0.5, 600)))
    assert health.price_health(down)["status"] == "Tendência de baixa"
    rocket = _daily(np.r_[np.full(400, 100.0), np.linspace(100, 200, 200)])
    assert health.price_health(rocket, stretch=0.25)["status"] == "Esticado"


def test_health_requires_positive_12m_for_healthy():
    # Tendência de 200 dias subindo, mas há 1 ano o preço estava num pico mais alto que hoje
    v = np.linspace(100, 150, 600)
    v[600 - 275:600 - 245] = 300  # pico há ~1 ano, fora da janela da MM200
    h = health.price_health(_daily(v), stretch=0.9, rsi_hot=101)
    assert h["mm200_subindo"] and h["ret_12m"] < 0
    assert h["status"] == "Recuperando"


def test_crypto_annualization_uses_365():
    s = _daily(np.linspace(1, 2, 400), weekends=True)
    assert health._periods_per_year(s) == 365


def test_percentile_and_rates():
    s = pd.Series([1, 2, 3, 4, 5.0])
    assert health.percentile(s) == 100.0
    assert round(health.real_rate(13.75, 4.95), 2) == 8.38
    assert health.fx_breakeven(10, 10) == 0


def test_tesouro_parse_and_implied():
    raw = ("Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;"
           "PU Venda Manha;PU Base Manha\n"
           "Tesouro Prefixado;01/01/2032;05/11/2026;15,34;15,46;481,63;478,1;478,1\n"
           "Tesouro IPCA+;15/08/2032;05/11/2026;7,92;8,04;3082,39;3060;3060\n"
           "Tesouro Selic;01/03/2029;05/11/2026;0,06;0,07;20216,19;20200;20200\n").encode()
    df = brasil.parse_tesouro(raw)
    today = brasil.tesouro_hoje(df)
    assert set(today["Titulo"]) == {"Tesouro Prefixado", "Tesouro IPCA+", "Tesouro Selic"}
    imp = brasil.implied_inflation(today)
    assert round(imp["Inflação implícita %"].iloc[0], 2) == round((1.1534 / 1.0792 - 1) * 100, 2)


def test_model_portfolios_and_brl():
    idx = pd.date_range("2015-01-31", periods=30, freq="ME")
    m = pd.DataFrame({t: np.linspace(100, 130, 30) for t in strategies.MODEL_TICKERS}, index=idx)
    w = strategies.model_weights({"id": "x", "tipo": "fixa", "pesos": {"VTI": 0.6, "AGG": 0.4}}, m)
    assert np.allclose(w.sum(axis=1), 1)
    r = pd.Series(0.01, index=idx[1:])
    fx = pd.Series(np.r_[5.0, np.full(29, 5.05)], index=idx)  # dólar sobe 1% no 1º mês
    brl = backtest.to_brl(r, fx)
    assert np.isclose(brl.iloc[0], 1.01 * 1.01 - 1) and np.isclose(brl.iloc[1], 0.01)
    cdi = backtest.cdi_monthly(pd.Series([1.0], index=[pd.Timestamp("2026-10-01")]))
    assert cdi.index[0] == pd.Timestamp("2026-10-31") and cdi.iloc[0] == 0.01


def test_provider_routing():
    assert openrouter.split_model("anthropic/claude-haiku-5.5") == ("openrouter", "anthropic/claude-haiku-5.5")
    assert openrouter.split_model("gemini:gemini-3.8-flash") == ("gemini", "gemini-3.8-flash")
    assert openrouter.split_model("ollama:qwen3:8b") == ("ollama", "qwen3:8b")
    assert openrouter.split_model("google/gemma-4-31b-it:free")[0] == "openrouter"
    p = openrouter.build_payload("gemini:gemini-3.8-flash", [], web_search=True)
    assert p["model"] == "gemini-3.8-flash" and "plugins" not in p
