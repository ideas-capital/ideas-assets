"""Painel (Mercado hoje) — objetivo: em 30 segundos saber o regime e se há algo a fazer hoje.

Ordem: faixa de mercado → inteligência de mercado (regime, amplitude, VIX, eventos) → sinal do dia
→ ativo em destaque (gráfico + métricas da regra) → oportunidades → o que mudou → IA.
Cálculos em pwass/engine (swing.py, mercado.py); dados em pwass/data via pwass/ui/cache.py.
"""
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pwass.ai import committee
from pwass.data import fred
from pwass.engine import fatores as FT, indicators, mercado, swing as S
from pwass.engine.radar import zone_status
from pwass.ai import prompts
from pwass.ui import cache, charts, components as ds, context, settings, theme, tvchart
from pwass.ui.theme import badge, colored_pct, esc, num, pct

sw = cache.config("swing")
sid = st.session_state.get("estrategia_swing", sw.get("padrao", "pullback"))
strat, risk = sw["estrategias"][sid], sw["risco"]
names = {t: (n, g) for g, d in sw["universo"].items() for t, n in d.items()}
ia_on = st.session_state.get("ia_alertas", True)

# ------------------------------------------------------------------ dados
pcfg = cache.config("painel")
STRIP = pcfg["faixa"]
RISK_CLASSES = tuple(pcfg["classes_risco"])
with st.spinner("Carregando mercado e rodando as estratégias..."):
    data = cache.ohlcv(tuple(names), "10y")
    strip = cache.prices(tuple(i["ticker"] for i in STRIP) + RISK_CLASSES, "2y")
    table, bts = S.scan(data, names, sid, strat, risk)

_rg = mercado.regime(strip, RISK_CLASSES)
up, regime, rkind = _rg["acima"], _rg["rotulo"], _rg["tipo"]

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
REC = {"rec_ticker": "Faixa de mercado", "rec_inteligencia": "Inteligência de mercado", "rec_sinal": "Sinal do dia",
       "rec_grafico": "Gráfico", "rec_metricas": "Métricas da estratégia", "rec_tabela": "Oportunidades e novidades",
       "rec_ia": "IA"}
for k in REC:
    st.session_state.setdefault(k, True)

asof_px = max(strip[i["ticker"]].dropna().index[-1] for i in STRIP if i["ticker"] in strip)
h1, h2, h3 = st.columns([6.2, 1.3, 1.7], vertical_alignment="center")
with h1:
    ds.page_header("Painel", f"Estratégia ativa: {strat['nome']}")
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

# ------------------------------------------------------------------ faixa de mercado
if st.session_state["rec_ticker"]:
    items = []
    for i in STRIP:
        if i["ticker"] not in strip:
            items.append({"nome": i["nome"], "valor": "—", "var": None})  # indisponível, não estimado
            continue
        s_ = strip[i["ticker"]].dropna()
        items.append({"nome": i["nome"], "valor": num(s_.iloc[-1], i["casas"]),
                      "var": float(s_.iloc[-1] / s_.iloc[-2] - 1), "spark": list(s_.iloc[-60:])})
    ds.ticker_strip(items, source="Yahoo Finance", asof=f"último pregão de cada ativo, até {asof_px:%d/%m/%Y} · diário")

