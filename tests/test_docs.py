"""Coerência da documentação com a navegação real do app."""
import pathlib
import re

ROOT = pathlib.Path(__file__).parents[1]
ANTIGOS = ["Mercado hoje", "Raio-X", "Estratégias e carteiras", "Scanner de ações", "Radar de ativos", "Terminal)", "*Terminal*"]


def _menu_titulos() -> list[str]:
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    return re.findall(r'\("paginas/\w+\.py", "([^"]+)"', app)


def test_guia_e_readme_nao_citam_telas_antigas():
    for arq in ("docs/GUIA.md", "README.md"):
        txt = (ROOT / arq).read_text(encoding="utf-8")
        achados = [n for n in ANTIGOS if n in txt]
        assert not achados, f"{arq} cita telas que não existem mais: {achados}"


def test_guia_lista_todas_as_telas_do_menu():
    guia = (ROOT / "docs/GUIA.md").read_text(encoding="utf-8")
    faltando = [t for t in _menu_titulos() if t not in guia and t.split(" ")[0] not in guia]
    assert not faltando, f"telas do menu sem menção no GUIA.md: {faltando}"


def test_todo_arquivo_do_menu_existe_e_paginas_estao_no_menu_ou_ocultas():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    no_menu = set(re.findall(r'"paginas/(\w+)\.py"', app))
    em_disco = {p.stem for p in (ROOT / "paginas").glob("*.py")}
    assert no_menu == em_disco, (no_menu ^ em_disco)      # nada órfão (como o antigo mercado.py) nem menu apontando para o vazio


def test_workflow_de_alertas_e_yaml_valido():
    import yaml
    w = yaml.safe_load((ROOT / ".github/workflows/alertas.yml").read_text(encoding="utf-8"))
    assert "jobs" in w and (w.get("on") or w.get(True))


def test_nenhum_segredo_ou_dado_local_versionado():
    import subprocess
    arqs = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    ruins = [a for a in arqs if a.endswith(".local.json") or a.endswith(".local.yaml") or a.endswith("secrets.toml") or a.startswith(("vault/", "exports/"))]
    assert not ruins, ruins
