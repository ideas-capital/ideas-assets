import numpy as np
import pandas as pd

from pwass.engine import alertas as A


def _df(close, vol=None, n=None):
    close = np.asarray(close, float)
    idx = pd.bdate_range("2024-01-01", periods=len(close))
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Volume": vol if vol is not None else np.full(len(close), 1e6)}, index=idx)


def al(tipo, **p):
    return {"id": "1", "ticker": "X", "tipo": tipo, "params": p, "ativo": True}


def test_preco_e_variacao():
    d = _df([100, 100, 110])
    assert A.avaliar(al("preco", direcao="acima", valor=105), d)["disparou"]
    assert not A.avaliar(al("preco", direcao="abaixo", valor=105), d)["disparou"]
    assert A.avaliar(al("variacao", limite_pct=5, direcao="alta"), d)["disparou"]
    assert not A.avaliar(al("variacao", limite_pct=5, direcao="queda"), d)["disparou"]
    assert abs(A.avaliar(al("variacao", limite_pct=5, direcao="qualquer"), d)["valor"] - 0.1) < 1e-12


def test_rsi_cruzamento_rompimento_volume():
    queda = _df(np.linspace(100, 50, 60))
    assert A.avaliar(al("rsi", direcao="abaixo", valor=30), queda)["disparou"]
    c = np.r_[np.full(60, 100.0), 90, 120]                      # passa de abaixo para acima da MM50 no último dia
    assert A.avaliar(al("cruzamento", media=50, sentido="acima"), _df(c))["disparou"]
    assert not A.avaliar(al("cruzamento", media=50, sentido="abaixo"), _df(c))["disparou"]
    r = np.r_[np.full(30, 100.0), 105]
    assert A.avaliar(al("rompimento", dias=20, lado="maxima"), _df(r))["disparou"]
    assert not A.avaliar(al("rompimento", dias=20, lado="minima"), _df(r))["disparou"]
    v = np.r_[np.full(30, 1e6), 3e6]
    assert A.avaliar(al("volume", multiplo=2), _df(np.full(31, 100.0), v))["disparou"]


def test_sinal_de_estrategia_e_dados_curtos():
    import yaml
    from tests import regressao
    sw = yaml.safe_load((regressao.ROOT / "config/swing.yaml").read_text(encoding="utf-8"))
    raw = pd.read_parquet(regressao.FIX / "ohlcv_swing.parquet")
    d = raw[raw.Ticker == "SPY"].drop(columns="Ticker").set_index("Date")
    r = A.avaliar(al("sinal", estrategia="pullback", situacao="COMPRA"), d, sw)
    assert isinstance(r["disparou"], bool) and "COMPRA" in r["mensagem"]
    assert not A.avaliar(al("preco", direcao="acima", valor=1), _df([1, 2]))["disparou"]     # < 3 barras
    assert A.avaliar(al("sinal", estrategia="x", situacao="COMPRA"), d, sw)["mensagem"].endswith("desconhecida")


def test_avaliar_todos_ignora_inativos_e_quebrados():
    d = _df([100, 100, 110])
    a1 = al("preco", direcao="acima", valor=105)
    a2 = {**al("preco", direcao="acima", valor=105), "id": "2", "ativo": False}
    a3 = {"id": "3", "ticker": "X", "tipo": "preco", "params": {}, "ativo": True}       # sem 'direcao' → erro tratado
    out = A.avaliar_todos([a1, a2, a3], {"X": d})
    assert [o["alerta"]["id"] for o in out] == ["1"]


def test_notify_formatar_e_telegram_sem_credencial():
    from pwass.data import notify
    txt = notify.formatar([{"mensagem": "X fechou em 10,00"}], "06/11/2026")
    assert "06/11/2026" in txt and "• X fechou em 10,00" in txt
    assert notify.telegram(None, "1", txt) is False and notify.telegram("t", None, txt) is False

    class S:
        def post(self, url, json=None, timeout=None):
            self.url, self.json = url, json
            class R:
                def raise_for_status(self): pass
            return R()
    s = S()
    assert notify.telegram("TOK", "42", "oi", sessao=s) and s.url.endswith("/botTOK/sendMessage") and s.json["chat_id"] == "42"


def test_descrever():
    assert A.descrever(al("preco", direcao="acima", valor=105)) == "Preço acima de 105"
    assert "MM50" in A.descrever(al("cruzamento", media=50, sentido="acima"))
    assert A.descrever(al("sinal", estrategia="pullback", situacao="COMPRA")) == "Estratégia pullback: COMPRA"
