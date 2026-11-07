"""Analista IA: envie relatórios, prints de gráfico, filings da SEC ou teses de terceiros."""
import datetime as dt
import math

import streamlit as st

from pwass.ai import documents, estruturada as E, openrouter, prompts
from pwass.engine import ativo as A, swing as S
from pwass.ui import cache, components as ds, context, settings, theme

ds.page_header("Analista IA",
               "Análise estruturada de um ativo a partir de números calculados pelo app, e leitura de documentos. "
               "Toda resposta da IA é interpretação — não dado.")

if not settings.any_ai():
    theme.note("Para usar esta tela, cole uma chave em ⚙️ Configurações: <b>OpenRouter</b> (todos os modelos, "
               "pago por uso) ou <b>Google AI Studio</b> (Gemini Flash grátis). Passo a passo em "
               "<b>Guia e rotina → IA: opções</b>.", warn=True)

MAX_CHARS = cache.config("ai").get("max_doc_chars", 400_000)


def cost_hint(model: str, chars: int) -> None:
    est = settings.estimate_cost(model, chars)
    tokens = chars // 4
    st.caption(f"≈ {tokens:,} tokens de entrada".replace(",", ".")
               + (f" · custo estimado US$ {est:.3f}" if est is not None else ""))


tab_est, tab_doc, tab_img, tab_sec, tab_claim = st.tabs(
    ["Análise estruturada", "Relatório / documento", "Gráfico (imagem)", "Filings da SEC", "Auditar tese de terceiro"])


def _limpa(d):
    return {k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v) for k, v in d.items()}


