"""Smoke test de todas as páginas com AppTest (sem rede: páginas que exigem dados só precisam não quebrar o import
do app; falhas de rede aparecem como mensagens da própria página, não como exceção não tratada)."""
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).parents[1]


@pytest.mark.parametrize("tema", ["dark", "light"])
def test_pagina_componentes(tema):
    at = AppTest.from_file(str(ROOT / "paginas/_componentes.py"), default_timeout=30)
    at.query_params["tema"] = tema
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_paginas_sem_cor_hexadecimal():
    """Cores só via tokens (§2.3). Páginas não podem ter #RRGGBB."""
    import re
    achados = {f.name: re.findall(r"#[0-9A-Fa-f]{6}\b", f.read_text(encoding="utf-8"))
               for f in (ROOT / "paginas").glob("*.py")}
    assert not {k: v for k, v in achados.items() if v}


def test_status_de_badge_invalido():
    from pwass.ui import components
    with pytest.raises(ValueError):
        components.badge("QUALQUER")
    assert "COMPRA" in components.badge("compra")
