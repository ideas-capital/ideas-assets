"""Mercado hoje — o Terminal do IDEAS CAPITAL assets.

Topo: regime, alertas e recursos. Faixa de cotações. Sinal do dia da estratégia
ativa (com plano de entrada, stop, alvos e tamanho da posição). Gráfico TradingView
com métricas reais do backtest. Radar de sinais e todas as classes embaixo.
"""
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pwass import radar as R
from pwass.ai import committee
from pwass.data import fred
from pwass.engine import indicators, swing as S
from pwass.engine.radar import zone_status
from pwass.ui import cache, charts, context, settings, theme, tvchart
from pwass.ui.theme import badge, colored_pct, esc, num, pct

sw = cache.config("swing")
sid = st.session_state.get("estrategia_swing", sw.get("padrao", "pullback"))
strat, risk = sw["estrategias"][sid], sw["risco"]
names = {t: (n, g) for g, d in sw["universo"].items() for t, n in d.items()}
ia_on = st.session_state.get("ia_alertas", True)

# ------------------------------------------------------------------ dados
TICKER_STRIP = [("^GSPC", "S&P 500"), ("^NDX", "Nasdaq 100"), ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"),
                ("GC=F", "Ouro"), ("BRL=X", "USD/BRL"), ("^TNX", "Juro 10a EUA"), ("^VIX", "VIX")]
RISK_CLASSES = ("SPY", "QQQ", "IWM", "VEU", "EEM", "VNQ", "DBC")
with st.spinner("Carregando mercado e rodando as estratégias..."):
    data = cache.ohlcv(tuple(names), "10y")
    strip = cache.prices(tuple(t for t, _ in TICKER_STRIP) + RISK_CLASSES, "2y")
    table, bts = S.scan(data, names, sid, strat, risk)

up = sum(bool(strip[t].dropna().iloc[-1] > indicators.sma(strip[t].dropna(), 200).iloc[-1]) for t in RISK_CLASSES)
regime, rkind = ("FAVORÁVEL", "ok") if up >= 5 else ("MISTO", "warn") if up >= 3 else ("DEFENSIVO", "bad")

# ------------------------------------------------------------------ alertas
alerts = []
for _, r in table[table["Situação"] == S.COMPRA].iterrows():
    alerts.append(("ok", f"<b>{r.Ticker}</b> — setup de compra ({strat['curto']}), histórico {r['Histórico'].lower()}"))
for _, r in table[table["Situação"] == S.SAIR].iterrows():
    alerts.append(("bad", f"<b>{r.Ticker}</b> — regra de saída acionada: vender na abertura"))
for it in cache.config("watchlist").get("satellite", []):
    t = it["ticker"]
    if t in data:
        stt, _ = zone_status(float(data[t]["Close"].iloc[-1]), it.get("zone_min"), it.get("zone_max"))
        if stt == "NA ZONA":
            alerts.append(("info", f"<b>{t}</b> entrou na sua zona de entrada ({it['zone_min']}–{it['zone_max']})"))

# ------------------------------------------------------------------ cabeçalho
REC = {"rec_ticker": "Faixa de cotações", "rec_sinal": "Sinal do dia", "rec_grafico": "Gráfico",
       "rec_metricas": "Métricas da estratégia", "rec_tabela": "Radar e classes", "rec_ia": "Comitê de IA"}
for k in REC:
    st.session_state.setdefault(k, True)

h1, h2, h3 = st.columns([6.2, 1.3, 1.7], vertical_alignment="center")
h1.markdown(f'<div class="ic-title"><h2>MERCADO HOJE</h2><span class="ic-pill">REGIME: '
            f'<b style="color:var(--{"up" if rkind == "ok" else "warn" if rkind == "warn" else "down"})">{regime}</b>'
            f' ({up} de {len(RISK_CLASSES)} classes de risco acima da MM200)</span>'
            f'<span class="ic-pill">Estratégia: <b>{esc(strat["nome"])}</b></span></div>', unsafe_allow_html=True)
if ia_on:
    with h2.popover(f"Alertas · {len(alerts)}", icon=":material/notifications:", width="stretch"):
        if not alerts:
            st.caption("Nenhum alerta hoje.")
        for kind, txt in alerts:
            st.markdown(f'<div class="ic-alert">{badge("●", kind)} {txt}</div>', unsafe_allow_html=True)
