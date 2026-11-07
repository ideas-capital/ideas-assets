"""Renderizadores do relatório: Excel (openpyxl) e PDF (fpdf2 + matplotlib). Sem Streamlit, sem rede.

Entrada: o dict de `pwass.engine.relatorio.montar`. Os dois formatos leem o MESMO dict, então os números
coincidem com a tela. O PDF usa fontes padrão (latin-1): acentos do português funcionam; símbolos fora do
latin-1 são trocados por equivalentes simples (`_l1`).
"""
from __future__ import annotations

import io
import math

import pandas as pd

from pwass.ui import tokens

PRIMARY = tokens.THEMES["light"]["primary"]
PCT_COLS = ("Taxa de acerto", "Resultado médio", "Ganho médio", "Perda média", "Exposição média", "a.a. regra (média dos ativos)",
            "a.a. buy & hold (média dos ativos)", "Pior queda (média dos ativos)", "Dia", "Acerto", "CAGR", "CAGR B&H", "Máx. queda")
OPP_COLS = ["Ticker", "Ativo", "Último", "Dia", "Situação", "Histórico", "Operações", "Acerto", "Profit factor", "Resultado médio"]


def _isnan(x) -> bool:
    return x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def br(x, d: int = 2) -> str:
    """Número em pt-BR; ausente → '—'."""
    if _isnan(x):
        return "—"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_pct(x, d: int = 1) -> str:
    return "—" if _isnan(x) else br(x * 100, d) + "%"


def _celula(col: str, v) -> str:
    if isinstance(v, (list, tuple)):
        return ", ".join(map(str, v))
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if col in PCT_COLS:
            return br_pct(v)
        if col in ("Operações", "Ativos"):
            return str(int(v))
        return br(v, 2)
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def _l1(t: str) -> str:
    """Texto seguro para fonte latin-1 do PDF."""
    t = (t.replace("—", "-").replace("–", "-").replace("≥", ">=").replace("≤", "<=").replace("×", "x").replace("→", "->")
          .replace("●", "*").replace("’", "'").replace("“", '"').replace("”", '"').replace("▲", "alta").replace("▼", "baixa"))
    return t.encode("latin-1", "replace").decode("latin-1")


def opp_tabela(rel: dict) -> pd.DataFrame:
    """Oportunidades do relatório: só situações com ação (COMPRA, PERTO, EM POSIÇÃO, SAIR), colunas fixas."""
    df = rel["oportunidades"]
    return df[[c for c in OPP_COLS if c in df.columns]]


def linhas_resumo(rel: dict) -> list[tuple[str, str]]:
    r = rel["resumo"]
    return [("Regime de mercado", f"{r['regime']} ({r['classes_acima']} de {r['classes_total']} classes acima da MM200)"),
            ("Amplitude (ativos acima da MM200)", f"{br_pct(r['amplitude_pct'], 0)} ({r['amplitude_acima']} de {r['amplitude_n']})"),
            ("VIX", f"{br(r['vix'], 1)} (percentil {br_pct(r['vix_percentil'], 0)} em 2 anos)"),
            ("Estratégia ativa", rel["meta"]["estrategia_ativa"]),
            ("Setups de compra hoje", str(r["setups_de_compra"])),
            ("Novos setups no último pregão", ", ".join(r["novos_setups"]) or "nenhum"),
            ("Cruzaram a MM200 para cima", ", ".join(r["cruzaram_mm200_acima"]) or "nenhum"),
            ("Cruzaram a MM200 para baixo", ", ".join(r["cruzaram_mm200_abaixo"]) or "nenhum"),
            ("Dados de", rel["meta"]["data_dados"]), ("Gerado em", rel["meta"]["gerado_em"])]


# ------------------------------------------------------------------ Excel
def para_excel(rel: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    head_fill, head_font = PatternFill("solid", fgColor=PRIMARY.lstrip("#")), Font(bold=True, color="FFFFFF")

    def aba(nome: str, df: pd.DataFrame, fmt: dict | None = None):
        ws = wb.create_sheet(nome)
        ws.append(list(df.columns))
        for c in ws[1]:
            c.fill, c.font, c.alignment = head_fill, head_font, Alignment(horizontal="center")
        for row in df.itertuples(index=False):
            ws.append([None if _isnan(v) else (v.isoformat() if hasattr(v, "isoformat") else (", ".join(map(str, v)) if isinstance(v, (list, tuple)) else v)) for v in row])
        for j, col in enumerate(df.columns, 1):
            ws.column_dimensions[ws.cell(1, j).column_letter].width = max(12, min(40, len(str(col)) + 4))
            f = "0.0%" if col in PCT_COLS else "#,##0.00" if df[col].dtype.kind == "f" else None
            if f:
                for r in range(2, len(df) + 2):
                    ws.cell(r, j).number_format = f
        ws.freeze_panes = "A2"
        return ws

    ws = wb.active
    ws.title = "Resumo"
    ws.append([rel["meta"]["titulo"]]); ws["A1"].font = Font(bold=True, size=14, color=PRIMARY.lstrip("#"))
    for k, v in linhas_resumo(rel):
        ws.append([k, v])
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 38, 70
    ws.append([]); ws.append([rel["aviso"]])
    aba("Oportunidades", opp_tabela(rel))
    aba("Estratégias (backtest)", rel["estrategias"])
    n = rel["nucleo"]
    nuc = []
    if n.get("gem"):
        nuc.append(("GEM — posição para o próximo mês", f"{n['gem']['pick']} (UCITS {n['gem']['ucits']})"))
    ws2 = wb.create_sheet("Núcleo")
    for k, v in nuc:
        ws2.append([k, v])
    if n.get("gtaa") is not None:
        ws2.append([]); ws2.append(list(n["gtaa"].columns))
        for row in n["gtaa"].itertuples(index=False):
            ws2.append([None if _isnan(v) else v for v in row])
    ws3 = wb.create_sheet("Riscos e fontes")
    ws3.append(["Riscos"]); [ws3.append([t]) for t in rel["riscos"]]
    ws3.append([]); ws3.append(["Fontes"]); [ws3.append([t]) for t in rel["fontes"]]
    ws3.column_dimensions["A"].width = 120
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ PDF
def grafico_png(curvas: dict[str, pd.Series], titulo: str) -> bytes | None:
    if not curvas:
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cores = [tokens.THEMES["light"]["up"], tokens.SERIES["mm50"], tokens.SERIES["mm20"], tokens.THEMES["light"]["text_muted"]]
    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=150)
    for i, (nome, s) in enumerate(curvas.items()):
        ax.plot(s.index, s.values, label=nome, color=cores[i % len(cores)], lw=1.4)
    from matplotlib.ticker import FormatStrFormatter, NullFormatter
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f")); ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_title(titulo, fontsize=9, loc="left"); ax.grid(color=tokens.THEMES["light"]["grid"])
    ax.legend(fontsize=7, loc="upper left", frameon=False); ax.tick_params(labelsize=7)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    buf = io.BytesIO(); fig.tight_layout(); fig.savefig(buf, format="png"); plt.close(fig)
    return buf.getvalue()