# ------------------------------------------------------------------ inteligência de mercado
amp = mercado.amplitude(data)
vix_s = strip["^VIX"].dropna() if "^VIX" in strip else None
vix_pct = mercado.percentil(vix_s) if vix_s is not None else float("nan")
cal_tk = tuple(i["ticker"] for i in cache.config("watchlist").get("satellite", []))
if st.session_state["rec_inteligencia"]:
    c1, c2, c3, c4 = st.columns(4)
    regime_kind = {"ok": "up", "warn": "warn", "bad": "down"}[rkind]
    c1.markdown(ds.kpi("Regime", f'<span style="color:var(--{regime_kind})">{regime}</span>',
                       source=f"{up} de {len(RISK_CLASSES)} classes de risco acima da MM200 (calculado)"),
                unsafe_allow_html=True)
    c1.caption(f"{up} de {len(RISK_CLASSES)} classes acima da MM200")
    c2.markdown(ds.kpi("Amplitude (> MM200)", pct(amp["pct"], 0, False),
                       source=f"{amp['acima']} de {amp['n']} ativos do universo do laboratório (calculado)"),
                unsafe_allow_html=True)
    c2.caption(f"{amp['acima']} de {amp['n']} ativos · tendência predominante: **{mercado.tendencia_predominante(amp['pct'])}**")
    c3.markdown(ds.kpi("VIX", num(vix_s.iloc[-1], 1) if vix_s is not None else "—",
                       source="Yahoo Finance (^VIX), observado"), unsafe_allow_html=True)
    c3.caption(f"percentil {pct(vix_pct, 0, False)} nos últimos 2 anos" if vix_pct == vix_pct else "percentil indisponível")
    with c4:
        cal = cache.earnings_calendar(cal_tk) if cal_tk else None
        prox = cal[(cal["Data"] >= pd.Timestamp.today().normalize()) &
                   (cal["Data"] <= pd.Timestamp.today().normalize() + pd.Timedelta(days=7))] if cal is not None and not cal.empty else None
        if prox is not None and not prox.empty:
            ev = "<br>".join(f"{r.Ticker} · {r.Data:%d/%m}" for r in prox.sort_values("Data").itertuples())
            st.markdown(ds.kpi("Resultados na semana (watchlist)", f'<span style="font-size:14px">{ev}</span>',
                               source="Yahoo Finance calendar"), unsafe_allow_html=True)
        else:
            st.markdown(ds.kpi("Resultados na semana (watchlist)", "—",
                               source="Sem resultados previstos ou calendário indisponível no Yahoo"),
                        unsafe_allow_html=True)
            st.caption("Nenhum resultado previsto ou dado indisponível")
    st.markdown(ds.source_note("Calculado pelo app a partir de dados do Yahoo Finance",
                               f"{asof_px:%d/%m/%Y} · universo e classes em config/swing.yaml e painel.yaml"),
                unsafe_allow_html=True)

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

if st.session_state["rec_sinal"] and best is not None:
    with st.expander("Por que este sinal? Fatores a favor e contra", icon=":material/rule:"):
        _tk = best["Ticker"]
        _outras = {}
        for _k, _d in sw["estrategias"].items():
            if _k != sid:
                _b = S.backtest(data[_tk], _k, _d, risk["custo_por_lado"], risk["multiplo_atr_stop"])
                _outras[_d["curto"]] = S.status_today(data[_tk], _k, _d, _b)[0]
        ds.fatores(FT.fatores(data[_tk], sid, strat, regime=regime, historico=best["Histórico"], outras_estrategias=_outras),
                   f"{_tk} · {strat['curto']}")
        st.caption("O score numérico de qualidade do sinal NÃO é mostrado: não passou na validação fora da amostra (docs/redesign/SCORE.md).")

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

