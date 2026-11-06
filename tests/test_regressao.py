"""Regressão numérica: swing e carteiras idênticos aos valores-ouro gravados antes do redesign v5."""
import json

from tests import regressao


def test_numeros_identicos_ao_golden():
    esperado = json.loads((regressao.FIX / "golden.json").read_text())
    atual = json.loads(json.dumps(regressao.compute(), sort_keys=True))
    assert atual == esperado
