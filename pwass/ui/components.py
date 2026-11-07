"""Componentes do Design System v5. Cada um tem estados normal / carregando / vazio / erro.

Regras: cores só via tokens (CSS `var(--...)`), todo número com fonte e data (`source_note`),
dado ausente = "—" com motivo. Catálogo e exemplos: docs/redesign/DESIGN-SYSTEM.md e a página
oculta `paginas/_componentes.py` (abrir em /_componentes).

Exemplo:
    >>> page_header("Painel", "Mercado hoje", source="Yahoo Finance", asof="06/11/2026 18:05")
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from pwass.ui import cache, theme, tokens
from pwass.ui.theme import esc, money, num, pct

BRT = ZoneInfo("America/Sao_Paulo")
STATES = ("normal", "loading", "empty", "error")


def now_brt() -> str:
    return dt.datetime.now(BRT).strftime("%d/%m/%Y %H:%M BRT")


def _delta_html(x, digits: int = 1) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return '<span title="Dado indisponível">—</span>'
    return f'<span class="{"pw-up" if x >= 0 else "pw-down"}">{pct(x, digits)}</span>'


# ------------------------------------------------------------------ fonte / estados
def source_note(source: str, asof: str | None = None, freq: str | None = None) -> str:
    """Rodapé de fonte. source_note('Yahoo Finance', '06/11/2026 18:05 BRT', 'diário')."""
    parts = [f"Fonte: {esc(source)}"] + ([esc(asof)] if asof else []) + ([esc(freq)] if freq else [])
    return f'<div class="ds-src">{" · ".join(parts)}</div>'


def empty_state(title: str, reason: str = "", action: str = "") -> None:
    st.markdown(f'<div class="ds-empty"><b>{esc(title)}</b>{esc(reason)}'
                f'{"<br>" + esc(action) if action else ""}</div>', unsafe_allow_html=True)


def error_state(title: str, reason: str = "", action: str = "") -> None:
    st.markdown(f'<div class="ds-empty err" role="alert"><b>{esc(title)}</b>{esc(reason)}'
                f'{"<br>" + esc(action) if action else ""}</div>', unsafe_allow_html=True)


def loading_state(rows: int = 1) -> None:
    st.markdown('<div class="ds-skel" aria-busy="true"></div>' * rows, unsafe_allow_html=True)


def _guard(state: str, empty_msg: str = "Sem dados para mostrar.", error_msg: str = "") -> bool:
    """True se o componente deve parar de desenhar (estado diferente de 'normal')."""
    if state == "loading":
        loading_state()
    elif state == "empty":
        empty_state(empty_msg, "Dado indisponível na fonte ou filtro sem resultado.")
    elif state == "error":
        error_state("Não foi possível carregar", error_msg or "A fonte não respondeu.", "Tente novamente em instantes.")
    return state != "normal"


# ------------------------------------------------------------------ cabeçalhos
def page_header(title: str, subtitle: str = "", source: str = "", asof: str = "", actions: str = "") -> None:
    """Título (24 px), subtítulo e, à direita, fonte/atualização."""
    right = source_note(source, asof) if source else ""
    st.markdown(f'<div class="ds-hdr"><div><h1>{esc(title)}</h1>'
                f'<div class="sub">{esc(subtitle)}</div></div><div>{right}{actions}</div></div>', unsafe_allow_html=True)


def universe_options() -> dict[str, str]:
    """{ticker: 'TICKER — Nome (classe)'} do universo configurado (swing + universe + watchlist)."""
    opts: dict[str, str] = {}
    for classe, d in cache.config("swing").get("universo", {}).items():
        for tk, nome in d.items():
            opts[tk] = f"{tk} — {nome} ({classe})"
    for grupo, tks in cache.config("universe").get("grupos", {}).items():
        for tk in tks:
            opts.setdefault(tk, f"{tk} ({grupo})")
    for item in cache.config("watchlist").get("satellite", []) or []:
        opts.setdefault(item["ticker"], f"{item['ticker']} (watchlist)")
    return opts


def topbar(data_asof: str | None = None, delayed: bool = True, n_alerts: int | None = None) -> None:
    """Barra do topo: busca global, status dos dados e alertas.

    - Busca: universo configurado; ticker livre é aceito (sufixo .SA para B3) e validado na página Ativo.
    - Alertas: só aparece se `n_alerts` for informado (contagem real). Sem fonte de alertas, não mostra.
    - Dados: 'Dados de: <data/hora>' + aviso de atraso (Yahoo diário ≈ fechamento anterior).
    """
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    with c1:
        opts = universe_options()
        pick = st.selectbox("Buscar ativo", list(opts), index=None, placeholder="Buscar ativo (ticker ou nome)…",
                            format_func=lambda k: opts.get(k, k), accept_new_options=True,
                            label_visibility="collapsed", key="topbar_busca")
        if pick:
            tk = str(pick).strip().upper()
            st.session_state["ticker"] = tk
            st.session_state.pop("topbar_busca", None)
            st.query_params["t"] = tk
            st.switch_page("paginas/ativo.py")
    with c2:
        when = data_asof or "—"
        lag = " · cotações diárias (atraso até o último fechamento)" if delayed else ""
        al = ""
        if n_alerts is not None:
            al = f" · {n_alerts} alerta{'s' if n_alerts != 1 else ''}"
        st.markdown(f'<div class="ds-top"><span>Dados de: {esc(when)}{esc(lag)}{esc(al)}</span></div>',
                    unsafe_allow_html=True)


# ------------------------------------------------------------------ indicadores
def kpi(label: str, value: str, delta=None, spark: list[float] | None = None, source: str = "",
        state: str = "normal", digits: int = 1) -> str:
    """Cartão de KPI (HTML). `value` já formatado; `delta` fração (0.012 = +1,2%); `source` vai no tooltip."""
    if state != "normal":
        return '<div class="ds-kpi"><div class="l">{}</div><div class="v" title="Indisponível">—</div></div>'.format(esc(label))
    sp = theme.sparkline(spark) if spark and len(spark) > 1 else ""
    tip = f' title="{esc(source)}"' if source else ""
    return (f'<div class="ds-kpi"{tip}><div class="l">{esc(label)}</div><div class="v">{value}</div>'
            f'<div class="d">{_delta_html(delta, digits) if delta is not None else ""}</div>{sp}</div>')


def kpi_row(items: list[str]) -> None:
    cols = st.columns(len(items))
    for col, html_ in zip(cols, items):
        col.markdown(html_, unsafe_allow_html=True)


def ticker_strip(items: list[dict], state: str = "normal", source: str = "Yahoo Finance", asof: str = "") -> None:
    """Faixa de cotações. items = [{'nome','valor'(str),'var'(fração|None),'spark'(list|None)}]."""
    if _guard(state, "Nenhuma cotação configurada."):
        return
    cells = "".join(
        f'<div class="it"><div class="n">{esc(i["nome"])}</div><div class="p">{esc(i.get("valor", "—"))} '
        f'{_delta_html(i.get("var"))}</div>{theme.sparkline(i["spark"]) if i.get("spark") else ""}</div>'
        for i in items)
    st.markdown(f'<div class="ds-strip">{cells}</div>', unsafe_allow_html=True)
    st.markdown(source_note(source, asof), unsafe_allow_html=True)


def asset_header(ticker: str, name: str, market: str, klass: str, price, var, currency: str = "US$",
                 asof: str = "", favorite: bool | None = None, state: str = "normal") -> None:
    """Cabeçalho do ativo. `favorite` None = sem botão ★ (watchlist ainda não existe → não mostrar controle morto)."""
    if _guard(state, f"{ticker}: sem cotação."):
        return
    st.markdown(f'<div class="ds-asset"><span class="tk">{esc(ticker)}</span><span class="nm">{esc(name)}</span>'
                f'<span class="ds-tag">{esc(market)}</span><span class="ds-tag">{esc(klass)}</span>'
                f'<span class="px">{money(price, 2, currency)}</span>{_delta_html(var)}</div>'
                f'{source_note("Yahoo Finance", asof, "diário")}', unsafe_allow_html=True)


def badge(status: str) -> str:
    """Selo de status com semântica fixa: COMPRA, PERTO, EM POSIÇÃO, AGUARDAR, EVITAR, SAIR."""
    kind = tokens.BADGE_KIND.get(status.upper())
    if kind is None:
        raise ValueError(f"status desconhecido: {status!r}; use um de {sorted(tokens.BADGE_KIND)}")
    return theme.badge(status.upper(), kind)


ORIGEM = {"observado": ("ds-obs", "Observado (dado da fonte)"), "calculado": ("ds-calc", "Calculado pelo app"),
          "simulado": ("ds-sim", "Simulado / backtest"), "ia": ("ds-ia", "Interpretação da IA"),
          "real": ("ds-real", "Operação real (registrada por você)")}


def origin_tag(kind: str) -> str:
    """Rótulo de origem do número (§2.1-6): observado | calculado | simulado | ia | real."""
    cls, label = ORIGEM[kind]
    return f'<span class="ds-tag {cls}" title="{label}">{label.split(" (")[0]}</span>'


# ------------------------------------------------------------------ tabela e gráfico
def data_table(df: pd.DataFrame, *, column_config: dict | None = None, column_order: list[str] | None = None,
               on_select_open_asset: str | None = None, export_name: str | None = None, height: int | None = None,
               key: str, state: str = "normal", source: str = "", asof: str = "") -> pd.DataFrame | None:
    """Padrão global de tabela: st.dataframe + column_config, ordenação, scroll e exportação CSV.

    on_select_open_asset='Ticker' → clicar numa linha abre a página Ativo com aquele ticker.
    Retorna a linha selecionada (DataFrame) ou None.
    """
    if _guard(state) or df is None or df.empty:
        if state == "normal":
            empty_state("Nada para mostrar", "Nenhum resultado com os critérios atuais.")
        return None
    kw = dict(width="stretch", hide_index=True, column_config=column_config, column_order=column_order, key=key)
    if height:
        kw["height"] = height
    sel = None
    if on_select_open_asset:
        ev = st.dataframe(df, on_select="rerun", selection_mode="single-row", **kw)
        rows = ev.selection.rows if ev is not None else []
        if rows:
            sel = df.iloc[rows]
            st.session_state["ticker"] = str(sel.iloc[0][on_select_open_asset])
            st.switch_page("paginas/ativo.py")
    else:
        st.dataframe(df, **kw)
    if source:
        st.markdown(source_note(source, asof), unsafe_allow_html=True)
    if export_name:
        st.download_button("Exportar CSV", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name=f"{export_name}.csv", mime="text/csv", key=f"{key}_csv")
    return sel


def chart_container(title: str, source: str, asof: str = "", legend: str = "", state: str = "normal"):
    """Contêiner de gráfico: título, (controles dentro do `with`), legenda e fonte. Use: `with chart_container(...) as c:`."""
    box = st.container(border=True)
    with box:
        st.markdown(f"**{esc(title)}**")
        if _guard(state):
            return _Noop(box)
    return _Chart(box, legend, source, asof)


class _Noop:
    def __init__(self, box): self.box = box
    def __enter__(self): return self.box.__enter__()
    def __exit__(self, *a): return self.box.__exit__(*a)


class _Chart(_Noop):
    def __init__(self, box, legend, source, asof):
        super().__init__(box)
        self.legend, self.source, self.asof = legend, source, asof

    def __exit__(self, *a):
        if self.legend:
            st.markdown(f'<div class="ds-src">{esc(self.legend)}</div>', unsafe_allow_html=True)
        st.markdown(source_note(self.source, self.asof), unsafe_allow_html=True)
        return self.box.__exit__(*a)


def insight_card(observed: str, interpretation: str = "", limitation: str = "", origin: str = "calculado") -> None:
    """Observado → interpretação → limitação. `origin` rotula quem produziu a interpretação."""
    parts = [f'<div class="k">Observado</div>{observed}']
    if interpretation:
        parts.append(f'<div class="k">Interpretação {origin_tag(origin)}</div>{interpretation}')
    if limitation:
        parts.append(f'<div class="k">Limitação</div>{limitation}')
    st.markdown('<div class="ds-insight">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def chips(items: list[str]) -> None:
    """Critérios aplicados (filtros) sempre visíveis."""
    st.markdown("".join(f'<span class="ds-chip">{esc(i)}</span>' for i in items), unsafe_allow_html=True)
