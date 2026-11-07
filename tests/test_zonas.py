import numpy as np
import pandas as pd

from pwass.engine import zonas

RISK = {"capital_laboratorio_usd": 5000, "risco_por_operacao": 0.01, "posicao_maxima": 0.25,
        "multiplo_atr_stop": 2.0, "alvos_em_r": [1.5, 3.0]}


def _df(n=300):
    c = 100 + 10 * np.sin(np.arange(n) / 8) + np.arange(n) * 0.05
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1e6}, index=idx)


def test_plano_usa_regras_de_risco():
    df = _df()
    p = zonas.plano_zona(df, 90, 100, RISK)
    assert p["entrada"] == 95 and abs(p["stop"] - (95 - p["R"])) < 1e-9
    assert abs(p["R"] - 2.0 * p["atr"]) < 1e-9
    assert abs(p["alvo1"] - (95 + 1.5 * p["R"])) < 1e-9 and abs(p["alvo2"] - (95 + 3 * p["R"])) < 1e-9
    assert abs(p["risco_usd"] - min(5000 * 0.01, p["quantidade"] * p["R"])) < 1e-6 or p["valor"] <= 1250 + 1e-6
    assert p["valor"] <= 5000 * 0.25 + 1e-6               # teto de posição
    assert all(isinstance(t, str) and o in ("observado", "calculado") for t, o in p["justificativas"])


def test_status_da_zona_e_ordem_invertida():
    df = _df()
    last = float(df["Close"].iloc[-1])
    assert zonas.plano_zona(df, last - 1, last + 1, RISK)["status"] == "NA ZONA"
    acima = zonas.plano_zona(df, last * 0.8, last * 0.9, RISK)
    assert acima["status"] == "ACIMA DA ZONA" and acima["dist_pct"] > 0
    assert zonas.plano_zona(df, last * 0.9, last * 0.8, RISK)["entrada"] == acima["entrada"]   # min/max trocados
    assert zonas.plano_zona(df, last * 1.1, last * 1.2, RISK)["status"] == "ABAIXO DA ZONA"
