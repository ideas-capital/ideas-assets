"""Alertas e watchlist: listas de acompanhamento, alertas configuráveis e o que disparou agora.

Dados do usuário ficam no store (pwass/store.py). A verificação automática roda no GitHub Actions
(.github/workflows/alertas.yml) e avisa por Telegram se houver credenciais; sem elas, os alertas
aparecem aqui e na topbar.
"""
import pandas as pd
import streamlit as st

from pwass import store as _store
from pwass.engine import alertas as AL, indicators, swing as S
from pwass.ui import cache, components as ds, dados, theme

sw = cache.config("swing")
st_ = cache.store()
ds.page_header("Alertas e watchlist", "Acompanhe listas de ativos e seja avisado quando uma condição acontecer.",
               source="Yahoo Finance (diário)", asof="avaliado no último fechamento")
st.caption(f"Armazenamento: **{st_.backend}**" + (" — arquivos locais: somem se o app reiniciar na nuvem (configure o Supabase para guardar de forma permanente)."
                                                  if st_.backend == "local" else " — dados persistentes."))

t_wl, t_al = st.tabs(["Watchlists", "Alertas"])

# ------------------------------------------------------------------ Watchlists
with t_wl:
    listas = dados.listas()
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    nome_novo = c2.text_input("Nova lista", placeholder="Ex.: Tecnologia", key="wl_novo")
    if c2.button("Criar lista", disabled=not nome_novo.strip(), key="wl_criar"):
        dados.nova_lista(nome_novo)
        st.rerun()
    if not listas:
        ds.empty_state("Nenhuma watchlist ainda", "Crie uma lista ao lado ou favorite um ativo na página Ativo (★).")
    else:
        ids = [d["id"] for d in listas]
        sel = c1.selectbox("Lista", ids, format_func=lambda i: next(d["nome"] for d in listas if d["id"] == i), key="wl_sel")
        lst = next(d for d in listas if d["id"] == sel)
        a1, a2 = st.columns([3, 2], vertical_alignment="bottom")
        novo_tk = a1.text_input("Adicionar ticker", placeholder="NVDA, PETR4.SA, BTC-USD", key="wl_tk").strip().upper()
        if a2.button("Adicionar", disabled=not novo_tk, key="wl_add"):
            try:
                ok = bool(cache.ohlcv((novo_tk,), "1y"))
            except Exception:  # noqa: BLE001
                ok = False
            if not ok:
                st.error(f"{novo_tk}: o Yahoo não retornou cotações. Confira o ticker (B3 usa .SA).")
            else:
                dados.salvar_lista(sel, lst["nome"], lst["tickers"] + [novo_tk])
                st.rerun()
        if lst["tickers"]:
            with st.spinner("Carregando cotações..."):
                data = cache.ohlcv(tuple(lst["tickers"]), "2y")
            sid = st.session_state.get("estrategia_swing", sw.get("padrao"))
            rows = []
            for t in lst["tickers"]:
                d = data.get(t)
                if d is None or len(d) < 60:
                    rows.append({"Ticker": t, "Último": None, "Dia": None, "1 mês": None, "RSI 14": None, "vs MM200": None, "Sinal": "sem dados"})
                    continue
                c = d["Close"]
                sig = S.signals(d, sid, sw["estrategias"][sid]).iloc[-1] if len(d) >= 260 else None
                rows.append({"Ticker": t, "Último": float(c.iloc[-1]), "Dia": float(c.iloc[-1] / c.iloc[-2] - 1),
                             "1 mês": float(c.iloc[-1] / c.iloc[-22] - 1) if len(c) > 22 else None,
                             "RSI 14": float(indicators.rsi(c).iloc[-1]),
                             "vs MM200": float(c.iloc[-1] / indicators.sma(c, 200).iloc[-1] - 1) if len(c) > 200 else None,
                             "Sinal": ("COMPRA" if sig["entry"] else "PERTO" if sig["near"] else "SAIR" if sig["exit"] else "—") if sig is not None else "histórico curto"})
            ds.chips([f"Sinal da estratégia: {sw['estrategias'][sid]['curto']}"])
            ds.data_table(pd.DataFrame(rows), key="wl_tbl", on_select_open_asset="Ticker", export_name=f"watchlist_{lst['nome']}",
                          source="Yahoo Finance (diário) · sinal calculado pelo app",
                          column_config={"Último": st.column_config.NumberColumn(format="%.2f"), "Dia": st.column_config.NumberColumn(format="percent"),
                                         "1 mês": st.column_config.NumberColumn(format="percent"), "RSI 14": st.column_config.NumberColumn(format="%.0f"),
                                         "vs MM200": st.column_config.NumberColumn(format="percent")})
            r1, r2 = st.columns([3, 2], vertical_alignment="bottom")
            rem = r1.multiselect("Remover da lista", lst["tickers"], key="wl_rem")
            if r2.button("Remover selecionados", disabled=not rem, key="wl_rm"):
                dados.salvar_lista(sel, lst["nome"], [t for t in lst["tickers"] if t not in rem])
                st.rerun()
        else:
            ds.empty_state("Lista vazia", "Adicione tickers acima.")
        if st.button("Apagar esta lista", key="wl_del"):
            st_.delete("watchlists", sel)
            st.rerun()

# ------------------------------------------------------------------ Alertas
with t_al:
    lista = dados.alertas()
    st.markdown("#### Disparados agora")
    hits = dados.disparados(lista)
    if not lista:
        ds.empty_state("Nenhum alerta configurado", "Crie um abaixo ou pela página Ativo (botão Criar alerta).")
    elif not hits:
        ds.empty_state("Nada disparou no último fechamento", "Os alertas ativos foram avaliados e nenhuma condição ocorreu.")
    for h in hits:
        st.markdown(f"{ds.origin_tag('calculado')} {theme.esc(h['mensagem'])}", unsafe_allow_html=True)
    if hits:
        st.markdown(ds.source_note("Calculado pelo app", "último fechamento diário do Yahoo Finance"), unsafe_allow_html=True)

    st.markdown("#### Criar alerta")
    universo = sorted(set(ds.universe_options()) | {t for w in dados.listas() for t in w["tickers"]})
    tk = st.selectbox("Ativo", universo, index=None, placeholder="Escolha ou digite um ticker", accept_new_options=True, key="al_tk")
    if tk:
        dados.formulario_alerta(str(tk).strip().upper(), "al_novo", sw)

    st.markdown("#### Meus alertas")
    for a in lista:
        k1, k2, k3, k4 = st.columns([1.2, 4, 1.2, 1], vertical_alignment="center")
        k1.markdown(f"**{a['ticker']}**")
        k2.markdown(f"{AL.TIPOS[a['tipo']]}: {AL.descrever(a)}")
        ligado = k3.toggle("Ativo", value=a.get("ativo", True), key=f"al_on_{a['id']}")
        if ligado != a.get("ativo", True):
            st_.put("alertas", a["id"], {**a, "ativo": ligado})
            st.rerun()
        if k4.button("", icon=":material/delete:", key=f"al_del_{a['id']}", help="Apagar alerta"):
            st_.delete("alertas", a["id"])
            st.rerun()
    st.caption("Aviso por Telegram: configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID (e SUPABASE_URL/KEY) nos secrets do GitHub; "
               "o workflow alertas.yml roda em dias úteis às 19h45 (Brasília). Sem isso, os alertas aparecem só no app.")