with h3.popover("Recursos", icon=":material/tune:", width="stretch"):
    st.caption("Mostrar ou esconder seções")
    for k, label in REC.items():
        st.toggle(label, key=k)

# ------------------------------------------------------------------ faixa de cotações
if st.session_state["rec_ticker"]:
    items = []
    for t, label in TICKER_STRIP:
        if t not in strip:
            continue
        s = strip[t].dropna()
        chg = s.iloc[-1] / s.iloc[-2] - 1
        digits = 4 if t == "BRL=X" else 2
        items.append(f'<div class="ic-tk"><div class="row"><span class="n">{label}</span>'
                     f'<span class="p">{num(s.iloc[-1], digits)}</span></div>'
                     f'<div class="row"><span style="font-size:.72rem;color:var(--muted)">{s.index[-1]:%d/%m}</span>'
                     f'{colored_pct(chg, 2)}</div>{theme.sparkline(s.iloc[-60:])}</div>')
    st.markdown(f'<div class="ic-ticker">{"".join(items)}</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ sinal do dia
best = S.best_setup(table)
default_tk = best["Ticker"] if best is not None else (
    table[table["Situação"].isin([S.SAIR, S.POSICAO, S.PERTO])]["Ticker"].iloc[0]
    if table["Situação"].isin([S.SAIR, S.POSICAO, S.PERTO]).any() else "SPY")


def decision_badge(row) -> str:
    q = row["Histórico"]
    if q in ("Bom", "Regular"):
        return '<span class="pw-badge pw-solid-ok">COMPRA</span>'
    if q == "Fraco":
        return '<span class="pw-badge pw-warn">SETUP COM HISTÓRICO FRACO — EVITAR</span>'
    return '<span class="pw-badge pw-warn">COMPRA ESPECULATIVA (pouco histórico)</span>'


if st.session_state["rec_sinal"]:
    if best is not None:
        tk = best["Ticker"]
        p = S.plan(data[tk], risk)
        stt = S.stats(bts[tk], S.periods_per_year(data[tk].index))
        exit_rule = {"pullback": f"saída principal pela regra: fechar acima da MM{strat.get('mm_saida', 5)}",
                     "cruzamento": "saída no cruzamento da EMA20 para baixo da EMA50",
                     "rompimento": f"saída ao fechar abaixo da mínima de {strat.get('canal_saida', 20)} dias"}[sid]
        others = table[(table["Situação"] == S.COMPRA) & (table["Ticker"] != tk)]["Ticker"].tolist()
        st.markdown(f"""
<div class="ic-panel"><div class="hd">Sinal do dia · {esc(strat['nome'])}</div>
<div class="ic-sig"><span class="tk">{tk}</span>{decision_badge(best)}
<span class="lv">Entrada ~{num(p['entrada'])} (abertura) · Stop {num(p['stop'])} · Alvo 1 {num(p['alvo1'])} · Alvo 2 {num(p['alvo2'])}</span></div>
<div style="margin-top:.45rem;font-size:.9rem">{esc(best['Ativo'])}: {esc(best['Detalhe'])} Tamanho pela regra de risco:
<b>{num(p['quantidade'], 2)} cotas (US$ {num(p['valor'], 0)})</b>, perda máxima <b>US$ {num(p['risco_usd'], 0)}</b>
(1% do laboratório). {exit_rule.capitalize()}.</div>
<div style="margin-top:.35rem;font-size:.82rem;color:var(--muted)">Histórico da regra em {tk} ({stt['Anos']:.0f} anos):
{stt['Operações']} operações · acerto {pct(stt['Taxa de acerto'], 0, False)} · profit factor {num(stt['Profit factor'], 2)} ·
resultado médio {pct(stt['Resultado médio'], 2)} por operação · máx. queda {pct(stt['Máx. queda estratégia'], 0)}.
{('Outros setups hoje: ' + ', '.join(others) + '.') if others else ''}</div></div>""", unsafe_allow_html=True)
    else:
        watch = table[table["Situação"].isin([S.PERTO])]["Ticker"].tolist()[:6]
        exits = table[table["Situação"] == S.SAIR]["Ticker"].tolist()
        st.markdown(f"""<div class="ic-panel"><div class="hd">Sinal do dia · {esc(strat['nome'])}</div>
<div class="ic-sig"><span class="tk">Sem setup novo hoje</span>{badge('AGUARDAR', 'mute')}</div>
<div style="margin-top:.4rem;font-size:.9rem">Perto do gatilho: <b>{', '.join(watch) or '—'}</b>.
{('Saídas acionadas: <b>' + ', '.join(exits) + '</b>.') if exits else ''} Disciplina também é não operar.</div></div>""",
                    unsafe_allow_html=True)

# ------------------------------------------------------------------ gráfico + métricas
if st.session_state["rec_grafico"] or st.session_state["rec_metricas"]:
    order = list(table["Ticker"])
    c1, c2 = st.columns([2.25, 1]) if st.session_state["rec_grafico"] and st.session_state["rec_metricas"] else (st.container(), st.container())
    with c1:
        a, b, c = st.columns([1.4, 0.9, 3.2], vertical_alignment="bottom")
        tk = a.selectbox("Ativo", order, index=order.index(default_tk) if default_tk in order else 0,
                         format_func=lambda t: f"{t} · {names.get(t, (t,))[0]}", key="term_tk")
        tf = b.segmented_control("Tempo", ["1D", "1S"], default="1D", key="term_tf",
                                 help="Diário ou semanal. Intradiário (1h/15m) não é usado: os dados grátis "
                                      "têm histórico curto demais para um backtest confiável.") or "1D"
        opts = ["Médias", "Bollinger", "Volume", "RSI", "Fibonacci", "Máx/Mín 20d", "Plano"]
        sel = c.pills("Indicadores e desenhos", opts, selection_mode="multi",
                      default=["Médias", "Bollinger", "Volume", "RSI", "Plano"], key="term_ind")
    df = data[tk]
    row = table.set_index("Ticker").loc[tk]
    p = S.plan(df, risk)
    if st.session_state["rec_grafico"]:
        with c1:
            show = {"mm": "Médias" in sel, "bb": "Bollinger" in sel, "vol": "Volume" in sel, "rsi": "RSI" in sel,
                    "fib": "Fibonacci" in sel, "hl20": "Máx/Mín 20d" in sel, "plan": "Plano" in sel}
            if tvchart.AVAILABLE:
                tvchart.render(df, tk, tf=tf, show=show, plan=p if row["Situação"] in (S.COMPRA, S.PERTO) else None,
                               trades=bts[tk].trades, key="term")
            else:
                st.plotly_chart(charts.price_chart(df["Close"], tk), width="stretch")
            st.caption(f"{tk}: **{row['Situação']}** — {row['Detalhe']}  ·  Setas = operações da regra "
                       f"{strat['curto']} no histórico (C = compra; % = resultado).")
    if st.session_state["rec_metricas"]:
        with c2:
            stt = S.stats(bts[tk], S.periods_per_year(df.index))
            pool = S.pooled(list(bts.values()))
            kpi = lambda l, v: f'<div class="ic-kpi"><div class="l">{l}</div><div class="v">{v}</div></div>'  # noqa: E731
            st.markdown(f"""<div class="ic-panel"><div class="hd">Métricas da estratégia · {tk}</div>
<div class="ic-kpis">{kpi('Taxa de acerto', pct(stt['Taxa de acerto'], 0, False))}{kpi('Profit factor', num(stt['Profit factor'], 2))}
{kpi('Resultado médio/op.', pct(stt['Resultado médio'], 2))}{kpi('Operações', str(stt['Operações']))}
{kpi('Retorno a.a. estratégia', pct(stt['CAGR estratégia']))}{kpi('Retorno a.a. buy & hold', pct(stt['CAGR buy & hold']))}
{kpi('Máx. queda estratégia', pct(stt['Máx. queda estratégia'], 0))}{kpi('Máx. queda buy & hold', pct(stt['Máx. queda buy & hold'], 0))}</div>
<div style="font-size:.78rem;color:var(--muted)">Posicionado {pct(stt['Tempo posicionado'], 0, False)} do tempo ·
{stt['Anos']:.0f} anos · custos de {risk['custo_por_lado'] * 100:.2f}% por lado · execução na abertura seguinte.<br>
Universo inteiro: {pool.get('Operações', 0)} operações, acerto {pct(pool.get('Taxa de acerto'), 0, False)},
PF {num(pool.get('Profit factor'), 2)}, médio {pct(pool.get('Resultado médio'), 2)}/op.</div></div>""",
                        unsafe_allow_html=True)
            b = bts[tk]
            eq = pd.DataFrame({"Estratégia": (1 + b.daily).cumprod(), "Buy & hold": (1 + b.bh).cumprod()})
            fig = go.Figure()
            t = theme.tokens()
            fig.add_scatter(x=eq.index, y=eq["Estratégia"], name="Estratégia", line=dict(color=t["up"], width=1.8),
                            fill="tozeroy", fillcolor="rgba(38,166,154,.10)")
            fig.add_scatter(x=eq.index, y=eq["Buy & hold"], name="Buy & hold", line=dict(color=t["muted"], width=1.2))
            lay = charts.layout()
            lay["legend"] = dict(orientation="h", y=-0.18, x=0, font=dict(size=11))
            lay["margin"] = dict(l=8, r=8, t=28, b=8)
            fig.update_layout(height=240, title=dict(text="Estratégia vs buy & hold (US$ 1 investido)", font=dict(size=12)),
                              **lay)
            fig.update_yaxes(type="log", tickformat=".1f")
            st.plotly_chart(fig, width="stretch", key=f"eq_{tk}_{sid}")
            dd = eq / eq.cummax() - 1
            fig2 = go.Figure()
            fig2.add_scatter(x=dd.index, y=dd["Estratégia"], name="Estratégia", line=dict(color=t["down"], width=1.2),
                             fill="tozeroy", fillcolor="rgba(239,83,80,.12)")
            lay2 = charts.layout()
            lay2["margin"] = dict(l=8, r=8, t=28, b=8)
            fig2.update_layout(height=170, title=dict(text="Queda da estratégia a partir do topo", font=dict(size=12)),
                               showlegend=False, **lay2)
            fig2.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig2, width="stretch", key=f"dd_{tk}_{sid}")
            last = b.trades.tail(6).iloc[::-1]
            if not last.empty:
                rows = [[f"{r['Entrada']:%d/%m/%y}", f"{r['Saída']:%d/%m/%y}", str(int(r["Dias"])), colored_pct(r["Retorno"])]
                        for _, r in last.iterrows()]
                st.markdown('<div class="hd" style="font-size:.72rem;color:var(--muted);margin:.2rem 0">ÚLTIMAS OPERAÇÕES</div>'
                            + theme.table([("Entrada", ""), ("Saída", ""), ("Dias", "r"), ("Resultado", "r")], rows,
                                          scroll=False), unsafe_allow_html=True)

