"""Score de qualidade do sinal (0–100) e sua validação fora da amostra.

O score só pode ser MOSTRADO se passar na validação (config/score.yaml → validacao.mostrar). Passos:
1. Cada operação do backtest recebe 7 componentes de 0 a 1, calculados SÓ com dados até o fechamento do sinal.
2. Calibração (entradas até 2019): peso de cada componente ∝ max(0, correlação de Spearman com o retorno da operação).
3. Teste (entradas de 2020 em diante, nunca vistas na calibração): retorno médio por faixa de score, correlação e
   p-valor por permutação. Mostrar o score exige correlação > 0, p < 0,05 e faixa alta melhor que a baixa.
Sem viés de olhar o futuro: o "histórico da regra" usa só operações JÁ ENCERRADAS antes do sinal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pwass.engine import indicators, swing

COMPONENTES = ["tendencia", "momento", "volume", "volatilidade", "confirmacao", "regime", "historico"]
ROTULOS = {"tendencia": "Tendência (preço vs MM200)", "momento": "Momento (retorno 63 dias)", "volume": "Volume relativo",
           "volatilidade": "Volatilidade baixa (ATR %)", "confirmacao": "Confirmação de outras estratégias",
           "regime": "Regime (SPY > MM200)", "historico": "Histórico da regra no ativo"}


def _clip01(s: pd.Series) -> pd.Series:
    return s.clip(0, 1)


def componentes_serie(df: pd.DataFrame, outras: list[pd.DataFrame], spy_close: pd.Series | None) -> pd.DataFrame:
    """Componentes de 0–1 para cada data de `df` (exceto 'historico', que depende das operações)."""
    c = df["Close"]
    out = pd.DataFrame(index=df.index)
    out["tendencia"] = _clip01((c / indicators.sma(c, 200) - 1) / 0.20)
    out["momento"] = _clip01((c.pct_change(63) + 0.10) / 0.30)
    out["volume"] = _clip01(df["Volume"] / df["Volume"].rolling(20).mean().shift(1) / 2)
    out["volatilidade"] = 1 - _clip01(swing.atr(df, 14) / c / 0.05)
    out["confirmacao"] = (sum((s["entry"] | s["near"]).astype(float) for s in outras) / len(outras)) if outras else 0.0
    out["regime"] = ((spy_close > indicators.sma(spy_close, 200)).astype(float).reindex(df.index).ffill()
                     if spy_close is not None else 0.5)
    return out


def _historico(trades: pd.DataFrame, i: int, data_sinal: pd.Timestamp, minimo: int = 5) -> float:
    """Profit factor das operações da MESMA regra/ativo encerradas antes do sinal → 0–1 (0,5 se poucas)."""
    prev = trades[trades["Saída"] < data_sinal]
    if len(prev) < minimo:
        return 0.5
    w, l = prev.loc[prev.Retorno > 0, "Retorno"].sum(), -prev.loc[prev.Retorno <= 0, "Retorno"].sum()
    pf = w / l if l > 0 else 3.0
    return float(np.clip((pf - 0.8) / 1.7, 0, 1))


def dataset(data: dict[str, pd.DataFrame], sw: dict, spy_close: pd.Series | None = None) -> pd.DataFrame:
    """Uma linha por operação do backtest: ticker, estrategia, sinal, retorno e os 7 componentes."""
    risk, rows = sw["risco"], []
    for t, df in data.items():
        if len(df) < 300:
            continue
        sigs = {sid: swing.signals(df, sid, p) for sid, p in sw["estrategias"].items()}
        for sid, p in sw["estrategias"].items():
            tr = swing.backtest(df, sid, p, risk["custo_por_lado"], risk["multiplo_atr_stop"]).trades
            if tr.empty:
                continue
            comp = componentes_serie(df, [s for k, s in sigs.items() if k != sid], spy_close)
            tr = tr.sort_values("Entrada").reset_index(drop=True)
            for i, r in tr.iterrows():
                pos = df.index.get_loc(r["Entrada"]) - 1          # barra do sinal (fechamento anterior à entrada)
                if pos < 0:
                    continue
                d_sinal = df.index[pos]
                row = comp.iloc[pos].to_dict()
                row["historico"] = _historico(tr.iloc[:i], i, d_sinal)
                rows.append({"ticker": t, "estrategia": sid, "sinal": d_sinal, "retorno": float(r["Retorno"]), **row})
    d = pd.DataFrame(rows)
    return d.dropna(subset=COMPONENTES).reset_index(drop=True) if len(d) else d


def calibrar(treino: pd.DataFrame) -> dict[str, float]:
    """Pesos ∝ max(0, Spearman(componente, retorno)) no treino; soma 1. Tudo zero → {} (sem score)."""
    raw = {k: max(0.0, float(treino[k].rank().corr(treino["retorno"].rank()))) for k in COMPONENTES}
    raw = {k: (0.0 if np.isnan(v) else v) for k, v in raw.items()}
    tot = sum(raw.values())
    return {k: v / tot for k, v in raw.items()} if tot > 0 else {}


def pontuar(comp: pd.DataFrame | pd.Series, pesos: dict[str, float]):
    """Score 0–100 = 100 × Σ peso × componente."""
    return 100 * sum(pesos.get(k, 0.0) * comp[k] for k in COMPONENTES)


def _spearman_perm(score: np.ndarray, ret: np.ndarray, n_perm: int = 2000, seed: int = 7) -> tuple[float, float]:
    rs, rr = pd.Series(score).rank().to_numpy(), pd.Series(ret).rank().to_numpy()
    rho = float(np.corrcoef(rs, rr)[0, 1])
    rng = np.random.default_rng(seed)
    perm = np.array([np.corrcoef(rs, rng.permutation(rr))[0, 1] for _ in range(n_perm)])
    return rho, float((np.sum(perm >= rho) + 1) / (n_perm + 1))        # p unilateral (H1: correlação > 0)


def faixas(score: pd.Series, retorno: pd.Series, cortes: tuple[float, float]) -> pd.DataFrame:
    """Tabela por faixa (baixa/média/alta): operações, acerto, retorno médio, profit factor."""
    lab = pd.cut(score, [-np.inf, cortes[0], cortes[1], np.inf], labels=["Baixa", "Média", "Alta"])
    rows = []
    for f in ["Baixa", "Média", "Alta"]:
        r = retorno[lab == f]
        w, l = r[r > 0].sum(), -r[r <= 0].sum()
        rows.append({"Faixa": f, "Operações": len(r), "Taxa de acerto": float((r > 0).mean()) if len(r) else np.nan,
                     "Retorno médio": float(r.mean()) if len(r) else np.nan,
                     "Profit factor": float(w / l) if l > 0 else np.nan})
    return pd.DataFrame(rows)


def validar(ds: pd.DataFrame, corte: str = "2020-01-01", min_faixa: int = 30) -> dict:
    """Calibra no treino e avalia no teste. Retorna pesos, tabelas, métricas e a decisão `mostrar` com os motivos."""
    corte = pd.Timestamp(corte)
    treino, teste = ds[ds["sinal"] < corte], ds[ds["sinal"] >= corte]
    res = {"n_treino": len(treino), "n_teste": len(teste), "corte": str(corte.date()), "pesos": {}, "mostrar": False, "motivos": []}
    if len(treino) < 100 or len(teste) < 100:
        res["motivos"].append(f"amostra pequena (treino {len(treino)}, teste {len(teste)}; mínimo 100 em cada)")
        return res
    pesos = calibrar(treino)
    res["pesos"] = pesos
    if not pesos:
        res["motivos"].append("nenhum componente teve correlação positiva com o retorno no treino")
        return res
    s_tr, s_te = pontuar(treino, pesos), pontuar(teste, pesos)
    cortes = (float(s_tr.quantile(1 / 3)), float(s_tr.quantile(2 / 3)))      # faixas definidas SÓ no treino
    res["cortes"] = cortes
    res["tabela_treino"], res["tabela_teste"] = faixas(s_tr, treino["retorno"], cortes), faixas(s_te, teste["retorno"], cortes)
    res["rho_treino"], _ = _spearman_perm(s_tr.to_numpy(), treino["retorno"].to_numpy(), 200)
    res["rho_teste"], res["p_teste"] = _spearman_perm(s_te.to_numpy(), teste["retorno"].to_numpy())
    t = res["tabela_teste"].set_index("Faixa")
    ok = True
    if not res["rho_teste"] > 0:
        ok = False; res["motivos"].append(f"correlação fora da amostra não é positiva ({res['rho_teste']:+.3f})")
    if not res["p_teste"] < 0.05:
        ok = False; res["motivos"].append(f"correlação fora da amostra não é significativa (p = {res['p_teste']:.3f})")
    if t.loc["Alta", "Operações"] < min_faixa or t.loc["Baixa", "Operações"] < min_faixa:
        ok = False; res["motivos"].append(f"faixas com menos de {min_faixa} operações no teste")
    elif not t.loc["Alta", "Retorno médio"] > t.loc["Baixa", "Retorno médio"]:
        ok = False; res["motivos"].append("faixa alta não rendeu mais que a baixa no teste")
    res["mostrar"] = ok
    if ok:
        res["motivos"].append("passou nos quatro critérios fora da amostra")
    return res
