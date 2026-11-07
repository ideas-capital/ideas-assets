"""Regras de alerta avaliadas sobre candles diários (funções puras, sem rede).

Um alerta é um dict: {"id", "ticker", "tipo", "params": {...}, "ativo": bool, "nome"?}.
`avaliar(alerta, df, sw)` devolve {"disparou": bool, "mensagem": str, "valor": float|None} avaliando o
ÚLTIMO fechamento (nunca o futuro). Dado insuficiente → disparou False com motivo (não estima).

Tipos e parâmetros:
- preco:       {"direcao": "acima"|"abaixo", "valor": 200.0}
- variacao:    {"limite_pct": 5.0, "direcao": "alta"|"queda"|"qualquer"}   (variação do último pregão)
- rsi:         {"direcao": "acima"|"abaixo", "valor": 70, "periodo": 14}
- cruzamento:  {"media": 50|200, "sentido": "acima"|"abaixo"}   (o fechamento cruzou a média NESTE pregão)
- rompimento:  {"dias": 55, "lado": "maxima"|"minima"}   (fecha acima da máxima / abaixo da mínima dos N dias anteriores)
- volume:      {"multiplo": 2.0}   (volume de hoje ≥ múltiplo × média das 20 sessões anteriores)
- sinal:       {"estrategia": "pullback", "situacao": "COMPRA"|"PERTO"|"SAIR"}   (regra do Laboratório, config/swing.yaml)
"""
from __future__ import annotations

import pandas as pd

from pwass.engine import indicators, swing

TIPOS = {"preco": "Preço", "variacao": "Variação no dia", "rsi": "RSI", "cruzamento": "Cruzamento de média",
         "rompimento": "Rompimento de canal", "volume": "Volume anormal", "sinal": "Sinal de estratégia"}


def _res(disparou: bool, msg: str, valor=None) -> dict:
    return {"disparou": bool(disparou), "mensagem": msg, "valor": None if valor is None else float(valor)}


def avaliar(a: dict, df: pd.DataFrame, sw: dict | None = None) -> dict:
    t, p, tk = a["tipo"], a.get("params", {}), a["ticker"]
    if df is None or len(df) < 3:
        return _res(False, f"{tk}: sem dados suficientes")
    c = df["Close"]
    last = float(c.iloc[-1])
    if t == "preco":
        v = float(p["valor"])
        ok = last >= v if p["direcao"] == "acima" else last <= v
        return _res(ok, f"{tk} fechou em {last:,.2f}, {p['direcao']} de {v:,.2f}", last)
    if t == "variacao":
        d = last / float(c.iloc[-2]) - 1
        lim = float(p["limite_pct"]) / 100
        ok = {"alta": d >= lim, "queda": d <= -lim, "qualquer": abs(d) >= lim}[p.get("direcao", "qualquer")]
        return _res(ok, f"{tk} variou {d * 100:+.1f}% no último pregão (limite {p['limite_pct']:g}%)", d)
    if t == "rsi":
        per = int(p.get("periodo", 14))
        if len(c) <= per + 1:
            return _res(False, f"{tk}: histórico curto para RSI {per}")
        r = float(indicators.rsi(c, per).iloc[-1])
        ok = r >= p["valor"] if p["direcao"] == "acima" else r <= p["valor"]
        return _res(ok, f"RSI {per} de {tk} em {r:.0f} ({p['direcao']} de {p['valor']:g})", r)
    if t == "cruzamento":
        n = int(p["media"])
        if len(c) <= n + 1:
            return _res(False, f"{tk}: histórico curto para MM{n}")
        m = indicators.sma(c, n)
        hoje, ontem = c.iloc[-1] > m.iloc[-1], c.iloc[-2] > m.iloc[-2]
        ok = (hoje and not ontem) if p["sentido"] == "acima" else ((not hoje) and ontem)
        return _res(ok, f"{tk} {'cruzou' if ok else 'não cruzou'} a MM{n} para {p['sentido']} neste pregão", last)
    if t == "rompimento":
        n = int(p["dias"])
        if len(df) <= n + 1:
            return _res(False, f"{tk}: histórico curto para canal de {n} dias")
        if p["lado"] == "maxima":
            ref = float(df["High"].iloc[-n - 1:-1].max())
            ok = last > ref
        else:
            ref = float(df["Low"].iloc[-n - 1:-1].min())
            ok = last < ref
        return _res(ok, f"{tk} fechou em {last:,.2f}; {'máxima' if p['lado'] == 'maxima' else 'mínima'} de {n} dias: {ref:,.2f}", last)
    if t == "volume":
        if len(df) < 22:
            return _res(False, f"{tk}: histórico curto para média de volume")
        media = float(df["Volume"].iloc[-21:-1].mean())
        if not media:
            return _res(False, f"{tk}: volume médio indisponível")
        r = float(df["Volume"].iloc[-1]) / media
        return _res(r >= p["multiplo"], f"Volume de {tk} em {r:.1f}× a média de 20 sessões (limite {p['multiplo']:g}×)", r)
    if t == "sinal":
        if not sw or p["estrategia"] not in sw["estrategias"]:
            return _res(False, f"{tk}: estratégia desconhecida")
        if len(df) < 260:
            return _res(False, f"{tk}: histórico curto para a regra")
        sg = swing.signals(df, p["estrategia"], sw["estrategias"][p["estrategia"]]).iloc[-1]
        flag = {"COMPRA": "entry", "PERTO": "near", "SAIR": "exit"}[p["situacao"]]
        return _res(bool(sg[flag]), f"{tk}: {sw['estrategias'][p['estrategia']]['curto']} — {p['situacao']} "
                                    f"{'acionado' if sg[flag] else 'não acionado'} no último fechamento", last)
    raise ValueError(f"tipo de alerta desconhecido: {t}")


def avaliar_todos(alertas: list[dict], dados: dict[str, pd.DataFrame], sw: dict | None = None) -> list[dict]:
    """Avalia só os alertas ativos; devolve os disparados (cada um com o alerta original em 'alerta')."""
    out = []
    for a in alertas:
        if not a.get("ativo", True):
            continue
        try:
            r = avaliar(a, dados.get(a["ticker"]), sw)
        except Exception as e:  # noqa: BLE001 — um alerta quebrado não derruba os outros
            r = _res(False, f"{a.get('ticker')}: erro ao avaliar ({e})")
        if r["disparou"]:
            out.append({**r, "alerta": a})
    return out


def descrever(a: dict) -> str:
    """Condição do alerta em português (para listas na tela)."""
    p, t = a.get("params", {}), a["tipo"]
    if t == "preco":
        return f"Preço {p['direcao']} de {p['valor']:g}"
    if t == "variacao":
        return f"Variação no dia: {p.get('direcao', 'qualquer')} ≥ {p['limite_pct']:g}%"
    if t == "rsi":
        return f"RSI({p.get('periodo', 14)}) {p['direcao']} de {p['valor']:g}"
    if t == "cruzamento":
        return f"Preço cruza a MM{p['media']} para {p['sentido']}"
    if t == "rompimento":
        return f"Fecha {'acima da máxima' if p['lado'] == 'maxima' else 'abaixo da mínima'} de {p['dias']} dias"
    if t == "volume":
        return f"Volume ≥ {p['multiplo']:g}× a média de 20 sessões"
    if t == "sinal":
        return f"Estratégia {p['estrategia']}: {p['situacao']}"
    return t
