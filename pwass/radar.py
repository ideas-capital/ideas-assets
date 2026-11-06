"""Monta o Radar de ativos. Usado pela tela do app e pelo script diário.

Recebe um objeto `loaders` com as funções de coleta, para que o app use as
versões com cache e o script (GitHub Actions) use as diretas.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import pandas as pd

from pwass.data import brasil, fred, market
from pwass.engine import health as H

EMOJI = {H.VERDE: "🟢", H.AZUL: "🔵", H.AMARELO: "🟡", H.VERMELHO: "🔴"}

DIRECT = SimpleNamespace(
    prices=lambda tickers, period: market.prices(list(tickers), period),
    fundamentals=lambda tickers: market.fundamentals_many(list(tickers)),
    fred=fred.series,
    sgs=lambda sid, start=None, last=None: brasil.sgs(sid, start=start, last=last),
    focus=brasil.focus_ipca_12m,
    tesouro=brasil.tesouro,
)


def _row(group, ticker, name, h):
    return {"Grupo": group, "Ticker": ticker, "Ativo": name, "Leitura": f"{EMOJI[h['cor']]} {h['status']}",
            "Preço": h["preco"], "1 mês": h["ret_1m"], "12 meses": h["ret_12m"], "vs MM200": h["dist_mm200"],
            "RSI": h["rsi"], "Vol. 3m": h["vol_3m"], "Queda do topo": h["queda_topo"],
            "Postura prudente": h["postura"], "Motivos": h["motivos"], "_cor": h["cor"], "_status": h["status"]}


def assets(cfg: dict, L=DIRECT, with_fundamentals: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Semáforo de todos os ativos com preço. Retorna (tabela, preços)."""
    groups = cfg["grupos"]
    tickers = [t for g in groups.values() for t in g["ativos"]] + list(cfg.get("cambio", {}))
    px = L.prices(tuple(dict.fromkeys(tickers)), "3y")
    rows = []
    for gname, g in groups.items():
        for t, name in g["ativos"].items():
            if t not in px or px[t].dropna().shape[0] < 230:
                continue
            h = H.price_health(px[t], g.get("esticado", 0.25), g.get("rsi_quente", 75))
            rows.append(_row(gname, t, name, h))
    df = pd.DataFrame(rows)
    stocks = [t for gname, g in groups.items() if "Ações" in gname for t in g["ativos"]]
    if with_fundamentals and stocks and not df.empty:
        try:
            f = L.fundamentals(tuple(stocks))
            df["P/L futuro"] = df["Ticker"].map(pd.to_numeric(f["fwd_pe"], errors="coerce"))
        except Exception:  # noqa: BLE001 — fundamentos são opcionais no radar
            pass
    return df, px


def us_rates(L=DIRECT) -> pd.DataFrame:
    """Juros, inflação e crédito dos EUA com leitura histórica."""
    rows = []

    def add(name, value, pct, reading, cor, since, unit="%"):
        rows.append({"Indicador": name, "Valor": value, "Unidade": unit, "Percentil": pct,
                     "Leitura": f"{EMOJI[cor]} {reading}", "Histórico desde": since, "_cor": cor})

    def safe(sid):
        try:
            return L.fred(sid)
        except Exception:  # noqa: BLE001
            return None

    cpi = safe("CPIAUCSL")
    tb = safe("DGS3MO")
    if tb is not None:
        txt, cor = "caixa em dólar", H.AZUL
        if cpi is not None:
            real = H.real_rate(tb.iloc[-1], cpi.iloc[-1])
            txt = f"rende {'+' if real >= 0 else ''}{_br(real)}% acima da inflação ({_br(cpi.iloc[-1])}%)"
            cor = H.VERDE if real > 1 else H.AZUL if real > 0 else H.VERMELHO
        add("T-Bill 3 meses", tb.iloc[-1], H.percentile(tb[tb.index >= "2006"]), txt, cor, 2006)
    for sid, name, since in (("DGS10", "Treasury 10 anos", 2006), ("DGS30", "Treasury 30 anos", 2006)):
        s = safe(sid)
        if s is not None:
            s = s[s.index >= str(since)]
            p = H.percentile(s)
            txt, cor = H.reading_rate(s.iloc[-1], p, hi="taxa alta para os padrões de 20 anos",
                                      lo="taxa baixa: pouco prêmio para prazo longo")
            add(name, s.iloc[-1], p, txt, cor, since)
    s = safe("DFII10")
    if s is not None:
        p = H.percentile(s)
        v = s.iloc[-1]
        txt = ("juro real acima de 2%: historicamente bom para travar" if v >= 2 else
               "juro real positivo, moderado" if v > 0.5 else "juro real baixo ou negativo")
        add("Juro real 10 anos (TIPS)", v, p, txt, H.VERDE if v >= 2 else H.AZUL if v > 0.5 else H.VERMELHO, 2003)
    s = safe("T10Y2Y")
    if s is not None:
        v = s.iloc[-1]
        add("Curva 10a − 2a", v, H.percentile(s[s.index >= "2006"]),
            "curva invertida: sinal clássico de alerta" if v < 0 else "curva positiva (normal)",
            H.VERMELHO if v < 0 else H.AZUL, 2006, "p.p.")
    for sid, name in (("BAMLC0A0CM", "Spread crédito grau de investimento"), ("BAMLH0A0HYM2", "Spread High Yield")):
        s = safe(sid)
        if s is not None:
            p = H.percentile(s)
            txt, cor = ("spread apertado: crédito caro, pouco prêmio pelo risco", H.AMARELO) if p <= 25 else \
                       ("spread largo: mercado estressado, prêmio alto (com risco)", H.AZUL) if p >= 75 else \
                       ("spread na média dos últimos anos", H.AZUL)
            add(name, s.iloc[-1], p, txt, cor, s.index[0].year, "p.p.")
    return pd.DataFrame(rows)


