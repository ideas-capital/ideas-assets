"""Analista IA: envie relatórios, prints de gráfico, filings da SEC ou teses de terceiros."""
import streamlit as st

from pwass.ai import documents, openrouter, prompts
from pwass.ui import cache, context, settings, theme

theme.header("Analista IA",
             "Importe um relatório, um print de gráfico ou um filing da SEC. O texto é extraído aqui no app "
             "(custo zero) e só então vai para o modelo que você escolher.")

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


tab_doc, tab_img, tab_sec, tab_claim = st.tabs(
    ["📄 Relatório / documento", "🖼️ Gráfico (imagem)", "🏛️ Filings da SEC", "🔍 Auditar tese de terceiro"])

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
