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
