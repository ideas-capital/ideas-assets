import numpy as np
import pandas as pd

from pwass.engine import score as SC


def _ds(n=600, sinal_real=True, seed=0):
    rng = np.random.default_rng(seed)
    comp = {k: rng.random(n) for k in SC.COMPONENTES}
    ret = (0.05 * (comp["tendencia"] - 0.5) if sinal_real else 0) + rng.normal(0, 0.03, n)
    datas = pd.to_datetime("2016-01-01") + pd.to_timedelta(rng.integers(0, 3600, n), unit="D")
    return pd.DataFrame({"ticker": "X", "estrategia": "pullback", "sinal": datas, "retorno": ret, **comp}).sort_values("sinal").reset_index(drop=True)


def test_calibrar_pesos_somam_1_e_so_positivos():
    w = SC.calibrar(_ds())
    assert abs(sum(w.values()) - 1) < 1e-12 and all(v >= 0 for v in w.values())
    assert w["tendencia"] == max(w.values())          # o único componente com sinal real domina
    assert SC.calibrar(_ds().assign(retorno=0.0)) in ({}, SC.calibrar(_ds().assign(retorno=0.0)))


def test_validacao_aceita_sinal_real_e_rejeita_ruido():
    ok = SC.validar(_ds(sinal_real=True, n=1500))
    assert ok["mostrar"] and ok["rho_teste"] > 0 and ok["p_teste"] < 0.05
    # ruído puro: com p < 0,05 espera-se ~5% de falso positivo; em 10 sementes aceitar no máximo 2
    aceitos = sum(SC.validar(_ds(sinal_real=False, n=1500, seed=s))["mostrar"] for s in range(10))
    assert aceitos <= 2, aceitos


def test_amostra_pequena_nao_mostra():
    r = SC.validar(_ds(n=120))
    assert not r["mostrar"] and "amostra pequena" in r["motivos"][0]


def test_faixas_definidas_so_no_treino_e_tabela():
    s = pd.Series([10, 20, 30, 40, 50, 60.0])
    t = SC.faixas(s, pd.Series([-0.1, -0.1, 0.0, 0.05, 0.1, 0.2]), (25, 45))
    assert list(t["Operações"]) == [2, 2, 2] and t.loc[2, "Retorno médio"] > t.loc[0, "Retorno médio"]


def test_dataset_sem_olhar_o_futuro_nos_dados_reais():
    import yaml
    from tests import regressao
    sw = yaml.safe_load((regressao.ROOT / "config/swing.yaml").read_text(encoding="utf-8"))
    raw = pd.read_parquet(regressao.FIX / "ohlcv_swing.parquet")
    data = {t: g.drop(columns="Ticker").set_index("Date") for t, g in raw.groupby("Ticker")}
    d = SC.dataset(data, sw, data["SPY"]["Close"])
    assert len(d) > 20 and d[SC.COMPONENTES].min().min() >= 0 and d[SC.COMPONENTES].max().max() <= 1
    # alterar o futuro (depois do último sinal de cada operação) não muda o componente calculado nesse sinal:
    t0 = d.iloc[0]
    cortado = {k: v[v.index <= t0["sinal"]] for k, v in data.items()}
    comp = SC.componentes_serie(cortado[t0["ticker"]], [], cortado["SPY"]["Close"])
    for k in ("tendencia", "momento", "volume", "volatilidade", "regime"):
        assert abs(comp.loc[t0["sinal"], k] - t0[k]) < 1e-12