def brazil(L=DIRECT, fx: pd.Series | None = None, tbill: float | None = None) -> dict:
    """Renda fixa brasileira: indicadores, Tesouro Direto e comparação com o T-Bill."""
    out: dict = {"erros": []}

    def safe(fn, *a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:  # noqa: BLE001
            out["erros"].append(str(e)[:120])
            return None

    selic = safe(L.sgs, brasil.SGS["selic_meta"], last=1)
    cdi = safe(L.sgs, brasil.SGS["cdi_aa"], last=1)
    ipca = safe(L.sgs, brasil.SGS["ipca_12m"], last=1)
    foc = safe(L.focus)
    ind = {}
    if selic is not None:  # a série traz a meta vigente com data futura (até a próxima reunião)
        ind["Selic meta"] = (selic.iloc[-1], "vigente")
    if cdi is not None:
        ind["CDI"] = (cdi.iloc[-1], f"{cdi.index[-1]:%d/%m/%Y}")
    if ipca is not None:
        ind["IPCA 12 meses"] = (ipca.iloc[-1], f"{ipca.index[-1]:%m/%Y}")
    if foc:
        ind["IPCA esperado 12m (Focus)"] = (foc[0], foc[1])
    if selic is not None and foc:
        rr = H.real_rate(selic.iloc[-1], foc[0])
        ind["Juro real ex-ante"] = (rr, "Selic ÷ IPCA esperado")
        out["juro_real"] = rr
    out["indicadores"] = ind

    td = safe(L.tesouro)
    if td is not None:
        today = brasil.tesouro_hoje(td)
        out["tesouro"] = today
        out["data_tesouro"] = today["Data"].max()
        hist = brasil.ipca_plus_history(td)
        out["ipca_hist"] = hist
        if len(hist):
            out["ipca_atual"] = hist.iloc[-1]
            out["ipca_pct"] = H.percentile(hist)
        out["implicita"] = brasil.implied_inflation(today)

    if cdi is not None and tbill is not None and not math.isnan(tbill):
        out["breakeven"] = H.fx_breakeven(cdi.iloc[-1], tbill)
    if fx is not None and fx.dropna().shape[0] > 230:
        out["dolar"] = H.price_health(fx, stretch=0.10, rsi_hot=70)
    return out


def _br(x: float, d: int = 1) -> str:
    """Número no formato brasileiro (vírgula decimal)."""
    return f"{x:.{d}f}".replace(".", ",")


def summary(df: pd.DataFrame, us: pd.DataFrame, br: dict) -> list[str]:
    """Frases-resumo com regras fixas (sem IA)."""
    lines = []
    risk = df[~df["Grupo"].str.contains("Renda fixa", regex=False)] if not df.empty else df
    if not risk.empty:
        above = risk["_status"].isin(["Alta saudável", "Esticado", "Recuperando"]).sum()
        healthy = (risk["_status"] == "Alta saudável").sum()
        hot = (risk["_status"] == "Esticado").sum()
        down = (risk["_status"] == "Tendência de baixa").sum()
        lines.append(f"<b>{above} de {len(risk)}</b> ativos de risco estão acima da média de 200 dias "
                     f"(<b>{healthy}</b> em alta saudável); <b>{hot}</b> esticado(s) e <b>{down}</b> em "
                     "tendência de baixa.")
    tips = us[us["Indicador"].str.startswith("Juro real")] if not us.empty else us
    if not tips.empty:
        lines.append(f"Juro real americano de 10 anos em <b>{_br(tips['Valor'].iloc[0], 2)}%</b> "
                     f"(percentil {tips['Percentil'].iloc[0]:.0f} desde 2003).")
    if "juro_real" in br:
        lines.append(f"Juro real brasileiro ex-ante em <b>{_br(br['juro_real'])}%</b>"
                     + (f"; IPCA+ longo pagando <b>{_br(br['ipca_atual'], 2)}%</b> + inflação "
                        f"(percentil {br['ipca_pct']:.0f} desde 2010)." if "ipca_atual" in br else "."))
    if "breakeven" in br:
        lines.append(f"Para o T-Bill empatar com o CDI (líquidos de IR), o dólar precisa subir "
                     f"~<b>{_br(br['breakeven'])}% ao ano</b>.")
    return lines
