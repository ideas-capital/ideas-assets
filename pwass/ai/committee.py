"""Comitê de IA: três especialistas e um juiz, sem framework.

Por que não CrewAI/AutoGen/LangGraph: são 4 chamadas em sequência; um orquestrador
de poucas linhas é mais barato, mais rápido e mais fácil de auditar. Cada agente
recebe só números já calculados pelo app (a IA interpreta; o Python calcula).

Fluxo:  Técnico ─┐
        Macro/Fundamentalista ─┼─> Juiz → recomendação final (comprar/aguardar/...)
        Risco ───┘
"""
from __future__ import annotations

import json
from typing import Callable

from pwass.ai.prompts import SYSTEM

AGENTS = {
    "tecnico": ("Agente Técnico", """Você é o AGENTE TÉCNICO. Avalie só tendência, momento, sobrecompra/sobrevenda,
volatilidade e o setup da estratégia selecionada, usando o histórico da regra NAQUELE ativo
(número de operações, acerto, profit factor, máxima queda). Diga se o gatilho é de qualidade
ou se o histórico não sustenta. Máximo 180 palavras, em tópicos."""),
    "fundamental": ("Agente Macro/Fundamentalista", """Você é o AGENTE MACRO/FUNDAMENTALISTA. Avalie valuation
(P/L, crescimento, margens, Piotroski, DCF reverso) e o pano de fundo macro (juros, curva, dólar,
volatilidade). Para ETF ou cripto, foque no macro e no ciclo. Diga se os fundamentos apoiam,
são neutros ou contradizem uma compra agora. Máximo 180 palavras, em tópicos."""),
    "risco": ("Agente de Risco", """Você é o AGENTE DE RISCO. Avalie o plano da operação: distância do stop,
tamanho da posição pelo ATR, risco em dólares, relação risco/retorno dos alvos, volatilidade
e máxima queda histórica. Diga se o risco é aceitável dentro do laboratório de swing e o que
ajustar (tamanho menor, esperar, não entrar). Máximo 150 palavras, em tópicos."""),
}

JUDGE = """Você é o JUIZ do comitê. Leia os três pareceres e os dados e decida.
Responda exatamente neste formato, em português:

## Decisão: <COMPRAR | AGUARDAR | MANTER | REDUZIR | VENDER | EVITAR> — convicção <baixa | média | alta>
**Plano:** entrada, stop e alvos (use os números do plano fornecido; não invente outros).
**Por quê (3 pontos):**
- ...
**Onde os agentes discordam:** ...
**O que invalida a decisão:** gatilhos objetivos (preço, indicador, evento).

Sem percentuais de confiança. Seja curto."""


def _blob(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, default=str, indent=1)


def run(ticker: str, data: dict, ask: Callable, models: dict) -> dict:
    """Executa o comitê. `ask(messages, model)` devolve um objeto com `.text` (ou None se falhar)."""
    out: dict = {}
    payload = _blob(data)
    for key, (name, role) in AGENTS.items():
        r = ask([{"role": "system", "content": SYSTEM + "\n" + role},
                 {"role": "user", "content": f"Ativo: {ticker}\n\nDADOS:\n{payload}"}], models.get(key))
        if r is None:
            return out
        out[key] = (name, r)
    opinions = "\n\n".join(f"### {name}\n{r.text}" for name, r in out.values())
    j = ask([{"role": "system", "content": SYSTEM + "\n" + JUDGE},
             {"role": "user", "content": f"Ativo: {ticker}\n\nPARECERES:\n{opinions}\n\nDADOS:\n{payload}"}],
            models.get("juiz"))
    if j is not None:
        out["juiz"] = ("Juiz", j)
    return out