def para_pdf(rel: dict) -> bytes:
    from fpdf import FPDF

    rgb = tuple(int(PRIMARY.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    class Doc(FPDF):
        def header(self):
            self.set_fill_color(*rgb); self.rect(0, 0, 210, 16, "F")
            self.set_text_color(255, 255, 255); self.set_font("Helvetica", "B", 12); self.set_xy(10, 5)
            self.cell(0, 6, "IDEAS CAPITAL assets", new_x="LMARGIN"); self.set_font("Helvetica", "", 9)
            self.set_xy(120, 5); self.cell(80, 6, _l1(rel["meta"]["titulo"]), align="R")
            self.set_text_color(23, 32, 51); self.set_y(20)

        def footer(self):
            self.set_y(-14); self.set_font("Helvetica", "", 6.5); self.set_text_color(91, 107, 130)
            self.multi_cell(0, 3, _l1(rel["aviso"]), align="L"); self.set_x(10)
            self.cell(0, 3, f"Pagina {self.page_no()} - gerado em {_l1(rel['meta']['gerado_em'])} - dados de {_l1(rel['meta']['data_dados'])}", align="R")

    pdf = Doc(format="A4"); pdf.set_auto_page_break(True, 18); pdf.set_margins(10, 20, 10); pdf.add_page()

    def h(txt):
        if pdf.get_y() > 245:          # evita título de seção órfão no pé da página
            pdf.add_page()
        pdf.ln(2); pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(*rgb); pdf.cell(0, 6, _l1(txt), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(23, 32, 51); pdf.set_font("Helvetica", "", 9)

    def tabela(df: pd.DataFrame, larg: list[float] | None = None):
        if df.empty:
            pdf.cell(0, 5, "Sem itens.", new_x="LMARGIN", new_y="NEXT"); return
        pdf.set_font("Helvetica", "", 7)
        with pdf.table(col_widths=larg, text_align="LEFT", line_height=4.2, borders_layout="HORIZONTAL_LINES",
                       headings_style=__import__("fpdf").fonts.FontFace(emphasis="BOLD", color=255, fill_color=rgb)) as t:
            r = t.row()
            for c in df.columns:
                r.cell(_l1(str(c)))
            for row in df.itertuples(index=False):
                r = t.row()
                for c, v in zip(df.columns, row):
                    r.cell(_l1(_celula(c, v)))
        pdf.set_font("Helvetica", "", 9)

    h("Resumo")
    for k, v in linhas_resumo(rel):
        pdf.set_font("Helvetica", "B", 9); pdf.cell(60, 5, _l1(k)); pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _l1(v), new_x="LMARGIN", new_y="NEXT")
    h("Oportunidades (estrategia ativa: " + rel["meta"]["estrategia_ativa"] + ")")
    tabela(opp_tabela(rel))
    h("Estrategias do Laboratorio - backtest simulado no universo")
    est = rel["estrategias"]
    tabela(est[[c for c in ("Estratégia", "Ativos", "Operações", "Taxa de acerto", "Profit factor", "Resultado médio", "Exposição média",
                            "a.a. regra (média dos ativos)", "a.a. buy & hold (média dos ativos)") if c in est.columns]])
    png = grafico_png(rel["curvas"], "Curvas de capital: media simples dos ativos (escala log; simulado)")
    if png:
        pdf.ln(2); pdf.image(io.BytesIO(png), w=190)
    h("Nucleo (carteiras-modelo)")
    n = rel["nucleo"]
    if n.get("gem"):
        pdf.multi_cell(0, 5, _l1(f"GEM - posicao para o proximo mes: {n['gem']['pick']} (UCITS {n['gem']['ucits']}). {n['gem']['why']}"),
                       new_x="LMARGIN", new_y="NEXT")
    if n.get("gtaa") is not None:
        tabela(n["gtaa"])
    h("Riscos e limites")
    for t in rel["riscos"]:
        pdf.multi_cell(0, 5, _l1("- " + t), new_x="LMARGIN", new_y="NEXT")
    h("Fontes")
    for t in rel["fontes"]:
        pdf.multi_cell(0, 5, _l1("- " + t), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
