"""Visual do IDEAS CAPITAL assets: tema claro/escuro, CSS e componentes HTML.

O tema é trocado em tempo real: os tokens abaixo alimentam (1) o tema nativo do
Streamlit (tabelas, campos, botões) e (2) as variáveis CSS dos componentes
próprios (cartões, ticker, tabelas com selos). App de uso pessoal: a troca vale
para o servidor inteiro, o que não é problema com um único usuário.
"""
from __future__ import annotations

import html as _html
import math

import streamlit as st

TOKENS = {
    "dark": {"bg": "#0B0E14", "panel": "#121620", "panel2": "#171C28", "border": "#232A38",
             "text": "#D1D4DC", "muted": "#8A93A6", "up": "#26A69A", "down": "#EF5350",
             "accent": "#2962FF", "accent2": "#22D3EE", "warn": "#F0B90B", "grid": "#1A2030"},
    "light": {"bg": "#F5F6F9", "panel": "#FFFFFF", "panel2": "#F0F2F7", "border": "#E0E3EB",
              "text": "#131722", "muted": "#6A7187", "up": "#089981", "down": "#F23645",
              "accent": "#2962FF", "accent2": "#0891B2", "warn": "#B7791F", "grid": "#EEF0F4"},
}


def mode() -> str:
    """Tema atual: o da sessão ou, na primeira carga, o que o servidor já está usando."""
    if "tema" not in st.session_state:
        try:
            st.session_state["tema"] = "light" if st._config.get_option("theme.base") == "light" else "dark"
        except Exception:  # noqa: BLE001
            st.session_state["tema"] = "dark"
    return st.session_state["tema"]


def tokens() -> dict:
    return TOKENS[mode()]


def apply_theme() -> None:
    """Aplica o tema nativo do Streamlit para o modo atual."""
    t = tokens()
    opts = {"base": mode(), "backgroundColor": t["bg"], "secondaryBackgroundColor": t["panel2"],
            "textColor": t["text"], "primaryColor": t["accent"]}
    for k, v in opts.items():
        try:
            if st._config.get_option(f"theme.{k}") != v:
                st._config.set_option(f"theme.{k}", v)
        except Exception:  # noqa: BLE001 — opção inexistente nesta versão
            pass


def set_mode(new: str) -> None:
    st.session_state["tema"] = new
    apply_theme()


