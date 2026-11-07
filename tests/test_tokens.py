"""Contraste WCAG AA dos tokens (texto ≥ 4,5:1; elementos gráficos ≥ 3:1)."""
import pytest

from pwass.ui import tokens

SURFACES = ("bg", "bg2", "surface", "surface_raised")
TEXTS = ("text", "text_muted", "primary_text", "up", "down", "warn", "indicator")


@pytest.mark.parametrize("mode", ["dark", "light"])
@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("fg", TEXTS)
def test_texto_aa(mode, surface, fg):
    t = tokens.THEMES[mode]
    assert tokens.contrast(t[fg], t[surface]) >= 4.5, (mode, fg, surface)


@pytest.mark.parametrize("mode", ["dark", "light"])
def test_primary_com_texto_branco(mode):  # botão primário: texto branco sobre azul
    assert tokens.contrast("#FFFFFF", tokens.THEMES[mode]["primary"]) >= 4.5


@pytest.mark.parametrize("mode", ["dark", "light"])
@pytest.mark.parametrize("serie", sorted(tokens.SERIES))
def test_series_grafico(mode, serie):
    assert tokens.contrast(tokens.SERIES[serie], tokens.THEMES[mode]["surface"]) >= 3.0, (mode, serie)


def test_temas_tem_mesmas_chaves():
    assert tokens.THEMES["dark"].keys() == tokens.THEMES["light"].keys()


def test_contraste_referencia():
    assert tokens.contrast("#FFFFFF", "#000000") == 21.0


def test_config_toml_espelha_tokens():
    import pathlib
    import tomllib
    cfg = tomllib.loads((pathlib.Path(__file__).parents[1] / ".streamlit/config.toml").read_text())
    for mode, t in tokens.THEMES.items():
        c = cfg["theme"][mode]
        assert (c["backgroundColor"], c["textColor"], c["primaryColor"]) == (t["bg"], t["text"], t["primary"])
        assert cfg["theme"][mode]["sidebar"]["backgroundColor"] == t["bg2"]
