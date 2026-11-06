"""Laboratório de Swing Trade: três estratégias mecânicas com backtest honesto.

Regras de execução (iguais no backtest e no sinal de hoje):
- O sinal é calculado no FECHAMENTO do dia t.
- A ordem é executada na ABERTURA do dia t+1 (nada de olhar o futuro).
- Custos de 0,10% por lado (configurável em config/swing.yaml).
- Só candles diários.

Estratégias:
1. pullback   — Connors RSI(2): preço > MM200 e RSI(2) < 10; sai quando fecha acima da MM5.
2. cruzamento — EMA20 cruza acima da EMA50 com preço > MM200; sai no cruzamento para baixo.
3. rompimento — fecha acima da máxima de 55 dias com volume > 1,5× a média de 20 dias;
                stop de 2×ATR; sai ao fechar abaixo da mínima de 20 dias (Tartarugas).

Gestão de risco (ATR + risco fixo): quantidade = capital × 1% ÷ (2 × ATR14).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from pwass.engine import indicators

COMPRA, SAIR, POSICAO, PERTO, AGUARDAR, EVITAR = (
    "COMPRA", "SAIR", "EM POSIÇÃO", "PERTO DO GATILHO", "AGUARDAR", "EVITAR")


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range de Wilder."""
    prev = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def periods_per_year(idx: pd.DatetimeIndex) -> int:
    return 365 if (idx[-200:].dayofweek >= 5).mean() > 0.1 else 252


# ------------------------------------------------------------------ sinais
def signals(df: pd.DataFrame, sid: str, p: dict) -> pd.DataFrame:
    """Colunas booleanas avaliadas no fechamento: entry, exit, near, trend; e níveis úteis."""
    c = df["Close"]
    out = pd.DataFrame(index=df.index)
    sma_t = indicators.sma(c, p.get("mm_tendencia", 200))
    out["trend"] = c > sma_t
    out["atr"] = atr(df, 14)
    if sid == "pullback":
        r = indicators.rsi(c, p["rsi_periodo"])
        sma_exit = indicators.sma(c, p["mm_saida"])
        out["rsi"] = r
        out["exit_level"] = sma_exit
        out["entry"] = out["trend"] & (r < p["rsi_entrada"])
        out["exit"] = c > sma_exit
        out["near"] = out["trend"] & (r < p["rsi_perto"]) & ~out["entry"]
    elif sid == "cruzamento":
        f, s = ema(c, p["rapida"]), ema(c, p["lenta"])
        up = f > s
        out["fast"], out["slow"] = f, s
        out["entry"] = up & ~up.shift(1, fill_value=True) & out["trend"]
        out["exit"] = ~up & up.shift(1, fill_value=False)
        out["near"] = out["trend"] & ~up & (f / s > 0.99)
        out["exit_level"] = s
    elif sid == "rompimento":
        hh = df["High"].rolling(p["canal_entrada"]).max().shift(1)
        ll = df["Low"].rolling(p["canal_saida"]).min().shift(1)
        vol = df["Volume"]
        vol_ok = vol > p["volume_minimo"] * vol.rolling(20).mean()
        out["hh"], out["exit_level"] = hh, ll
        out["entry"] = (c > hh) & vol_ok
        out["exit"] = c < ll
        out["near"] = (c >= 0.97 * hh) & ~out["entry"]
    else:
        raise ValueError(f"Estratégia desconhecida: {sid}")
    return out


# ------------------------------------------------------------------ backtest
@dataclass
class Backtest:
    trades: pd.DataFrame        # uma linha por operação
    daily: pd.Series            # retorno diário da estratégia
    bh: pd.Series               # retorno diário do buy & hold no mesmo período
    open_trade: dict | None     # operação ainda aberta no último dia


