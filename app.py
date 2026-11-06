"""IDEAS CAPITAL assets — terminal pessoal de investimentos no exterior.

Rodar:  streamlit run app.py
Telas em paginas/; cálculos em pwass/engine/; dados em pwass/data/; IA em pwass/ai/;
visual em pwass/ui/. Configurações editáveis em config/*.yaml.
"""
import streamlit as st

from pwass.ui import cache, settings, theme

st.set_page_config(page_title="IDEAS CAPITAL assets", page_icon=":material/candlestick_chart:",
                   layout="wide", initial_sidebar_state="expanded")
theme.apply_theme()
theme.inject()

# Menu: (arquivo, título, ícone). A primeira página de "Acompanhar" é a inicial.
MENU = {
    "Acompanhar": [
        ("paginas/terminal.py", "Mercado hoje", ":material/candlestick_chart:"),
        ("paginas/radar_ativos.py", "Radar de ativos", ":material/radar:"),
        ("paginas/estrategias.py", "Estratégias e carteiras", ":material/explore:"),
    ],
    "Analisar": [
        ("paginas/scanner.py", "Scanner de ações", ":material/manage_search:"),
        ("paginas/ativo.py", "Raio-X do ativo", ":material/query_stats:"),
        ("paginas/radar.py", "Zonas de entrada", ":material/my_location:"),
    ],
    "Inteligência artificial": [("paginas/analista.py", "Analista IA", ":material/smart_toy:")],
    "Aprender": [("paginas/guia.py", "Guia e rotina", ":material/menu_book:")],
}
pages = {sec: [st.Page(f, title=t, icon=i, default=(f == "paginas/terminal.py")) for f, t, i in items]
         for sec, items in MENU.items()}
nav = st.navigation(pages, position="hidden")

with st.sidebar:
    # ---- Marca (troque o "IC" por um logo: st.image("assets/logo.png") no lugar do bloco abaixo)
    st.markdown('<div class="ic-brand"><span class="logo">IC</span><span class="name">IDEAS CAPITAL</span>'
                '<span class="sub">assets</span></div>', unsafe_allow_html=True)
    for sec, lst in pages.items():
        st.markdown(f'<div class="ic-sec">{sec}</div>', unsafe_allow_html=True)
        for p in lst:
            st.page_link(p)

    # ---- Estratégia ativa do laboratório de swing (filtra o Terminal)
    sw = cache.config("swing")
    st.markdown('<div class="ic-sec">Estratégia do algoritmo</div>', unsafe_allow_html=True)
    st.session_state.setdefault("estrategia_swing", sw.get("padrao", "pullback"))
    for sid, d in sw["estrategias"].items():
        active = st.session_state["estrategia_swing"] == sid
        if st.button(d["curto"], key=f"sw_{sid}", type="primary" if active else "secondary", width="stretch"):
            st.session_state["estrategia_swing"] = sid
            st.session_state.pop("term_tk", None)  # gráfico volta para o sinal da nova estratégia
            st.rerun()

    st.divider()
    st.session_state.setdefault("ia_alertas", True)
    st.toggle(":material/notifications_active: Ativar IA & Alertas", key="ia_alertas")
    dark = st.toggle(":material/dark_mode: Tema escuro", value=theme.mode() == "dark")
    if dark != (theme.mode() == "dark"):
        theme.set_mode("dark" if dark else "light")
        st.rerun()
    st.markdown('<div class="ic-sec">Configurações</div>', unsafe_allow_html=True)
    settings.sidebar()

nav.run()
theme.footer()
