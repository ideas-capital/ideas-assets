import numpy as np
import pandas as pd

from pwass.engine import comparar as C, diario as D


def test_alinhar_cripto_com_acao_usa_dias_uteis():
    cripto = pd.Series(np.arange(1, 15, dtype=float), index=pd.date_range("2024-01-01", periods=14, freq="D"))
    acao = pd.Series(np.arange(1, 11, dtype=float), index=pd.bdate_range("2024-01-01", periods=10))
    df, info = C.alinhar({"BTC": cripto, "AAA": acao})
    assert (df.index.dayofweek < 5).all() and len(df) == 10
    assert info["ppy"] == 252 and info["misto"] and info["descartados"]["BTC"] == 4 and info["descartados"]["AAA"] == 0


def test_alinhar_so_cripto_usa_365():
    idx = pd.date_range("2024-01-01", periods=30, freq="D")
    df, info = C.alinhar({"A": pd.Series(range(1, 31), index=idx, dtype=float), "B": pd.Series(range(2, 32), index=idx, dtype=float)})
    assert info["ppy"] == 365 and not info["misto"] and len(df) == 30


def test_base100_metricas_correlacao():
    idx = pd.bdate_range("2023-01-02", periods=260)
    a = pd.Series(np.linspace(100, 150, 260), index=idx)
    b = pd.Series(np.linspace(100, 150, 260)[::-1] + 50, index=idx)
    df = pd.concat({"A": a, "B": b}, axis=1)
    assert (C.base100(df).iloc[0] == 100).all()
    m = C.metricas(df)
    assert abs(m.loc["A", "Retorno no período"] - 0.5) < 1e-12 and m.loc["B", "Pior queda"] < 0 and m.loc["A", "Pior queda"] == 0
    assert C.correlacao(df).loc["A", "A"] == 1.0


def _regra():
    return pd.DataFrame({"Entrada": pd.to_datetime(["2024-03-04", "2024-06-03"]), "Saída": pd.to_datetime(["2024-03-12", "2024-06-10"]),
                         "Retorno": [0.05, -0.02]})


def test_diario_resultado_e_par_da_regra():
    t = {"entrada_data": "2024-03-05", "entrada_preco": 100, "saida_data": "2024-03-14", "saida_preco": 110}
    assert abs(D.resultado(t) - 0.10) < 1e-12 and D.resultado({"entrada_preco": 100}) is None
    p = D.par_da_regra(t, _regra())
    assert p["regra_retorno"] == 0.05 and p["dif_entrada_dias"] == 1 and p["dif_saida_dias"] == 2
    assert D.par_da_regra({**t, "entrada_data": "2024-04-15"}, _regra()) is None       # a regra não mandava entrar
    assert D.par_da_regra(t, pd.DataFrame()) is None


def test_diario_resumo():
    par = {"regra_retorno": 0.04}
    r = D.resumo([{"real": 0.10, "par": par}, {"real": -0.05, "par": None}, {"real": None, "par": None}])
    assert r["operacoes"] == 2 and r["acerto_real"] == 0.5 and r["seguiu_regra"] == 0.5
    assert abs(r["retorno_medio_real"] - 0.025) < 1e-12 and r["retorno_medio_real_pareadas"] == 0.10 and r["retorno_medio_regra_pareadas"] == 0.04
    assert np.isnan(D.resumo([])["acerto_real"])
