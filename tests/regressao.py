"""Números de regressão do redesign v5: calcula swing e carteiras sobre fixtures reais gravadas.

`python -m tests.regressao` regrava tests/fixtures/golden.json (só fazer ao mudar uma regra DE PROPÓSITO,
com justificativa). `tests/test_regressao.py` compara o cálculo atual com o arquivo.
"""
from __future__ import annotations

import json
import math
import pathlib

import pandas as pd
import yaml

from pwass.engine import backtest as B, strategies as ST, swing as S

FIX = pathlib.Path(__file__).parent / "fixtures"
ROOT = FIX.parents[1]


def _r(x, d=9):
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return x
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), d)


def compute() -> dict:
    sw = yaml.safe_load((ROOT / "config/swing.yaml").read_text(encoding="utf-8"))
    risk = sw["risco"]
    raw = pd.read_parquet(FIX / "ohlcv_swing.parquet")
    data = {t: g.drop(columns="Ticker").set_index("Date") for t, g in raw.groupby("Ticker")}
    out: dict = {"swing": {}, "carteiras": {}}
    for sid, p in sw["estrategias"].items():
        for tk, df in data.items():
            bt = S.backtest(df, sid, p, risk["custo_por_lado"], risk["multiplo_atr_stop"])
            st = S.stats(bt, S.periods_per_year(df.index))
            out["swing"][f"{sid}/{tk}"] = {
                "stats": {k: _r(v) for k, v in st.items()},
                "n_trades": len(bt.trades),
                "soma_retornos": _r(bt.trades["Retorno"].sum()) if len(bt.trades) else 0.0,
                "equity_final": _r((1 + bt.daily).prod()),
                "status_hoje": list(S.status_today(df, sid, p, bt)),
                "plano": {k: _r(v) for k, v in S.plan(df, risk).items()},
            }
    px = pd.read_parquet(FIX / "precos_carteiras.parquet")
    m = ST.monthly(px)
    for nome, w in (("gem", ST.gem_weights(m)), ("gtaa", ST.gtaa_weights(m))):
        r = B.run(w, m)
        out["carteiras"][nome] = {"n_meses": len(r), "equity_final": _r(B.equity(r).iloc[-1]),
                                  "metricas": {k: _r(v) for k, v in B.metrics(r).items()}}
    return out


if __name__ == "__main__":
    (FIX / "golden.json").write_text(json.dumps(compute(), indent=1, sort_keys=True, ensure_ascii=False))
    print("golden.json regravado")