def backtest(df: pd.DataFrame, sid: str, p: dict, cost: float = 0.001, atr_mult: float = 2.0) -> Backtest:
    sig = signals(df, sid, p)
    o, h, lo, c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    entry, exit_, atr_v = sig["entry"].to_numpy(), sig["exit"].to_numpy(), sig["atr"].to_numpy()
    use_stop = sid == "rompimento"
    n = len(df)
    daily = np.zeros(n)
    trades = []
    pos = False
    e_i = e_px = stop = 0.0
    start = int(np.argmax(~np.isnan(sig["atr"].to_numpy()))) + 1
    for i in range(max(start, 1), n):
        if not pos:
            if entry[i - 1] and not np.isnan(o[i]):
                pos, e_i, e_px = True, i, o[i]
                stop = o[i] - atr_mult * atr_v[i - 1] if use_stop else -np.inf
                if use_stop and lo[i] <= stop:  # stop no mesmo dia
                    px = stop
                    daily[i] = (px * (1 - cost)) / (e_px * (1 + cost)) - 1
                    trades.append((df.index[i], e_px, df.index[i], px, 1))
                    pos = False
                    continue
                daily[i] = c[i] / (e_px * (1 + cost)) - 1
            continue
        # em posição
        if exit_[i - 1]:
            px = o[i]
            daily[i] = px * (1 - cost) / c[i - 1] - 1
            trades.append((df.index[e_i], e_px, df.index[i], px, i - e_i))
            pos = False
            continue
        if use_stop and lo[i] <= stop:
            px = min(o[i], stop)
            daily[i] = px * (1 - cost) / c[i - 1] - 1
            trades.append((df.index[e_i], e_px, df.index[i], px, i - e_i))
            pos = False
            continue
        daily[i] = c[i] / c[i - 1] - 1
    tr = pd.DataFrame(trades, columns=["Entrada", "Preço entrada", "Saída", "Preço saída", "Dias"])
    if not tr.empty:
        tr["Retorno"] = tr["Preço saída"] * (1 - cost) / (tr["Preço entrada"] * (1 + cost)) - 1
    open_trade = None
    if pos:
        open_trade = {"entrada": df.index[e_i], "preco_entrada": e_px, "dias": n - 1 - e_i,
                      "resultado": c[-1] / e_px - 1, "stop": stop if use_stop else None}
    idx = df.index
    first = idx[start] if start < n else idx[0]
    d = pd.Series(daily, index=idx)[first:]
    bh = df["Close"].pct_change()[first:].fillna(0)
    return Backtest(tr, d, bh, open_trade)


def _cagr(r: pd.Series, ppy: int) -> float:
    years = len(r) / ppy
    eq = float((1 + r).prod())
    return eq ** (1 / years) - 1 if years > 0 and eq > 0 else math.nan


def _maxdd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def stats(bt: Backtest, ppy: int = 252) -> dict:
    t = bt.trades
    wins = t.loc[t["Retorno"] > 0, "Retorno"] if not t.empty else pd.Series(dtype=float)
    losses = t.loc[t["Retorno"] <= 0, "Retorno"] if not t.empty else pd.Series(dtype=float)
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else (math.inf if len(wins) else math.nan)
    d = bt.daily
    return {
        "Operações": len(t),
        "Taxa de acerto": len(wins) / len(t) if len(t) else math.nan,
        "Ganho médio": wins.mean() if len(wins) else math.nan,
        "Perda média": losses.mean() if len(losses) else math.nan,
        "Profit factor": pf,
        "Resultado médio": t["Retorno"].mean() if len(t) else math.nan,
        "Dias médios": t["Dias"].mean() if len(t) else math.nan,
        "Tempo posicionado": float((d != 0).mean()) if len(d) else math.nan,
        "CAGR estratégia": _cagr(d, ppy),
        "CAGR buy & hold": _cagr(bt.bh, ppy),
        "Máx. queda estratégia": _maxdd(d),
        "Máx. queda buy & hold": _maxdd(bt.bh),
        "Anos": len(d) / ppy,
    }


def pooled(bts: list[Backtest]) -> dict:
    """Estatísticas somando as operações de todos os ativos."""
    t = pd.concat([b.trades for b in bts if not b.trades.empty], ignore_index=True) if bts else pd.DataFrame()
    if t.empty:
        return {"Operações": 0}
    w, l = t[t["Retorno"] > 0]["Retorno"], t[t["Retorno"] <= 0]["Retorno"]
    return {"Operações": len(t), "Taxa de acerto": len(w) / len(t),
            "Profit factor": w.sum() / abs(l.sum()) if l.sum() != 0 else math.inf,
            "Resultado médio": t["Retorno"].mean(), "Ganho médio": w.mean(), "Perda média": l.mean(),
            "Dias médios": t["Dias"].mean()}