# ---------------------------------------------------------------- Análise estruturada
with tab_est:
    st.markdown(f'{ds.origin_tag("ia")} <span class="ds-src">A IA recebe <b>somente</b> o bloco de números abaixo (calculado pelo app, '
                "com data de referência) e responde em formato fixo. Níveis de preço, alvos e stops só podem ser os do bloco.</span>",
                unsafe_allow_html=True)
    tk_e = st.text_input("Ticker", value=st.session_state.get("ticker", "MSFT"), key="est_tk").strip().upper()
    q_e = st.text_input("Pergunta específica (opcional)", key="est_q")
    model_e = settings.model_picker("est_modelo")
    if tk_e and st.button("Montar dados e analisar", type="primary", key="est_go"):
        try:
            with st.spinner("Calculando os dados do ativo..."):
                b = context.asset_bundle(tk_e)
                ohl = cache.ohlcv((tk_e,), "10y").get(tk_e)
        except Exception as e:  # noqa: BLE001
            ds.error_state(f"Não consegui montar os dados de {tk_e}", str(e), "Confira o ticker.")
            st.stop()
        sw = cache.config("swing")
        risk = sw["risco"]
        f = b["_fund_raw"]
        klass = A.classe(f.get("quote_type"), tk_e)
        estr, plano = {}, None
        if ohl is not None and len(ohl) >= 260:
            for k, d in sw["estrategias"].items():
                bt = S.backtest(ohl, k, d, risk["custo_por_lado"], risk["multiplo_atr_stop"])
                stt = S.stats(bt, S.periods_per_year(ohl.index))
                estr[d["nome"]] = {"situacao_hoje": S.status_today(ohl, k, d, bt)[0], "historico": S.quality(stt),
                                   "backtest_simulado": _limpa(stt)}
            plano = _limpa(S.plan(ohl, risk))
        data_ref = f"{b['_close'].dropna().index[-1]:%d/%m/%Y}"
        fund = context.for_ai(b)
        payload = E.montar_payload(ticker=tk_e, classe=klass, moeda=f.get("currency") or "?", data_ref=data_ref,
                                   tecnica=b["tecnica"], estrategias=estr, plano=plano, riscos=risk,
                                   fundamentos={k: fund[k] for k in ("fundamentos", "piotroski", "dcf")}, retornos=b["retornos"])
        msgs = [{"role": "system", "content": prompts.SYSTEM + "\n\n" + E.SYSTEM_EXTRA},
                {"role": "user", "content": f"Analise {tk_e}." + (f" Pergunta: {q_e}" if q_e else "")
                 + "\n\nDADOS (JSON, referência " + data_ref + "):\n" + E.para_prompt(payload)}]
        res = settings.ask_ai(msgs, model=model_e, temperature=0.2)
        if res:
            agora = dt.datetime.now(ds.BRT)
            try:
                cache.store().put("analises_ia", f"{tk_e}-{agora:%Y%m%d%H%M%S}",
                                  {"ticker": tk_e, "quando": agora.strftime("%d/%m/%Y %H:%M BRT"), "quando_iso": agora.isoformat(),
                                   "data_ref": data_ref, "modelo": res.model, "custo": res.cost_usd, "texto": res.text, "payload": payload})
            except Exception as e_:  # noqa: BLE001
                st.warning(f"Análise gerada, mas não consegui salvar: {e_}")
    try:
        hist = sorted(cache.store().list("analises_ia"), key=lambda d: d.get("quando_iso", ""), reverse=True)
    except Exception as e_:  # noqa: BLE001
        hist = []
        st.caption(f"Histórico de análises indisponível: {e_}")
    if hist:
        a_ = hist[0]
        v = E.validar(a_["texto"], a_["payload"])
        st.markdown(f"#### {a_['ticker']} · dados de {a_['data_ref']}")
        if v["faltando"]:
            ds.error_state("Resposta fora do formato fixo", "Seções ausentes: " + ", ".join(v["faltando"]), "Rode de novo ou troque de modelo.")
        if v["percentual_de_confianca"]:
            theme.note("A resposta usa percentual de confiança, que não é calibrado. Ignore esse número.", warn=True)
        if v["numeros_fora"]:
            theme.note("Números citados em <b>Dados observados</b> que não estão nos dados enviados: "
                       + ", ".join(theme.num(n, 2) for n in v["numeros_fora"][:8]) + ". Confira antes de confiar.", warn=True)
        for nome, corpo in v["secoes"].items():
            with st.container(border=True):
                tag = {"Dados observados": "observado", "Decisão": "ia", "Interpretação": "ia", "Hipóteses": "ia",
                       "Riscos e limitações": "ia"}[nome]
                st.markdown(f"**{nome}** {ds.origin_tag(tag)}", unsafe_allow_html=True)
                st.markdown(corpo)
        custo = f" · custo US$ {a_['custo']:.4f}" if a_["custo"] is not None else ""
        st.markdown(ds.source_note(f"IA ({a_['modelo']}){custo}", f"gerada em {a_['quando']}", f"dados de {a_['data_ref']}"),
                    unsafe_allow_html=True)
        st.download_button("Baixar análise (.md)", a_["texto"], file_name=f"analise-{a_['ticker']}.md", mime="text/markdown", key="est_dl")
        with st.expander("Dados enviados à IA (JSON)"):
            st.json(a_["payload"], expanded=False)
        if len(hist) > 1:
            with st.expander(f"Análises anteriores salvas ({len(hist) - 1})"):
                for h in hist[1:]:
                    st.markdown(f"**{h['ticker']}** · {h['quando']} · {h['modelo']}")
                    st.markdown(h["texto"])
        _bk = cache.store().backend
        st.caption(f"Análises salvas no armazenamento **{_bk}**" + (" (arquivos locais: somem se o app reiniciar na nuvem)." if _bk == "local" else "."))

# ---------------------------------------------------------------- Documento
with tab_doc:
    up = st.file_uploader("PDF, HTML, TXT, CSV ou Excel", type=["pdf", "html", "htm", "txt", "md", "csv", "xlsx"])
    focus = st.text_input("Foco (opcional)", placeholder="Ex.: margens do segmento de nuvem e guidance")
    model = settings.model_picker("doc_modelo")
    if up:
        text = documents.extract(up.getvalue(), up.name)
        text, cut = documents.truncate(text, MAX_CHARS)
        st.caption(f"{len(text):,} caracteres extraídos".replace(",", ".") + (" (cortado)" if cut else ""))
        cost_hint(model, len(text))
        with st.expander("Ver texto extraído"):
            st.text(text[:5000] + ("..." if len(text) > 5000 else ""))
        if st.button("Analisar documento", type="primary"):
            r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                 {"role": "user", "content": prompts.summarize_report(text, focus)}], model=model)
            if r:
                settings.show_result(r, f"analise-{up.name}.md")

