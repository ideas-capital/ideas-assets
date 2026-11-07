"""Status de pregão (aberto/fechado) da NYSE e da B3, calculado por calendário e horário.

Sem rede. Feriados por regra fixa (NYSE: 10 feriados + regra de "observado"; B3: nacionais e
Carnaval/Corpus Christi derivados da Páscoa). Antecipações de véspera (meio-expediente) e feriados
extraordinários NÃO são cobertos — o rótulo na UI cita isso.

Exemplo:
    >>> import datetime as dt
    >>> from zoneinfo import ZoneInfo
    >>> status_nyse(dt.datetime(2026, 11, 6, 11, 0, tzinfo=ZoneInfo("America/New_York")))
    (True, 'aberto')
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from dateutil.easter import easter

NY, SP = ZoneInfo("America/New_York"), ZoneInfo("America/Sao_Paulo")


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    return d


def _last_weekday(year: int, month: int, weekday: int) -> dt.date:
    d = (dt.date(year + (month == 12), month % 12 + 1, 1)) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: dt.date) -> dt.date | None:
    """Sábado → sexta; domingo → segunda. (Ano-Novo em sábado não é compensado pela NYSE.)"""
    return d - dt.timedelta(days=1) if d.weekday() == 5 else d + dt.timedelta(days=1) if d.weekday() == 6 else d


def feriados_nyse(year: int) -> set[dt.date]:
    h = {_nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3), easter(year) - dt.timedelta(days=2),
         _last_weekday(year, 5, 0), _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 11, 3, 4)}
    ny = dt.date(year, 1, 1)
    if ny.weekday() != 5:
        h.add(_observed(ny))
    for m, d in ((6, 19), (7, 4), (12, 25)):
        h.add(_observed(dt.date(year, m, d)))
    return h


def feriados_b3(year: int) -> set[dt.date]:
    p = easter(year)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (11, 20), (12, 24), (12, 25), (12, 31)]
    return {dt.date(year, m, d) for m, d in fixos} | {p - dt.timedelta(days=48), p - dt.timedelta(days=47),
                                                       p - dt.timedelta(days=2), p + dt.timedelta(days=60)}


def _status(now: dt.datetime, tz: ZoneInfo, abre: dt.time, fecha: dt.time, feriados) -> tuple[bool, str]:
    t = now.astimezone(tz)
    if t.weekday() >= 5:
        return False, "fechado (fim de semana)"
    if t.date() in feriados(t.year):
        return False, "fechado (feriado)"
    if abre <= t.time() < fecha:
        return True, "aberto"
    return False, "fechado" if t.time() >= fecha else "fechado (abre às %s)" % abre.strftime("%H:%M")


def status_nyse(now: dt.datetime) -> tuple[bool, str]:
    return _status(now, NY, dt.time(9, 30), dt.time(16, 0), feriados_nyse)


def status_b3(now: dt.datetime) -> tuple[bool, str]:
    return _status(now, SP, dt.time(10, 0), dt.time(17, 0), feriados_b3)


# ------------------------------------------------------------------ inteligência de mercado (Painel)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pwass.engine import indicators  # noqa: E402


def amplitude(data: dict[str, pd.DataFrame], janela: int = 200) -> dict:
    """% dos ativos do universo com fechamento acima da média de `janela` dias (ignora quem tem histórico curto).

    >>> amplitude({"A": df_alta, "B": df_baixa})["pct"]  # fração 0–1
    """
    acima = [bool(d["Close"].iloc[-1] > indicators.sma(d["Close"], janela).iloc[-1])
             for d in data.values() if len(d) > janela]
    n = len(acima)
    return {"pct": (sum(acima) / n) if n else float("nan"), "acima": sum(acima), "n": n}


def tendencia_predominante(pct_acima: float) -> str:
    """Rótulo pela amplitude: ≥60% alta · 40–60% mista · <40% baixa. NaN → 'indisponível'."""
    if pct_acima != pct_acima:
        return "indisponível"
    return "alta" if pct_acima >= 0.6 else "mista" if pct_acima >= 0.4 else "baixa"


def percentil(serie: pd.Series, janela: int = 504) -> float:
    """Posição (0–1) do último valor dentro dos últimos `janela` pontos (ex.: VIX em 2 anos)."""
    s = serie.dropna().iloc[-janela:]
    return float((s <= s.iloc[-1]).mean()) if len(s) else float("nan")


def novidades(data: dict[str, pd.DataFrame], sinais: dict[str, pd.DataFrame], nomes: dict[str, str]) -> dict[str, list[str]]:
    """O que mudou no último pregão, por regra determinística.

    `sinais` = {ticker: swing.signals(df, ...)}. Retorna listas de tickers:
    novos_setups (entrada hoje e não ontem), cruzou_mm200_acima / cruzou_mm200_abaixo.
    """
    out: dict[str, list[str]] = {"novos_setups": [], "cruzou_mm200_acima": [], "cruzou_mm200_abaixo": []}
    for t, sg in sinais.items():
        if len(sg) > 2 and bool(sg["entry"].iloc[-1]) and not bool(sg["entry"].iloc[-2]):
            out["novos_setups"].append(t)
    for t, d in data.items():
        if len(d) <= 201:
            continue
        c = d["Close"]
        m = indicators.sma(c, 200)
        hoje, ontem = c.iloc[-1] > m.iloc[-1], c.iloc[-2] > m.iloc[-2]
        if hoje and not ontem:
            out["cruzou_mm200_acima"].append(t)
        elif ontem and not hoje:
            out["cruzou_mm200_abaixo"].append(t)
    return out


def regime(precos: pd.DataFrame, classes: tuple[str, ...] | list[str], janela: int = 200) -> dict:
    """Regime de mercado: quantas classes de risco estão acima da MM de `janela` dias.

    ≥5 FAVORÁVEL · 3–4 MISTO · <3 DEFENSIVO (sobre o nº fixo de 7 classes do config). Classes sem preço são
    ignoradas e contadas em `ausentes`. Retorna {rotulo, tipo ('ok'|'warn'|'bad'), acima, total, ausentes}.
    """
    acima, ausentes = 0, []
    for t in classes:
        if t not in precos or precos[t].dropna().size <= janela:
            ausentes.append(t)
            continue
        s = precos[t].dropna()
        acima += bool(s.iloc[-1] > indicators.sma(s, janela).iloc[-1])
    rotulo, tipo = ("FAVORÁVEL", "ok") if acima >= 5 else ("MISTO", "warn") if acima >= 3 else ("DEFENSIVO", "bad")
    return {"rotulo": rotulo, "tipo": tipo, "acima": acima, "total": len(classes), "ausentes": ausentes}