def inject() -> None:
    t = tokens()
    st.markdown(f"""
<style>
:root {{--bg:{t['bg']};--panel:{t['panel']};--panel2:{t['panel2']};--border:{t['border']};--text:{t['text']};
--muted:{t['muted']};--up:{t['up']};--down:{t['down']};--accent:{t['accent']};--accent2:{t['accent2']};--warn:{t['warn']};}}
.stApp {{background:var(--bg);}}
[data-testid="stSidebar"] {{background:var(--panel);border-right:1px solid var(--border);}}
[data-testid="stHeader"] {{background:transparent;}}
.block-container {{padding-top:1.1rem;padding-bottom:2.5rem;max-width:1500px;}}
h1,h2,h3,h4 {{letter-spacing:-.01em;}}
.pw-head h1 {{font-size:1.6rem;margin:0 0 .1rem 0;}}
.pw-head p {{color:var(--muted);margin:0 0 1rem 0;font-size:.95rem;}}
.pw-card {{border:1px solid var(--border);border-radius:10px;padding:11px 13px;background:var(--panel);height:100%;margin-bottom:.6rem;}}
.pw-card .t {{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;}}
.pw-card .v {{font-size:1.3rem;font-weight:650;margin:.1rem 0 .15rem 0;color:var(--text);}}
.pw-card .c {{font-size:.8rem;color:var(--muted);}}
.pw-up {{color:var(--up);font-weight:600;}} .pw-down {{color:var(--down);font-weight:600;}}
.pw-badge {{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:700;
           white-space:nowrap;letter-spacing:.02em;}}
.pw-ok {{background:color-mix(in srgb,var(--up) 18%,transparent);color:var(--up);}}
.pw-bad {{background:color-mix(in srgb,var(--down) 16%,transparent);color:var(--down);}}
.pw-warn {{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn);}}
.pw-info {{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent);}}
.pw-mute {{background:color-mix(in srgb,var(--muted) 16%,transparent);color:var(--muted);}}
.pw-solid-ok {{background:var(--up);color:#fff;}} .pw-solid-bad {{background:var(--down);color:#fff;}}
.pw-note {{border-left:3px solid var(--accent);background:color-mix(in srgb,var(--accent) 7%,transparent);
          padding:9px 13px;border-radius:6px;margin:.4rem 0 1rem 0;font-size:.9rem;}}
.pw-note.warn {{border-color:var(--warn);background:color-mix(in srgb,var(--warn) 8%,transparent);}}
.pw-signal {{border:1px solid var(--border);border-radius:12px;padding:14px 16px;background:var(--panel);margin-bottom:1rem;}}
.pw-signal .big {{font-size:1.35rem;font-weight:700;}}
.pw-foot {{color:var(--muted);font-size:.75rem;margin-top:2rem;border-top:1px solid var(--border);padding-top:.7rem;}}
/* ---------- Terminal ---------- */
.ic-brand {{line-height:1;margin:.2rem 0 1.1rem 0;}}
.ic-brand .logo {{width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--accent2));
  display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:.85rem;margin-right:.55rem;vertical-align:middle;}}
.ic-brand .name {{font-weight:800;font-size:1.32rem;letter-spacing:.02em;color:var(--text);vertical-align:middle;}}
.ic-brand .sub {{display:block;color:var(--accent2);font-size:1.05rem;font-weight:500;margin:.05rem 0 0 2.6rem;}}
.ic-sec {{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:.9rem 0 .25rem 0;font-weight:600;}}
.ic-title {{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;margin:.1rem 0 .2rem 0;}}
.ic-title h2 {{margin:0;font-size:1.45rem;font-weight:800;letter-spacing:.02em;}}
.ic-pill {{border:1px solid var(--border);background:var(--panel);border-radius:999px;padding:3px 12px;font-size:.82rem;}}
.ic-ticker {{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:7px;margin:.4rem 0 .9rem 0;}}
.ic-tk {{background:var(--panel);border:1px solid var(--border);border-radius:9px;padding:8px 11px;}}
.ic-tk .row {{display:flex;justify-content:space-between;align-items:baseline;gap:6px;}}
.ic-tk .n {{font-weight:700;font-size:.82rem;}} .ic-tk .p {{font-size:.86rem;font-variant-numeric:tabular-nums;}}
.ic-tk svg {{width:100%;height:30px;display:block;margin-top:3px;}}
.ic-panel {{background:var(--panel);border:1px solid var(--border);border-radius:11px;padding:12px 14px;margin-bottom:.8rem;}}
.ic-panel .hd {{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;font-weight:700;margin-bottom:.45rem;}}
.ic-sig {{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;}}
.ic-sig .tk {{font-size:1.5rem;font-weight:800;}}
.ic-sig .lv {{font-size:.95rem;font-variant-numeric:tabular-nums;}}
.ic-kpis {{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:.2rem 0 .6rem 0;}}
.ic-kpi .l {{font-size:.72rem;color:var(--muted);}} .ic-kpi .v {{font-size:1.15rem;font-weight:700;font-variant-numeric:tabular-nums;}}
.ic-table {{width:100%;border-collapse:collapse;font-size:.83rem;}}
.ic-table th {{text-align:left;color:var(--muted);font-weight:600;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
  padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap;position:sticky;top:0;background:var(--panel);}}
.ic-table td {{padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap;}}
.ic-table td.r, .ic-table th.r {{text-align:right;font-variant-numeric:tabular-nums;}}
.ic-table td.w {{white-space:normal;min-width:220px;color:var(--muted);font-size:.78rem;}}
.ic-table tr:hover td {{background:color-mix(in srgb,var(--accent) 5%,transparent);}}
.ic-scroll {{max-height:560px;overflow:auto;border:1px solid var(--border);border-radius:10px;background:var(--panel);}}
.ic-alert {{padding:6px 0;border-bottom:1px solid var(--border);font-size:.85rem;}}
div[data-testid="stPopover"] button {{border-radius:8px;}}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers de formatação
def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def esc(s) -> str:
    return _html.escape(str(s))


def pct(x, digits: int = 1, sign: bool = True) -> str:
    if _isnan(x):
        return "—"
    return (f"{x * 100:+.{digits}f}%" if sign else f"{x * 100:.{digits}f}%").replace(".", ",")


def num(x, digits: int = 2, prefix: str = "") -> str:
    if _isnan(x):
        return "—"
    if isinstance(x, float) and math.isinf(x):
        return "∞"
    s = f"{x:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return prefix + s


def colored_pct(x, digits: int = 1) -> str:
    if _isnan(x):
        return "—"
    return f'<span class="{"pw-up" if x >= 0 else "pw-down"}">{pct(x, digits)}</span>'


def badge(text: str, kind: str = "info") -> str:
    return f'<span class="pw-badge pw-{kind}">{esc(text)}</span>'


# ------------------------------------------------------------------ componentes
def header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="pw-head"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def card(title: str, value: str, caption: str = "", badge_html: str = "") -> str:
    return (f'<div class="pw-card"><div class="t">{title}</div><div class="v">{value}</div>'
            f'<div class="c">{caption} {badge_html}</div></div>')


def cards(items: list[str], per_row: int = 4) -> None:
    for i in range(0, len(items), per_row):
        cols = st.columns(per_row)
        for col, h in zip(cols, items[i:i + per_row]):
            col.markdown(h, unsafe_allow_html=True)


def note(text: str, warn: bool = False) -> None:
    st.markdown(f'<div class="pw-note{" warn" if warn else ""}">{text}</div>', unsafe_allow_html=True)


def signal_box(title: str, big: str, body: str) -> None:
    st.markdown(f'<div class="pw-signal"><div style="color:var(--muted);font-size:.78rem">{title}</div>'
                f'<div class="big">{big}</div><div>{body}</div></div>', unsafe_allow_html=True)


VERDICT_KIND = {"Forte": "ok", "Aguardar": "info", "Neutro": "warn", "Evitar": "bad"}


def verdict_badge(v: str) -> str:
    kind = next((k for p, k in VERDICT_KIND.items() if v.startswith(p)), "info")
    return badge(v, kind)


def sparkline(values, color: str | None = None, w: int = 160, h: int = 30) -> str:
    """Mini gráfico SVG (linha + área) para o ticker."""
    v = [float(x) for x in values if not _isnan(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1
    pts = [(i * w / (len(v) - 1), h - 2 - (x - lo) / span * (h - 4)) for i, x in enumerate(v)]
    color = color or ("var(--up)" if v[-1] >= v[0] else "var(--down)")
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{h} " + line + f" {w},{h}"
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polygon points="{area}" '
            f'fill="{color}" opacity=".12"/><polyline points="{line}" fill="none" stroke="{color}" '
            f'stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>')


def table(headers: list[tuple[str, str]], rows: list[list[str]], scroll: bool = True) -> str:
    """Tabela HTML densa. headers = [(título, 'r' para alinhar à direita | 'w' texto longo | '')]."""
    th = "".join(f'<th class="{a}">{esc(h)}</th>' for h, a in headers)
    body = "".join("<tr>" + "".join(f'<td class="{a}">{c}</td>' for (_, a), c in zip(headers, r)) + "</tr>"
                   for r in rows)
    t = f'<table class="ic-table"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'
    return f'<div class="ic-scroll">{t}</div>' if scroll else t


def footer() -> None:
    st.markdown('<div class="pw-foot">IDEAS CAPITAL assets · ferramenta pessoal de Renan Cotta. Sinais gerados por '
                'regras e IA para apoiar a leitura do mercado; a decisão, o aporte e o risco são exclusivamente do '
                'usuário. Dados: Yahoo Finance, FRED, Banco Central, Tesouro e SEC — podem ter atraso ou erro.</div>',
                unsafe_allow_html=True)
