import datetime as dt

from pwass.engine import mercado as m

NY, SP = m.NY, m.SP


def test_nyse_aberto_e_fechado():
    assert m.status_nyse(dt.datetime(2026, 11, 6, 11, 0, tzinfo=NY)) == (True, "aberto")   # sexta
    assert m.status_nyse(dt.datetime(2026, 11, 6, 17, 0, tzinfo=NY))[0] is False
    assert m.status_nyse(dt.datetime(2026, 11, 7, 11, 0, tzinfo=NY)) == (False, "fechado (fim de semana)")


def test_nyse_feriados_2026():
    f = m.feriados_nyse(2026)
    assert dt.date(2026, 11, 26) in f      # Thanksgiving
    assert dt.date(2026, 4, 3) in f        # Sexta-feira Santa
    assert dt.date(2026, 7, 3) in f        # 4 de julho cai no sábado → observado sexta
    assert dt.date(2026, 5, 25) in f       # Memorial Day


def test_conversao_de_fuso():
    # 14:30 UTC em novembro = 9:30 em Nova York → abre
    assert m.status_nyse(dt.datetime(2026, 11, 6, 14, 30, tzinfo=dt.timezone.utc))[0] is True


def test_b3():
    assert m.status_b3(dt.datetime(2026, 11, 6, 12, 0, tzinfo=SP)) == (True, "aberto")
    assert m.status_b3(dt.datetime(2026, 11, 20, 12, 0, tzinfo=SP)) == (False, "fechado (feriado)")  # Consciência Negra
    f = m.feriados_b3(2026)
    assert dt.date(2026, 2, 16) in f and dt.date(2026, 2, 17) in f   # Carnaval
    assert dt.date(2026, 6, 4) in f                                  # Corpus Christi
