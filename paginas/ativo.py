"""Raio-X de um ativo: fundamentos, técnica, saúde (Piotroski), valuation e IA."""
import streamlit as st

from pwass.ai import prompts
from pwass.engine import radar, valuation
from pwass.ui import cache, charts, context, settings, theme
from pwass.ui.theme import badge, card, num, pct

theme.header("Raio-X do ativo", "Tudo sobre uma ação ou ETF em uma tela — e uma segunda opinião da IA.")

default = st.session_state.get("ticker", "MSFT")
ticker = st.text_input("Ticker (Yahoo Finance)", value=default,
                       help="Ações e ETFs americanos (MSFT), ADRs (ASML) ou UCITS em Londres (CSPX.L).").strip().upper()
if not ticker:
    st.stop()
st.session_state["ticker"] = ticker

try:
    with st.spinner(f"Carregando {ticker}..."):
        b = context.asset_bundle(ticker)
except Exception as e:  # noqa: BLE001
    st.error(f"Não consegui carregar {ticker}: {e}")
    st.stop()

f, tech, close = b["_fund_raw"], b["tecnica"], b["_close"]
st.markdown(f"### {f.get('name') or ticker}  \n"
            f"{f.get('sector') or ''} · {f.get('industry') or ''} · {f.get('country') or ''} · "
            f"cotação em {f.get('currency') or '?'}")
if not b["dcf"]["moedas_iguais"]:
    theme.note(f"Balanço em <b>{f.get('fin_currency')}</b> e preço em <b>{f.get('currency')}</b> (típico de ADR). "
               "Métricas que misturam os dois (DCF, Graham, EV/EBITDA, FCF yield) foram desligadas.", warn=True)

trend = badge("▲ acima da MM200", "ok") if tech["price"] > tech["sma200"] else badge("▼ abaixo da MM200", "bad")
theme.cards([
    card("Preço", num(tech["price"]), f"12m {pct(b['retornos']['retorno_12m'])}", trend),
    card("P/L futuro", num(f.get("fwd_pe"), 1), f"atual {num(f.get('pe'), 1)}"),
    card("ROE", pct(f.get("roe"), 0, sign=False), f"margem op. {pct(f.get('op_margin'), 0, sign=False)}"),
    card("Crescimento receita", pct(f.get("rev_growth"), 0), f"lucro {pct(f.get('eps_growth'), 0)}"),
    card("Dívida / patrimônio", num(f.get("debt_equity"), 0), "em %, segundo o Yahoo"),
    card("Piotroski", f"{b['piotroski']['pontos']}/{b['piotroski']['de']}" if b["piotroski"]["de"] else "—",
         "saúde financeira (9 = máx.)"),
    card("Alvo médio analistas", num(f.get("target_mean")), f"{f.get('n_analysts') or 0} analistas"),
    card("RSI 14 dias", num(tech["rsi14"], 0), "> 70 sobrecomprado · < 30 sobrevendido"),
])

t_chart, t_health, t_val, t_ai = st.tabs(["Gráfico", "Saúde financeira", "Valuation", "Análise com IA"])

with t_chart:
    st.plotly_chart(charts.price_chart(close, ticker), width="stretch")
    theme.note(f"MM50 {num(tech['sma50'])} · MM200 {num(tech['sma200'])} · "
               f"preço {pct(tech['price'] / tech['sma200'] - 1)} vs MM200 · "
               f"Bollinger {num(tech['bb_lower'])}–{num(tech['bb_upper'])} · RSI semanal {num(tech['rsi14_w'], 0)}")

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
