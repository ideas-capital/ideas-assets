"""Transforma arquivos (PDF, HTML, planilhas, imagens) em algo que a IA lê.

Extrair o texto aqui, localmente, custa zero e funciona com qualquer modelo.
Imagens (prints de gráfico) vão como imagem para modelos com visão.
"""
from __future__ import annotations

import base64
import io
import re
from html.parser import HTMLParser

import pandas as pd


class _TextExtractor(HTMLParser):
    """Extrai texto visível de HTML, ignorando scripts, estilos e cabeçalho XBRL."""

    SKIP = {"script", "style", "head", "ix:header", "noscript"}
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in ("td", "th"):
            self.parts.append(" | ")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def pdf_text(data: bytes, max_pages: int = 120) -> str:
    from pypdf import PdfReader  # import local: só carrega quando precisa

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages[:max_pages]):
        pages.append(f"\n--- página {i + 1} ---\n{page.extract_text() or ''}")
    return "".join(pages).strip()


def table_text(data: bytes, filename: str, max_rows: int = 300) -> str:
    """CSV/Excel -> texto tabular compacto (a IA lê bem CSV)."""
    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(data))
    else:
        df = pd.read_csv(io.BytesIO(data), sep=None, engine="python")
    head = df.head(max_rows).to_csv(index=False)
    note = f"\n[{len(df)} linhas no total; mostrando {min(len(df), max_rows)}]"
    return head + note


def image_data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def extract(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return pdf_text(data)
    if name.endswith((".htm", ".html")):
        return html_to_text(data.decode("utf-8", errors="ignore"))
    if name.endswith((".csv", ".xlsx", ".xls")):
        return table_text(data, filename)
    return data.decode("utf-8", errors="ignore")


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    """Corta textos enormes. ~4 caracteres ≈ 1 token."""
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "\n\n[... documento cortado para controlar custo ...]", True