# ------------------------------------------------------------------ comitê de IA
if ia_on and st.session_state["rec_ia"]:
    with st.expander(f"Comitê de IA · {st.session_state.get('term_tk', default_tk)} — técnico, macro/fundamentos, risco e juiz",
                     icon=":material/smart_toy:"):
        tk = st.session_state.get("term_tk", default_tk)
        models = cache.config("ai").get("comite", {})
        st.caption("Agentes: " + " · ".join(f"{k}: `{v}`" for k, v in models.items())
                   + " — custo típico ~US$ 0,02. Troque os modelos em config/ai.yaml.")
        if st.button("Rodar comitê", type="primary", icon=":material/play_arrow:"):
            df = data[tk]
            per = {}
            for k, d in sw["estrategias"].items():
                b = S.backtest(df, k, d, risk["custo_por_lado"], risk["multiplo_atr_stop"])
                stt = S.stats(b, S.periods_per_year(df.index))
                per[d["nome"]] = {"situacao_hoje": S.status_today(df, k, d, b), "historico": S.quality(stt),
                                  **{kk: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
                                     for kk, v in stt.items()}}
            macro = {}
            for sid_ in ("DGS10", "DFII10", "T10Y2Y", "BAMLH0A0HYM2"):
                try:
                    macro[fred.YIELDS.get(sid_, sid_)] = round(float(cache.fred(sid_).iloc[-1]), 2)
                except Exception:  # noqa: BLE001
                    pass
            macro["VIX"] = round(float(strip["^VIX"].dropna().iloc[-1]), 2) if "^VIX" in strip else None
            macro["USD/BRL"] = round(float(strip["BRL=X"].dropna().iloc[-1]), 4) if "BRL=X" in strip else None
            try:
                fund = context.for_ai(context.asset_bundle(tk))
            except Exception:  # noqa: BLE001
                fund = {}
            payload = {"ativo": tk, "nome": names.get(tk, (tk,))[0], "estrategia_ativa": strat["nome"],
                       "tecnica": indicators.snapshot(df["Close"]), "estrategias": per,
                       "plano_pela_regra_de_risco": p, "regras_de_risco": risk, "macro": macro,
                       "fundamentos": fund, "regime": f"{regime} ({up}/{len(RISK_CLASSES)} acima da MM200)"}
            res = committee.run(tk, payload, lambda m, model: settings.ask_ai(m, model=model), models)
            if "juiz" in res:
                st.markdown(res["juiz"][1].text)
            cols = st.columns(3)
            for col, key in zip(cols, ("tecnico", "fundamental", "risco")):
                if key in res:
                    name, r = res[key]
                    col.markdown(f"**{name}** · `{r.model}`\n\n{r.text}")
            total = sum((r.cost_usd or 0) for _, r in res.values())
            if res:
                st.caption(f"Custo total do comitê: US$ {total:.4f}")

