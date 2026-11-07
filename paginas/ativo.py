"""Ativo — a página mais importante: tudo sobre um ativo em abas.

Visão geral · Técnica (candles, MM, Bollinger, RSI, MACD, Fibonacci, suporte/resistência) · Fundamentos
(só ações; ETF mostra taxa/AUM) · Histórico (backtest das 3 regras neste ativo) · Notícias e eventos · IA.
"""
import pandas as pd
import streamlit as st

from pwass.ai import prompts
from pwass.engine import ativo as A, health, indicators, radar, swing as S, valuation
from pwass.ui import cache, charts, components as ds, context, dados, settings, theme, tvchart
from pwass.ui.theme import badge, card, num, pct

ds.page_header("Ativo", "Preço, técnica, fundamentos, histórico das regras e uma segunda opinião da IA.")

default = st.session_state.get("ticker") or st.query_params.get("t") or "MSFT"
ticker = st.text_input("Ticker (Yahoo Finance)", value=default,
                       help="Ações e ETFs americanos (MSFT), ADRs (ASML), UCITS em Londres (CSPX.L), "
                            "B3 com sufixo .SA (PETR4.SA), cripto (BTC-USD).").strip().upper()
if not ticker:
    st.stop()
st.session_state["ticker"] = ticker

try:
    with st.spinner(f"Carregando {ticker}..."):
        b = context.asset_bundle(ticker)
except Exception as e:  # noqa: BLE001
    ds.error_state(f"Não consegui carregar {ticker}", str(e), "Confira o ticker (B3 usa .SA) e tente de novo.")
    st.stop()

f, tech, close = b["_fund_raw"], b["tecnica"], b["_close"]
klass = A.classe(f.get("quote_type"), ticker)
cur = {"BRL": "R$", "USD": "US$"}.get(f.get("currency") or "", f.get("currency") or "")
last_dt = close.dropna().index[-1]
var_dia = float(close.iloc[-1] / close.iloc[-2] - 1) if len(close) > 1 else None
ds.asset_header(ticker, f.get("name") or ticker, f.get("sector") or f.get("country") or "—", klass,
                tech["price"], var_dia, cur or "US$", asof=f"{last_dt:%d/%m/%Y}")
if not b["dcf"]["moedas_iguais"]:
    theme.note(f"Balanço em <b>{f.get('fin_currency')}</b> e preço em <b>{f.get('currency')}</b> (típico de ADR). "
               "Métricas que misturam os dois (DCF, Graham, EV/EBITDA, FCF yield) foram desligadas.", warn=True)

sw = cache.config("swing")
risk = sw["risco"]
try:
    _fav = dados.e_favorito(ticker)
    _a1, _a2, _ = st.columns([1.3, 1.6, 6], vertical_alignment="center")
    if _a1.button(":material/star: Favorito" if _fav else ":material/star_border: Favoritar", key="fav_btn",
                  help="Adiciona/remove da watchlist 'Favoritos'."):
        dados.alternar_favorito(ticker)
        st.rerun()
    with _a2.popover("Criar alerta", icon=":material/notifications:"):
        dados.formulario_alerta(ticker, "ativo_al", sw)
except Exception as _e:  # noqa: BLE001 — store indisponível não pode derrubar a página
    st.caption(f"Favoritos e alertas indisponíveis agora: {_e}")
try:
    ohl = cache.ohlcv((ticker,), "10y").get(ticker)
except Exception:  # noqa: BLE001
    ohl = None

tabs = ["Visão geral", "Técnica", "Fundamentos", "Histórico", "Notícias e eventos", "Análise com IA"]
t_ov, t_tec, t_fund, t_hist, t_news, t_ai = st.tabs(tabs)