# ------------------------------------------------------------------ situação de hoje
def plan(df: pd.DataFrame, risk: dict) -> dict:
    """Plano da operação pela regra de risco: stop por ATR, alvos em R e tamanho da posição."""
    price = float(df["Close"].iloc[-1])
    a = float(atr(df, 14).iloc[-1])
    r = risk["multiplo_atr_stop"] * a
    cap = risk["capital_laboratorio_usd"]
    qty = cap * risk["risco_por_operacao"] / r if r > 0 else 0
    qty = min(qty, cap * risk["posicao_maxima"] / price)
    t1, t2 = (price + m * r for m in risk["alvos_em_r"])
    return {"entrada": price, "stop": price - r, "alvo1": t1, "alvo2": t2, "R": r, "atr": a,
            "quantidade": qty, "valor": qty * price, "risco_usd": qty * r,
            "risco_pct_preco": r / price}


def status_today(df: pd.DataFrame, sid: str, p: dict, bt: Backtest) -> tuple[str, str]:
    sig = signals(df, sid, p).iloc[-1]
    if bt.open_trade:
        ot = bt.open_trade
        if sig["exit"]:
            return SAIR, f"Regra de saída acionada hoje: vender na abertura ({ot['resultado']:+.1%} na operação)."
        lvl = sig.get("exit_level")
        extra = f"; saída se fechar {'acima' if sid == 'pullback' else 'abaixo'} de {lvl:,.2f}" if pd.notna(lvl) else ""
        return POSICAO, f"Comprado há {ot['dias']} dias, {ot['resultado']:+.1%}{extra}."
    if sig["entry"]:
        return COMPRA, "Setup completo no fechamento de hoje: entrada na abertura do próximo pregão."
    if sig["near"]:
        return PERTO, "Quase lá: falta pouco para os critérios de entrada."
    if sig["trend"]:
        return AGUARDAR, "Tendência de alta, mas sem gatilho hoje."
    return EVITAR, "Abaixo da MM200: fora do filtro de tendência."


def scan(data: dict[str, pd.DataFrame], names: dict[str, tuple[str, str]], sid: str, p: dict,
         risk: dict) -> tuple[pd.DataFrame, dict[str, Backtest]]:
    """Roda a estratégia em todo o universo: situação de hoje + estatística histórica por ativo."""
    rows, bts = [], {}
    for t, df in data.items():
        if len(df) < 260:
            continue
        bt = backtest(df, sid, p, risk["custo_por_lado"], risk["multiplo_atr_stop"])
        bts[t] = bt
        st_ = stats(bt, periods_per_year(df.index))
        status, detail = status_today(df, sid, p, bt)
        last, prev = df["Close"].iloc[-1], df["Close"].iloc[-2]
        name, group = names.get(t, (t, ""))
        rows.append({"Ticker": t, "Ativo": name, "Classe": group, "Último": float(last),
                     "Histórico": quality(st_),
                     "Dia": float(last / prev - 1), "Situação": status, "Detalhe": detail,
                     "Operações": st_["Operações"], "Acerto": st_["Taxa de acerto"],
                     "Profit factor": st_["Profit factor"], "Resultado médio": st_["Resultado médio"],
                     "CAGR": st_["CAGR estratégia"], "CAGR B&H": st_["CAGR buy & hold"],
                     "Máx. queda": st_["Máx. queda estratégia"]})
    order = {COMPRA: 0, SAIR: 1, POSICAO: 2, PERTO: 3, AGUARDAR: 4, EVITAR: 5}
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out = df_out.assign(_o=df_out["Situação"].map(order)).sort_values(
            ["_o", "Profit factor"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)
    return df_out, bts


def quality(s: dict) -> str:
    """Qualidade do histórico da regra NAQUELE ativo: decide se o sinal merece confiança."""
    n, pf = s.get("Operações", 0), s.get("Profit factor", math.nan)
    if n < 8 or pf is None or (isinstance(pf, float) and math.isnan(pf)):
        return "Pouco histórico"
    if pf >= 1.5 and s.get("Resultado médio", 0) > 0:
        return "Bom"
    if pf >= 1.1:
        return "Regular"
    return "Fraco"


QUALITY_RANK = {"Bom": 0, "Regular": 1, "Pouco histórico": 2, "Fraco": 3}


def best_setup(table: pd.DataFrame) -> pd.Series | None:
    """Melhor setup de hoje: COMPRA com o melhor histórico da regra naquele ativo."""
    c = table[table["Situação"] == COMPRA]
    if c.empty:
        return None
    c = c.assign(_q=c["Histórico"].map(QUALITY_RANK))
    return c.sort_values(["_q", "Resultado médio"], ascending=[True, False]).drop(columns="_q").iloc[0]
