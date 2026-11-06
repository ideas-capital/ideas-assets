"""Semáforo de prudência: uma leitura simples e honesta de cada ativo.

Não diz "compre" ou "venda". Diz em que situação o ativo está e qual postura
costuma ser prudente nessa situação, usando regras clássicas e verificáveis:

- Tendência: preço vs média de 200 dias e a inclinação dessa média (Faber 2007).
- Esticamento: distância da média e RSI — perseguir alta esticada é o erro
  mais comum do investidor pessoa física.
- Risco: volatilidade dos últimos 3 meses vs a dos últimos 3 anos e queda
  desde o topo de 12 meses.
- Juros: nível atual comparado com a própria história (percentil).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from pwass.engine import indicators

VERDE, AZUL, AMARELO, VERMELHO = "verde", "azul", "amarelo", "vermelho"

POSTURA = {
    "Alta saudável": (VERDE, "Manter; aportes regulares dentro dos limites."),
    "Esticado": (AMARELO, "Não perseguir. Se passou do limite da carteira, rebalancear."),
    "Recuperando": (AZUL, "Tendência ainda não confirmada: aportar só em parcelas."),
    "Correção": (AZUL, "Queda dentro de tendência de alta: só aportes parcelados (DCA)."),
    "Tendência de baixa": (VERMELHO, "Não aumentar posição; esperar voltar acima da MM200."),
}


def _periods_per_year(s: pd.Series) -> int:
    """Cripto negocia todos os dias (365); bolsa ~252 pregões."""
    if len(s) < 30:
        return 252
    weekend = (s.index[-120:].dayofweek >= 5).mean()
    return 365 if weekend > 0.1 else 252


def price_health(close: pd.Series, stretch: float = 0.25, rsi_hot: float = 75) -> dict:
    """Leitura de um ativo com preço (ação, ETF, cripto). Precisa de ~1 ano de dados."""
    s = close.dropna()
    ppy = _periods_per_year(s)
    last = float(s.iloc[-1])
    sma200 = indicators.sma(s, 200)
    m, m_prev = float(sma200.iloc[-1]), float(sma200.iloc[-22]) if len(s) > 222 else math.nan
    rising = m > m_prev if not math.isnan(m_prev) else False
    dist = last / m - 1
    rsi = float(indicators.rsi(s).iloc[-1])
    rets = np.log(s).diff().dropna()
    vol3m = float(rets.iloc[-63:].std() * math.sqrt(ppy))
    vol3y = float(rets.iloc[-3 * ppy:].std() * math.sqrt(ppy))
    dd = last / float(s.iloc[-ppy:].max()) - 1
    end = s.index[-1]
    past = s[s.index <= end - pd.DateOffset(years=1)]
    ret12 = last / float(past.iloc[-1]) - 1 if len(past) else math.nan
    past1 = s[s.index <= end - pd.DateOffset(months=1)]
    ret1 = last / float(past1.iloc[-1]) - 1 if len(past1) else math.nan

    # Alta saudável exige os dois filtros clássicos: preço acima da MM200 subindo (Faber)
    # E retorno de 12 meses positivo (momento absoluto, Antonacci).
    if last > m and (dist > stretch or rsi >= rsi_hot):
        status = "Esticado"
    elif last > m:
        status = "Alta saudável" if rising and not (ret12 <= 0) else "Recuperando"
    else:
        status = "Correção" if rising else "Tendência de baixa"
    cor, postura = POSTURA[status]

    motivos = [f"{dist:+.0%} vs MM200 ({'subindo' if rising else 'caindo'})", f"RSI {rsi:.0f}"]
    if last > m and not (ret12 > 0):
        motivos.append("retorno de 12 meses negativo")
    if vol3y > 0 and vol3m > 1.5 * vol3y:
        motivos.append("volatilidade bem acima do normal")
    if dd < -0.25:
        motivos.append(f"{dd:.0%} desde o topo de 12m")
    return {"preco": last, "ret_1m": ret1, "ret_12m": ret12, "dist_mm200": dist, "mm200_subindo": rising,
            "rsi": rsi, "vol_3m": vol3m, "vol_3a": vol3y, "queda_topo": dd, "mayer": last / m,
            "status": status, "cor": cor, "postura": postura, "motivos": "; ".join(motivos)}


def percentile(s: pd.Series, value: float | None = None) -> float:
    """Em que percentil (0–100) da própria história está o valor atual."""
    s = s.dropna()
    v = s.iloc[-1] if value is None else value
    return float((s <= v).mean() * 100)


def reading_rate(value: float, pct: float, high_good: bool = True,
                 hi: str = "historicamente alto", lo: str = "historicamente baixo") -> tuple[str, str]:
    """Traduz um percentil em leitura e cor. high_good=True: taxa alta favorece quem compra o título."""
    if pct >= 80:
        return hi, VERDE if high_good else VERMELHO
    if pct <= 20:
        return lo, VERMELHO if high_good else VERDE
    return "na média histórica", AZUL


def real_rate(nominal_pct: float, inflation_pct: float) -> float:
    """Juro real pela fórmula de Fisher: (1 + nominal) / (1 + inflação) − 1, em %."""
    return ((1 + nominal_pct / 100) / (1 + inflation_pct / 100) - 1) * 100


def fx_breakeven(cdi_pct: float, tbill_pct: float, tax_br: float = 0.15, tax_us: float = 0.15) -> float:
    """Quanto o dólar precisa subir por ano para o T-Bill empatar com o CDI, líquido de IR (%)."""
    return ((1 + cdi_pct / 100 * (1 - tax_br)) / (1 + tbill_pct / 100 * (1 - tax_us)) - 1) * 100
