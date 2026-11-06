"""Análise estruturada do Analista IA: entrada só com números calculados + saída em formato fixo.

A IA NÃO recebe a internet nem inventa níveis: recebe um JSON montado pelo app (com data de referência) e
responde em 5 seções fixas. Depois, o app valida o formato, checa se os números citados em "Dados observados"
existem no JSON e sinaliza qualquer "% de confiança".
"""
from __future__ import annotations

import json
import math
import re

SECOES = ["Dados observados", "Interpretação", "Hipóteses", "Decisão", "Riscos e limitações"]
DECISOES = ["COMPRAR", "AGUARDAR", "MANTER", "REDUZIR", "VENDER", "EVITAR"]
CONVICCOES = ["baixa", "média", "alta"]

SYSTEM_EXTRA = f"""Responda EXATAMENTE com estas cinco seções, nesta ordem, cada uma começando com '## ' e o nome:
## Dados observados — só números que estão no JSON, citados como aparecem (sem arredondar para outro valor), com a fonte.
## Interpretação — sua leitura dos dados, marcada como interpretação.
## Hipóteses — 2 a 4 hipóteses que explicariam os dados, e o que as confirmaria ou refutaria.
## Decisão — uma linha no formato: **{' | '.join(DECISOES)}** · convicção {' | '.join(CONVICCOES)}  (nunca use percentual de confiança), seguida de 1 a 2 frases.
## Riscos e limitações — o que pode estar errado, dados ausentes (cite os campos nulos) e o que invalidaria a leitura.
Não crie níveis de preço, alvos ou stops: use somente os do JSON ('plano_pela_regra_de_risco'). Se um dado estiver nulo, diga que é indisponível."""


def montar_payload(*, ticker: str, classe: str, moeda: str, data_ref: str, tecnica: dict, estrategias: dict,
                   plano: dict | None, riscos: dict, fundamentos: dict | None, retornos: dict | None) -> dict:
    """Pacote de entrada da IA. Tudo calculado pelo app; `fontes` diz de onde cada bloco veio."""
    return {"data_referencia": data_ref, "ativo": ticker, "classe": classe, "moeda": moeda,
            "tecnica": tecnica, "retornos": retornos, "estrategias_do_laboratorio": estrategias,
            "plano_pela_regra_de_risco": plano, "regras_de_risco": riscos,
            "fundamentos": fundamentos if classe == "Ação" else None,
            "fontes": {"precos": "Yahoo Finance (diário)", "tecnica/estrategias/plano": "calculado pelo app",
                       "fundamentos": "Yahoo Finance (pode ter defasagem)"}}


def para_prompt(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str, indent=1)


# ------------------------------------------------------------------ validação da resposta
def _secoes(texto: str) -> dict[str, str]:
    partes = re.split(r"(?m)^##\s+", texto)
    out = {}
    for p in partes[1:]:
        titulo, _, corpo = p.partition("\n")
        out[titulo.strip().rstrip(":").lower()] = corpo.strip()
    return out


def _numeros(texto: str) -> list[float]:
    achados = re.findall(r"(?<![\w.,])-?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?!\d)", texto)
    vals = []
    for a in achados:
        a = a.strip()
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", a):
            a = a.replace(".", "").replace(",", ".")
        else:
            a = a.replace(",", ".")
        try:
            vals.append(float(a))
        except ValueError:
            pass
    return vals


def _folhas(x) -> list[float]:
    if isinstance(x, bool) or x is None:
        return []
    if isinstance(x, (int, float)):
        return [] if (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else [float(x)]
    if isinstance(x, dict):
        return [v for y in x.values() for v in _folhas(y)]
    if isinstance(x, (list, tuple)):
        return [v for y in x for v in _folhas(y)]
    if isinstance(x, str):
        return _numeros(x)
    return []


def numeros_fora_dos_dados(observados: str, payload: dict) -> list[float]:
    """Números citados em 'Dados observados' que não aparecem no JSON (tolerância de arredondamento).

    Aceita o valor como está, em % (×100) ou em fração (÷100), com tolerância de 0,6% relativo ou 0,06 absoluto.
    Anos e dias do mês (1–31 e 1900–2100) são ignorados: datas não são medidas.
    """
    base = _folhas(payload)
    ok = base + [b * 100 for b in base] + [b / 100 for b in base]
    fora = []
    for n in _numeros(observados):
        if 1900 <= abs(n) <= 2100 or (float(n).is_integer() and 0 <= n <= 31):
            continue
        if not any(abs(n - b) <= max(0.06, abs(b) * 0.006) for b in ok):
            fora.append(n)
    return fora


def validar(texto: str, payload: dict | None = None) -> dict:
    """Confere o formato fixo. Retorna secoes, faltando, decisao, conviccao, percentual_de_confianca, numeros_fora."""
    sec = _secoes(texto)
    faltando = [s for s in SECOES if s.lower() not in sec]
    dec = conv = None
    corpo = sec.get("decisão", "")
    m = re.search(r"\b(" + "|".join(DECISOES) + r")\b", corpo.upper())
    if m:
        dec = m.group(1)
    m2 = re.search(r"convic[çc][ãa]o\s*[:\-]?\s*(baixa|m[ée]dia|alta)", corpo, re.I)
    if m2:
        conv = m2.group(1).lower().replace("media", "média")
    pc = bool(re.search(r"(confian[çc]a|convic[çc][ãa]o|probabilidade)[^.\n]{0,40}\d+\s*%", texto, re.I))
    fora = numeros_fora_dos_dados(sec.get("dados observados", ""), payload) if payload else []
    return {"secoes": {s: sec[s.lower()] for s in SECOES if s.lower() in sec}, "faltando": faltando,
            "decisao": dec, "conviccao": conv, "percentual_de_confianca": pc, "numeros_fora": fora,
            "ok": not faltando and dec is not None and conv is not None and not pc}
