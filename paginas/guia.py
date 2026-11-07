"""Guia: renderiza docs/GUIA.md em abas (uma por seção '## ')."""
import streamlit as st

from pwass.ui import cache, components as ds

ds.page_header("Guia e rotina", "Como o app pensa, como usar cada tela e a rotina para acompanhar o mercado.", source="docs/GUIA.md")

text = (cache.ROOT / "docs" / "GUIA.md").read_text(encoding="utf-8")
sections = [s for s in text.split("\n## ")[1:]]  # ignora o título '# ...'
titles = [s.split("\n", 1)[0].strip() for s in sections]
for tab, sec in zip(st.tabs(titles), sections):
    with tab:
        st.markdown(sec.split("\n", 1)[1] if "\n" in sec else "")
