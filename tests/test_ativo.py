import pandas as pd

from pwass.engine import ativo


def test_classe():
    assert ativo.classe("ETF", "SPY") == "ETF" and ativo.classe("EQUITY", "AAPL") == "Ação"
    assert ativo.classe(None, "BTC-USD") == "Cripto" and ativo.classe(None, "^GSPC") == "Índice"
    assert ativo.classe(None, "AAPL") == "Desconhecida"      # sem evidência, não assume Ação


def test_performance_por_calendario():
    idx = pd.date_range("2020-01-01", "2025-06-30", freq="D")     # cripto-like: todos os dias
    s = pd.Series(range(1, len(idx) + 1), index=idx, dtype=float)
    p = ativo.performance(s)
    ini = pd.Timestamp("2025-06-30") - pd.DateOffset(months=1)
    assert abs(p["1M"] - (s.iloc[-1] / s[ini] - 1)) < 1e-12
    assert all(v is not None for v in p.values())
    curto = ativo.performance(s.iloc[-100:])
    assert curto["1A"] is None and curto["5A"] is None and curto["1M"] is not None