# ------------------------------------------------------------------ Visão geral
with t_ov:
    perf = A.performance(ohl["Close"] if ohl is not None else close)   # candles de 10 anos permitem a janela de 5A
    ds.kpi_row([ds.kpi(k, pct(v) if v is not None else "—", source=f"Yahoo Finance, calculado por data de calendário até {last_dt:%d/%m/%Y}"
                       if v is not None else "Histórico insuficiente para esta janela") for k, v in perf.items()])
    if ohl is not None:
        with ds.chart_container(f"{ticker} · diário", "Yahoo Finance (preços ajustados)", f"{last_dt:%d/%m/%Y}"):
            tvchart.render(ohl, ticker, tf="1D", show={"mm": True, "bb": False, "vol": True, "rsi": False, "plan": False},
                           key="ativo_ov")
    else:
        ds.empty_state("Candles indisponíveis", "O Yahoo não retornou OHLC deste ticker.")
        st.plotly_chart(charts.price_chart(close, ticker), width="stretch")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("##### Semáforo de tendência")
        try:
            hl = health.price_health(close)
            ds.insight_card(f"{hl['status']} · {hl['motivos']}", hl["postura"],
                            "Leitura de tendência por regras (MM200, RSI, volatilidade); não considera fundamentos.",
                            origin="calculado")
        except Exception:  # noqa: BLE001
            ds.empty_state("Semáforo indisponível", "Histórico curto demais (precisa de ~1 ano).")
    with sc2:
        st.markdown("##### Sinais ativos das regras")
        if ohl is None or len(ohl) < 260:
            ds.empty_state("Sinais indisponíveis", "Precisa de ~1 ano de candles diários.")
        else:
            rows = []
            for sid_, d_ in sw["estrategias"].items():
                bt_ = S.backtest(ohl, sid_, d_, risk["custo_por_lado"], risk["multiplo_atr_stop"])
                stt_ = S.status_today(ohl, sid_, d_, bt_)
                rows.append({"Estratégia": d_["curto"], "Situação": stt_[0],
                             "Histórico": S.quality(S.stats(bt_, S.periods_per_year(ohl.index)))})
            ds.data_table(pd.DataFrame(rows), key="ativo_sinais",
                          source="Calculado pelo app; histórico = backtest (simulado)", asof=f"{last_dt:%d/%m/%Y}")