# ------------------------------------------------------------------ oportunidades e novidades
if st.session_state["rec_tabela"]:
    st.markdown(f"#### Oportunidades · {strat['curto']}")
    groups = ["Todos"] + list(sw["universo"])
    f1, f2 = st.columns([3, 2], vertical_alignment="bottom")
    g = f1.segmented_control("Classe", groups, default="Todos", key="term_grp") or "Todos"
    so_acao = f2.toggle("Só com ação (esconde AGUARDAR e EVITAR)", value=True, key="term_so_acao")
    view = table if g == "Todos" else table[table["Classe"] == g]
    if so_acao:
        view = view[~view["Situação"].isin([S.AGUARDAR, S.EVITAR])]
    show_t = view[["Ticker", "Ativo", "Classe", "Último", "Dia", "Situação", "Histórico", "Operações", "Acerto",
                   "Profit factor", "Resultado médio", "CAGR", "CAGR B&H", "Detalhe"]].copy()
    show_t["Acerto"] *= 100
    ds.chips([f"Estratégia: {strat['curto']}", f"Classe: {g}", "Só com ação" if so_acao else "Todas as situações"])
    ds.data_table(show_t, key="term_opp", export_name=f"oportunidades_{sid}", on_select_open_asset="Ticker",
                  source="Yahoo Finance · backtest da regra em ~10 anos (simulado)", asof=f"{asof_px:%d/%m/%Y}",
                  column_config={"Último": st.column_config.NumberColumn(format="%.2f"),
                                 "Dia": st.column_config.NumberColumn(format="percent"),
                                 "Acerto": st.column_config.NumberColumn("Acerto", format="%.0f%%"),
                                 "Profit factor": st.column_config.NumberColumn("PF", format="%.2f"),
                                 "Resultado médio": st.column_config.NumberColumn("Médio/op.", format="percent"),
                                 "CAGR": st.column_config.NumberColumn("a.a. regra", format="percent"),
                                 "CAGR B&H": st.column_config.NumberColumn("a.a. B&H", format="percent"),
                                 "Detalhe": st.column_config.TextColumn(width="large")})
    st.caption("Histórico = qualidade da regra NAQUELE ativo nos últimos ~10 anos (Bom: profit factor ≥ 1,5; Regular: ≥ 1,1; "
               "Fraco: abaixo). Clique numa linha para abrir o ativo. O universo atual tem viés de sobrevivência.")

    st.markdown("#### O que mudou no último pregão")
    sinais = {t: S.signals(data[t], sid, strat) for t in bts}
    nov = mercado.novidades(data, sinais, {t: n for t, (n, _) in names.items()})
    saidas = table[table["Situação"] == S.SAIR]["Ticker"].tolist()
    linhas = [("Novos setups de compra", nov["novos_setups"]), ("Regra de saída acionada", saidas),
              ("Cruzaram a MM200 para cima", nov["cruzou_mm200_acima"]),
              ("Cruzaram a MM200 para baixo", nov["cruzou_mm200_abaixo"])]
    if any(v for _, v in linhas):
        for rot, v in linhas:
            if v:
                st.markdown(f"- **{rot}:** {', '.join(v)}")
    else:
        ds.empty_state("Sem mudanças relevantes", "Nenhum novo setup, saída ou cruzamento da MM200 no último pregão.")
    st.markdown(ds.source_note("Calculado pelo app (regras determinísticas)", f"{asof_px:%d/%m/%Y}"), unsafe_allow_html=True)

# ------------------------------------------------------------------ resumo do mercado por IA (veio da antiga página "Mercado")
if ia_on and st.session_state["rec_ia"]:
    with st.expander("Resumo do dia com IA", icon=":material/auto_awesome:"):
        st.caption("A IA recebe a faixa de mercado e o regime calculados acima e busca notícias recentes na web "
                   "(interpretação, não dado). Custo típico: menos de US$ 0,02.")
        model_r = settings.model_picker("mercado_modelo", default_preset="noticias")
        if st.button("Gerar resumo do mercado", type="primary", key="btn_resumo"):
            linhas_t = "\n".join(f"{i['nome']}: {num(strip[i['ticker']].dropna().iloc[-1], i['casas'])} "
                                  f"({pct(strip[i['ticker']].dropna().iloc[-1] / strip[i['ticker']].dropna().iloc[-2] - 1, 2)} no dia)"
                                  for i in STRIP if i["ticker"] in strip)
            extra = (f"Regime: {regime} ({up}/{len(RISK_CLASSES)} classes de risco acima da MM200). "
                     f"Amplitude: {pct(amp['pct'], 0, False)} dos ativos acima da MM200. VIX percentil {pct(vix_pct, 0, False)}.")
            res = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                   {"role": "user", "content": prompts.market_brief(linhas_t, extra)}],
                                  model=model_r, web=not model_r.startswith("perplexity/"))
            if res:
                settings.show_result(res, "resumo-mercado.md")
