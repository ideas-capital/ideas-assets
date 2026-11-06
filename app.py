"""IDEAS CAPITAL assets — terminal pessoal de investimentos no exterior.

Rodar:  streamlit run app.py
Telas em paginas/; cálculos em pwass/engine/; dados em pwass/data/; IA em pwass/ai/;
visual em pwass/ui/. Configurações editáveis em config/*.yaml.
"""
import datetime as dt
from pathlib import Path

import streamlit as st

from pwass.engine import mercado
from pwass.ui import cache, components, settings, theme

st.set_page_config(page_title="IDEAS CAPITAL assets", page_icon=":material/candlestick_chart:",
                   layout="wide", initial_sidebar_state="auto")
theme.inject()
ROOT = Path(__file__).parent

# Menu: (arquivo, título, ícone). A primeira página é a inicial. Páginas novas do redesign entram aqui.
MENU = {
    "Visão geral": [
        ("paginas/terminal.py", "Painel", ":material/candlestick_chart:"),
        ("paginas/radar_ativos.py", "Radar de mercado", ":material/radar:"),
    ],
    "Análise": [
        ("paginas/ativo.py", "Ativo", ":material/query_stats:"),
        ("paginas/scanner.py", "Scanner", ":material/manage_search:"),
        ("paginas/radar.py", "Zonas de entrada", ":material/my_location:"),
    ],
    "Estratégias": [
        ("paginas/laboratorio.py", "Laboratório de swing", ":material/science:"),
        ("paginas/carteiras.py", "Carteiras do Núcleo", ":material/account_balance:"),
    ],
    "Inteligência": [("paginas/analista.py", "Analista IA", ":material/smart_toy:")],
    "Sistema": [("paginas/guia.py", "Guia e rotina", ":material/menu_book:")],
}
pages = {sec: [st.Page(f, title=t, icon=i, default=(f == "paginas/terminal.py")) for f, t, i in items]
         for sec, items in MENU.items()}
# Página de checagem visual do Design System: fora do menu, acessível em /componentes.
hidden = st.Page("paginas/_componentes.py", title="Componentes", url_path="componentes")
nav = st.navigation({**pages, "_": [hidden]}, position="hidden")


def _market_status_html() -> str:
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for nome, (aberto, txt) in (("NYSE", mercado.status_nyse(now)), ("B3", mercado.status_b3(now))):
        cor = "var(--up)" if aberto else "var(--text-muted)"
        rows.append(f'<span style="color:{cor}">●</span> {nome}: {txt}')
    return ('<div class="ds-src">' + "<br>".join(rows) +
            '<br>Calculado por calendário e horário (sem véspera de feriado).</div><div style="height:12px"></div>')


with st.sidebar:
    if (ROOT / "assets" / "logo.svg").exists():
        st.logo(str(ROOT / "assets" / "logo.svg"))
    else:  # sem assets/logo.svg: mantém a marca "IC" (pendência registrada em PENDENCIAS.md)
        st.markdown('<div class="ic-brand"><span class="logo">IC</span><span class="name">IDEAS CAPITAL</span>'
                    '<span class="sub">assets</span></div>', unsafe_allow_html=True)
    for sec, lst in pages.items():
        st.markdown(f'<div class="ic-sec">{sec}</div>', unsafe_allow_html=True)
        for p in lst:
            st.page_link(p)

    # Estratégia ativa do laboratório: só aparece onde é usada (Painel).
    if nav.title == "Painel":
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
    st.markdown(_market_status_html(), unsafe_allow_html=True)
    st.session_state.setdefault("ia_alertas", True)
    st.toggle(":material/notifications_active: Ativar IA & Alertas", key="ia_alertas")
    st.markdown('<div class="ds-src">Tema: menu <b>⋮</b> no topo → Settings → Theme (Light / Dark / Sistema).</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="ic-sec">Configurações</div>', unsafe_allow_html=True)
    settings.sidebar()


def _data_asof() -> str | None:
    """Data do último fechamento de referência (SPY, diário). None se a fonte falhar."""
    try:
        last = cache.history("SPY", "1mo").dropna().index[-1]
        return f"{last:%d/%m/%Y} (fechamento SPY, Yahoo Finance)"
    except Exception:  # noqa: BLE001
        return None


components.topbar(data_asof=_data_asof())
nav.run()
theme.footer()
