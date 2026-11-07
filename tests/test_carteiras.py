import pandas as pd
import yaml

from pwass.engine import backtest, carteiras, strategies as ST
from tests import regressao


def _m():
    return ST.monthly(pd.read_parquet(regressao.FIX / "precos_carteiras.parquet"))


def test_retornos_iguais_ao_pipeline_original():
    m = _m()
    cfg = yaml.safe_load((regressao.ROOT / "config/estrategias.yaml").read_text(encoding="utf-8"))
    models = {k: {**v, "id": k} for k, v in cfg["carteiras"].items() if k in ("gem", "sp500", "global_60_40")}
    got = carteiras.retornos(models, m)
    for k, d in models.items():
        ref = backtest.run(ST.model_weights(d, m), m)
        pd.testing.assert_series_equal(got[d["nome"]], ref)


def test_converter_e_recortar():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    r = {"A": pd.Series([0.01] * 6, index=idx)}
    fx = pd.Series([5.0, 5.0, 5.5, 5.5, 5.5, 5.0], index=idx)
    brl = carteiras.converter_brl(r, fx, pd.Series([0.005] * 4, index=idx[:4]))
    assert set(brl) == {"A", "CDI (renda fixa BR)"}
    rec, end = carteiras.recortar(brl, idx[1])
    assert end == idx[3] and all(len(v) <= 3 for v in rec.values())


def test_formatar_metricas():
    met = pd.DataFrame({"x": {"Retorno a.a. (CAGR)": 0.0856, "Sharpe": 0.73, "Meses": 222.0}})
    f = carteiras.formatar_metricas(met)
    assert f.loc["Retorno a.a. (CAGR)", "x"] == "+8,6%" and f.loc["Sharpe", "x"] == "0,73" and f.loc["Meses", "x"] == "222"
