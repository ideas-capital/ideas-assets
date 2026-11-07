"""Smoke de todas as páginas (AppTest, nos dois temas). Precisa de rede (Yahoo). Uso:
    PYTHONPATH=. python scripts/smoke_paginas.py
Sai com código 1 se alguma página levantar exceção."""
import pathlib
import sys

from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGINAS = ["terminal", "radar_ativos", "ativo", "scanner", "radar", "laboratorio", "carteiras", "relatorios", "configuracoes", "diario", "comparar", "alertas", "analista", "guia", "_componentes"]
falhas = 0
for tema in ("dark", "light"):
    for p in PAGINAS:
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
        at.query_params["tema"] = tema
        at.run()
        if p != "terminal":
            at.switch_page(f"paginas/{p}.py")
            at.run()
        erro = [e.value[:200] for e in at.exception]
        falhas += bool(erro)
        print(tema, p, f"EXCEÇÃO: {erro}" if erro else "ok", flush=True)
sys.exit(1 if falhas else 0)