# ---------------------------------------------------------------- Imagem
with tab_img:
    theme.note("Envie um print do TradingView, Finviz ou de qualquer gráfico. Use um modelo com visão "
               "(Claude, Gemini, GPT ou Gemma).")
    imgs = st.file_uploader("Imagens", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    ctx = st.text_input("Contexto (opcional)", placeholder="Ex.: NVDA diário; estou avaliando entrada entre 180 e 195")
    model_i = settings.model_picker("img_modelo")
    if imgs:
        st.image([i.getvalue() for i in imgs], width=320)
        if st.button("Analisar gráfico", type="primary"):
            urls = [documents.image_data_url(i.getvalue(), i.type) for i in imgs]
            r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                 openrouter.user_message(prompts.analyze_chart(ctx), urls)], model=model_i)
            if r:
                settings.show_result(r, "analise-grafico.md")

# ---------------------------------------------------------------- SEC
with tab_sec:
    theme.note("Relatórios oficiais, gratuitos: <b>10-K/20-F</b> (anual), <b>10-Q/6-K</b> (trimestral), "
               "<b>8-K</b> (fatos relevantes — o release de resultados costuma vir como anexo 99.1).")
    tk = st.text_input("Ticker listado nos EUA", value=st.session_state.get("ticker", "MSFT")).strip().upper()
    if tk:
        try:
            fl = cache.sec_filings(tk, settings.sec_user_agent())
        except Exception as e:  # noqa: BLE001
            st.error(f"SEC: {e}")
            fl = None
        if fl is not None and not fl.empty:
            st.dataframe(fl, width="stretch", hide_index=True,
                         column_config={"url": st.column_config.LinkColumn("Documento", display_text="abrir")})
            labels = [f"{r['Tipo']} · {r['Entregue em']}" for _, r in fl.iterrows()]
            i = st.selectbox("Escolha o relatório", range(len(fl)), format_func=lambda k: labels[k])
            focus_s = st.text_input("Foco (opcional)", key="sec_foco",
                                    placeholder="Ex.: fatores de risco novos e mudanças no guidance")
            model_s = settings.model_picker("sec_modelo", default_preset="profundo")
            if st.button("Ler e analisar com IA", type="primary"):
                with st.spinner("Baixando da SEC..."):
                    txt = cache.sec_text(fl.iloc[i]["url"], settings.sec_user_agent())
                txt, cut = documents.truncate(txt, MAX_CHARS)
                cost_hint(model_s, len(txt))
                r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                                     {"role": "user", "content": prompts.summarize_report(txt, focus_s)}],
                                    model=model_s)
                if r:
                    settings.show_result(r, f"{tk}-{fl.iloc[i]['Tipo']}.md")

# ---------------------------------------------------------------- Tese de terceiro
with tab_claim:
    theme.note("Viu um post tipo <i>“Compre X entre $180 e $195”</i>? Cole aqui. Se informar o ticker, a IA "
               "recebe também os fundamentos, a técnica, o Piotroski e o DCF reverso do ativo.")
    claim = st.text_area("Afirmação ou previsão", placeholder="Ex.: NVDA é compra forte entre 180 e 195, alvo 260 em 6 meses.")
    tk2 = st.text_input("Ticker relacionado (opcional)", key="claim_tk").strip().upper()
    model_c = settings.model_picker("claim_modelo")
    if st.button("Auditar afirmação", type="primary", disabled=not claim):
        ctx_txt = "Nenhum dado de mercado anexado."
        if tk2:
            try:
                ctx_txt = prompts._blob(context.for_ai(context.asset_bundle(tk2)))
            except Exception as e:  # noqa: BLE001
                st.warning(f"Sem dados para {tk2}: {e}")
        r = settings.ask_ai([{"role": "system", "content": prompts.SYSTEM},
                             {"role": "user", "content": prompts.audit_claim(claim, ctx_txt)}], model=model_c)
        if r:
            settings.show_result(r, "auditoria-tese.md")