# ------------------------------------------------------------------ tabelas
SIT_KIND = {S.COMPRA: "solid-ok", S.SAIR: "solid-bad", S.POSICAO: "info", S.PERTO: "warn",
            S.AGUARDAR: "mute", S.EVITAR: "bad"}
Q_KIND = {"Bom": "ok", "Regular": "info", "Pouco histórico": "mute", "Fraco": "bad"}
if st.session_state["rec_tabela"]:
    t1, t2 = st.tabs([f"Radar de sinais · {strat['curto']}", "Todas as classes"])
    with t1:
        groups = ["Todos"] + list(sw["universo"])
        g = st.segmented_control("Classe", groups, default="Todos", key="term_grp") or "Todos"
        view = table if g == "Todos" else table[table["Classe"] == g]
        rows = [[f"<b>{r.Ticker}</b> <span style='color:var(--muted)'>{esc(r.Ativo)}</span>", num(r["Último"]),
                 colored_pct(r["Dia"], 2), badge(r["Situação"], SIT_KIND[r["Situação"]]),
                 badge(r["Histórico"], Q_KIND[r["Histórico"]]), str(r["Operações"]), pct(r["Acerto"], 0, False),
                 num(r["Profit factor"], 2), pct(r["Resultado médio"], 2), pct(r["CAGR"]), pct(r["CAGR B&H"]),
                 esc(r["Detalhe"])] for _, r in view.iterrows()]
        st.markdown(theme.table([("Ativo", ""), ("Último", "r"), ("Dia", "r"), ("Situação", ""), ("Histórico", ""),
                                 ("Ops", "r"), ("Acerto", "r"), ("PF", "r"), ("Médio/op", "r"), ("a.a. regra", "r"),
                                 ("a.a. B&H", "r"), ("Detalhe", "w")], rows), unsafe_allow_html=True)
        st.caption("Histórico = qualidade da regra NAQUELE ativo nos últimos ~10 anos (Bom: profit factor ≥ 1,5; "
                   "Regular: ≥ 1,1; Fraco: abaixo). 'a.a. regra' considera só o tempo posicionado; compare com o B&H.")
    with t2:
        rcfg = cache.config("radar")
        assets, _ = R.assets(rcfg, cache.LOADERS, with_fundamentals=False)
        LK = {"verde": "ok", "azul": "info", "amarelo": "warn", "vermelho": "bad"}
        rows = [[f"<b>{esc(r['Ativo'])}</b> <span style='color:var(--muted)'>{r['Ticker']}</span>",
                 num(r["Preço"]), colored_pct(r["1 mês"]), colored_pct(r["12 meses"]), colored_pct(r["vs MM200"]),
                 num(r["RSI"], 0), badge(r["_status"].upper(), LK[r["_cor"]]), esc(r["Postura prudente"])]
                for _, r in assets.iterrows()]
        st.markdown(theme.table([("Ativo", ""), ("Último", "r"), ("1 mês", "r"), ("12 meses", "r"), ("vs MM200", "r"),
                                 ("RSI", "r"), ("Leitura", ""), ("Postura", "w")], rows), unsafe_allow_html=True)