# ------------------------------------------------------------------ Técnica
with t_tec:
    if ohl is None or len(ohl) < 260:
        ds.empty_state("Gráfico técnico indisponível", "Precisa de ~1 ano de candles diários do Yahoo.")
    else:
        a1, a2 = st.columns([1, 4], vertical_alignment="bottom")
        tf = a1.segmented_control("Intervalo", ["1D", "1S"], default="1D", key="ativo_tf") or "1D"
        periodo = a1.segmented_control("Período", ["3M", "6M", "1A", "5A", "Tudo"], default="1A", key="ativo_per") or "1A"
        sel = a2.pills("Indicadores", ["Médias", "Bollinger", "Volume", "RSI", "MACD", "Fibonacci", "Suporte/Resistência"],
                       selection_mode="multi", default=["Médias", "Volume", "RSI"], key="ativo_ind")
        bars_ = {"3M": 63, "6M": 126, "1A": 252, "5A": 1260, "Tudo": len(ohl)}[periodo]
        if tf == "1S":
            bars_ = max(bars_ // 5, 26)
        sr = indicators.support_resistance(ohl)
        show = {"mm": "Médias" in sel, "bb": "Bollinger" in sel, "vol": "Volume" in sel, "rsi": "RSI" in sel,
                "macd": "MACD" in sel, "fib": "Fibonacci" in sel, "sr": "Suporte/Resistência" in sel, "plan": False}
        with ds.chart_container(f"{ticker} · {'diário' if tf == '1D' else 'semanal'}", "Yahoo Finance (preços ajustados)",
                                f"{last_dt:%d/%m/%Y}",
                                legend="MM20 azul · MM50 laranja · MM200 roxo · suportes verdes e resistências vermelhas "
                                       "(pivôs de 5 barras, confirmados 5 barras depois)"):
            tvchart.render(ohl, ticker, tf=tf, show=show, levels=sr, bars=bars_, key="ativo_tec")
        pv = indicators.pivot_points(*(float(ohl[c].iloc[-22:].max() if c == "High" else ohl[c].iloc[-22:].min() if c == "Low" else ohl[c].iloc[-1])
                                       for c in ("High", "Low", "Close")))
        theme.note(f"MM50 {num(tech['sma50'])} · MM200 {num(tech['sma200'])} · preço {pct(tech['price'] / tech['sma200'] - 1)} vs MM200 · "
                   f"Bollinger {num(tech['bb_lower'])}–{num(tech['bb_upper'])} · RSI semanal {num(tech['rsi14_w'], 0)}<br>"
                   f"Pivôs clássicos (últimos 22 pregões): S2 {num(pv['S2'])} · S1 {num(pv['S1'])} · P {num(pv['P'])} · "
                   f"R1 {num(pv['R1'])} · R2 {num(pv['R2'])} <span style='color:var(--muted)'>(calculado)</span>")

# ------------------------------------------------------------------ Fundamentos (só ações)
with t_fund:
    if klass == "ETF":
        ds.kpi_row([ds.kpi("Taxa de administração", pct(f.get("expense_ratio"), 2, False) if f.get("expense_ratio") is not None else "—",
                           source="Yahoo Finance; indisponível se vazio"),
                    ds.kpi("Patrimônio (AUM)", num(f.get("aum"), 0, cur + " ") if f.get("aum") else "—", source="Yahoo Finance"),
                    ds.kpi("Rendimento (dividendos)", pct(f.get("div_yield"), 2, False) if f.get("div_yield") else "—",
                           source="Yahoo Finance")])
        ds.empty_state("Composição e valuation de empresa não se aplicam a ETF",
                       "P/L, ROE e Piotroski são de empresas. Composição do ETF não vem do Yahoo gratuito.")
    elif klass in ("Cripto", "Índice", "Câmbio", "Futuro"):
        ds.empty_state(f"Sem fundamentos para {klass.lower()}", "Use a aba Técnica e o Histórico das regras.")
    else:
        if klass == "Desconhecida":
            theme.note("O Yahoo não informou o tipo deste ativo; fundamentos abaixo podem estar incompletos.", warn=True)
        theme.cards([
            card("P/L futuro", num(f.get("fwd_pe"), 1), f"atual {num(f.get('pe'), 1)}"),
            card("ROE", pct(f.get("roe"), 0, sign=False), f"margem op. {pct(f.get('op_margin'), 0, sign=False)}"),
            card("Crescimento receita", pct(f.get("rev_growth"), 0), f"lucro {pct(f.get('eps_growth'), 0)}"),
            card("Dívida / patrimônio", num(f.get("debt_equity"), 0), "em %, segundo o Yahoo"),
            card("Piotroski", f"{b['piotroski']['pontos']}/{b['piotroski']['de']}" if b["piotroski"]["de"] else "—",
                 "saúde financeira (9 = máx.)"),
            card("Alvo médio analistas", num(f.get("target_mean")), f"{f.get('n_analysts') or 0} analistas"),
            card("Valor de mercado", num(f.get("market_cap"), 0, cur + " ") if f.get("market_cap") else "—", "Yahoo Finance"),
            card("Beta", num(f.get("beta"), 2), "vs mercado"),
        ])
        st.markdown(ds.source_note("Yahoo Finance (fundamentos podem ter defasagem de trimestres)"), unsafe_allow_html=True)
        h_tab, v_tab = st.tabs(["Saúde financeira", "Valuation"])
        t_health, t_val = h_tab, v_tab
        with t_health:
            tests = b["_piotroski_tests"]
            if tests is None or tests.empty:
                st.info("Demonstrativos indisponíveis para este ticker (comum em ETFs).")
            else:
                theme.note("<b>Piotroski F-Score (2000)</b>: 9 testes simples comparando o último ano com o anterior. "
                           "8–9 = empresa melhorando em quase tudo; 0–3 = sinais de deterioração. Bancos e seguradoras "
                           "não têm alguns itens (aparecem em branco).")
                shown = tests.copy()
                shown["Passou"] = shown["Passou"].map({True: "✅", False: "❌", None: "—"})
                st.dataframe(shown, width="stretch", hide_index=True)

        with t_val:
            d = b["dcf"]
            if not d["moedas_iguais"] or "fcf_por_acao" not in d:
                st.info("DCF indisponível: moedas diferentes ou sem caixa livre positivo informado.")
            else:
                theme.note("<b>DCF reverso</b>: em vez de chutar o futuro, pergunta quanto crescimento o preço de hoje "
                           "já embute. Se o número for maior do que a empresa entregou na história, o preço exige perfeição.")
                g = d["crescimento_implicito_5a"]
                theme.signal_box("O preço atual embute", f"{pct(g, 1, sign=False)} de crescimento ao ano",
                                 f"no caixa livre por ação pelos próximos 5 anos (desacelerando até 2,5% no ano 10), "
                                 f"descontado a 9% a.a. Caixa livre por ação hoje: {num(d['fcf_por_acao'])}.")
                c1, c2, c3 = st.columns(3)
                growth = c1.slider("Seu crescimento (anos 1–5)", -10, 40, int(min(max((f.get("rev_growth") or 0.08) * 100, 0), 25))) / 100
                disc = c2.slider("Taxa de desconto", 6.0, 14.0, 9.0, 0.5) / 100
                term = c3.slider("Crescimento terminal", 0.0, 4.0, 2.5, 0.5) / 100
                fair = valuation.dcf_value(d["fcf_por_acao"], growth, disc, term)
                upside = fair / tech["price"] - 1
                margin = cache.config("watchlist")["strategy"]["margin_of_safety_pct"]
                v, why = radar.verdict(tech, "SEM ZONA", fair_value=fair, fwd_pe=f.get("fwd_pe"), margin_pct=margin)
                theme.cards([
                    card("Preço justo (seu DCF)", num(fair), f"vs preço: {pct(upside)}"),
                    card("Compra com margem", num(fair * (1 - margin / 100)), f"{margin}% abaixo do justo"),
                    card("Número de Graham", num(d.get("graham")), "referência p/ empresas maduras"),
                    card("Veredito do motor", "", "; ".join(why), theme.verdict_badge(v)),
                ])


# ------------------------------------------------------------------ Histórico (backtest neste ativo)
with t_hist:
    if ohl is None or len(ohl) < 260:
        ds.empty_state("Histórico indisponível", "Precisa de ~1 ano de candles diários.")
    else:
        theme.note("<b>Simulado</b>: sinal no fechamento, execução na abertura seguinte, custo de "
                   f"{risk['custo_por_lado'] * 100:.2f}% por lado, stop em {risk['multiplo_atr_stop']:g}×ATR. Resultado passado não garante futuro.")
        for sid_, d_ in sw["estrategias"].items():
            bt_ = S.backtest(ohl, sid_, d_, risk["custo_por_lado"], risk["multiplo_atr_stop"])
            st_ = S.stats(bt_, S.periods_per_year(ohl.index))
            with st.expander(f"{d_['nome']} · histórico {S.quality(st_).lower()} · {st_['Operações']} operações", expanded=sid_ == sw.get("padrao")):
                ds.kpi_row([ds.kpi("Taxa de acerto", pct(st_["Taxa de acerto"], 0, False), source="backtest (simulado)"),
                            ds.kpi("Profit factor", num(st_["Profit factor"], 2), source="backtest (simulado)"),
                            ds.kpi("Retorno a.a. regra", pct(st_["CAGR estratégia"]), source="só tempo posicionado; backtest"),
                            ds.kpi("Retorno a.a. buy & hold", pct(st_["CAGR buy & hold"]), source="mesmo período"),
                            ds.kpi("Máx. queda", pct(st_["Máx. queda estratégia"], 0), source="backtest (simulado)")])
                if len(bt_.trades):
                    tr = bt_.trades.copy()
                    ds.data_table(tr, key=f"ativo_tr_{sid_}", export_name=f"trades_{ticker}_{sid_}",
                                  column_config={"Retorno": st.column_config.NumberColumn(format="percent")},
                                  source="Backtest (simulado)", asof=f"{last_dt:%d/%m/%Y}")
                else:
                    ds.empty_state("Nenhuma operação", "A regra não gerou sinais neste ativo no período.")

# ------------------------------------------------------------------ Notícias e eventos
with t_news:
    n1, n2 = st.columns(2)
    with n1:
        st.markdown("##### Notícias (Yahoo Finance)")
        news = cache.news(ticker)
        if not news:
            ds.empty_state("Sem notícias", "O Yahoo não retornou notícias para este ticker agora.")
        for n in news:
            st.markdown(f"- [{n['titulo']}]({n['link']}) · {n['fonte']}")
        st.markdown(ds.source_note("Yahoo Finance", "títulos e links originais"), unsafe_allow_html=True)
    with n2:
        st.markdown("##### Documentos na SEC (10-K, 10-Q, 8-K)")
        if klass in ("Ação", "Desconhecida"):
            try:
                fl = cache.sec_filings(ticker, settings.sec_user_agent())
                ds.data_table(fl[["filingDate", "form", "url"]].rename(columns={"filingDate": "Data", "form": "Formulário", "url": "Documento"}),
                              key="ativo_sec", column_config={"Documento": st.column_config.LinkColumn("Documento", display_text="abrir")},
                              source="SEC EDGAR")
            except Exception as e:  # noqa: BLE001
                ds.empty_state("Sem documentos da SEC", str(e))
        else:
            ds.empty_state("Não se aplica", "A SEC cobre empresas listadas nos EUA e ADRs.")

# ------------------------------------------------------------------ IA
with t_ai:
    theme.note("A IA recebe todos os números desta tela (não a internet) e faz uma auditoria estruturada. "
               "O <b>debate</b> usa 3 modelos diferentes: um otimista, um pessimista e um juiz.")
    q = st.text_area("Pergunta específica (opcional)", placeholder="Ex.: o múltiplo atual se justifica pelo crescimento?")
    model = settings.model_picker("ativo_modelo")
    data = context.for_ai(b)
    c1, c2 = st.columns(2)
    if c1.button("Auditar com IA", type="primary", width="stretch"):
        r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                             {"role": "user", "content": prompts.audit_asset(ticker, data, q)}], model=model)
        if r:
            settings.show_result(r, f"auditoria-{ticker}.md")
    if c2.button("Debate: otimista × pessimista × juiz", width="stretch"):
        deb = cache.config("ai")["debate"]
        payload = prompts._blob(data)
        bull = settings.ask_ai([{"role": "system", "content": prompts.BULL}, {"role": "user", "content": payload}],
                               model=deb["bull"], temperature=0.5)
        bear = settings.ask_ai([{"role": "system", "content": prompts.BEAR}, {"role": "user", "content": payload}],
                               model=deb["bear"], temperature=0.5) if bull else None
        if bull and bear:
            x, y = st.columns(2)
            x.markdown(f"**🟢 Otimista** · `{bull.model}`\n\n{bull.text}")
            y.markdown(f"**🔴 Pessimista** · `{bear.model}`\n\n{bear.text}")
            judge = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                     {"role": "user", "content": prompts.judge(ticker, data, bull.text, bear.text)}],
                                    model=deb["judge"])
            if judge:
                st.markdown("---\n**⚖️ Juiz**")
                settings.show_result(judge, f"debate-{ticker}.md")
