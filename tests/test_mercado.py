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


def _df(close):
    import numpy as np
    import pandas as pd
    return pd.DataFrame({"Close": np.asarray(close, float)}, index=pd.bdate_range("2020-01-01", periods=len(close)))


def test_amplitude_e_tendencia():
    import numpy as np
    alta, baixa, curto = _df(np.linspace(50, 100, 300)), _df(np.linspace(100, 50, 300)), _df(np.linspace(1, 2, 50))
    a = m.amplitude({"A": alta, "B": baixa, "C": curto})
    assert (a["acima"], a["n"], a["pct"]) == (1, 2, 0.5)       # histórico curto fica de fora
    assert m.tendencia_predominante(0.7) == "alta" and m.tendencia_predominante(0.5) == "mista"
    assert m.tendencia_predominante(0.1) == "baixa" and m.tendencia_predominante(float("nan")) == "indisponível"


def test_percentil():
    import pandas as pd
    s = pd.Series(range(1, 101))
    assert m.percentil(s) == 1.0 and m.percentil(s.iloc[::-1].reset_index(drop=True)) == 0.01


def test_novidades_cruzamento_mm200_e_setup():
    import numpy as np
    import pandas as pd
    c = np.r_[np.linspace(100, 150, 250), 120, 160.0]            # cruza para cima na última barra
    d = _df(c)
    assert d["Close"].iloc[-3] > 0
    sinal_novo = pd.DataFrame({"entry": [False, False, True]})
    sinal_velho = pd.DataFrame({"entry": [False, True, True]})
    n = m.novidades({"X": _df(np.r_[np.linspace(100, 150, 250), 80, 160.0])}, {"A": sinal_novo, "B": sinal_velho}, {})
    assert n["novos_setups"] == ["A"] and n["cruzou_mm200_acima"] == ["X"]
