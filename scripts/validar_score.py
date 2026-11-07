"""Valida o score de qualidade do sinal com dados reais e grava config/score.yaml + docs/redesign/SCORE.md.

Uso:  python scripts/validar_score.py      (precisa de internet: baixa 10 anos de candles do universo)
Calibra com sinais até 2019 e testa de 2020 em diante. Se não passar, o score NÃO é mostrado no app
(`validacao.mostrar: false`) e o SCORE.md registra o motivo. Rodar de novo só muda o resultado se os dados mudarem.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pwass.data import market  # noqa: E402
from pwass.engine import score as SC  # noqa: E402


def _tab(df: pd.DataFrame) -> str:
    linhas = ["| Faixa | Operações | Taxa de acerto | Retorno médio | Profit factor |", "|---|---|---|---|---|"]
    for r in df.itertuples():
        linhas.append(f"| {r.Faixa} | {r.Operações} | {round(r._3 * 100)}% | {r._4 * 100:+.2f}% | {r._5:.2f} |".replace(".", ","))
    return "\n".join(linhas)


def main() -> None:
    sw = yaml.safe_load((ROOT / "config/swing.yaml").read_text(encoding="utf-8"))
    tickers = [t for d in sw["universo"].values() for t in d]
    data = market.ohlcv(list(dict.fromkeys(tickers + ["SPY"])), "10y")
    ds = SC.dataset(data, sw, data["SPY"]["Close"])
    ref = max(d.index[-1] for d in data.values())
    res = SC.validar(ds)
    print(f"{len(ds)} operações · treino {res['n_treino']} · teste {res['n_teste']} · mostrar={res['mostrar']}")
    for m in res["motivos"]:
        print(" -", m)
    cfg = {"validacao": {"mostrar": bool(res["mostrar"]), "motivos": res["motivos"], "data_dados": str(ref.date()),
                         "corte_treino_teste": res["corte"], "n_treino": res["n_treino"], "n_teste": res["n_teste"],
                         "rho_teste": round(res.get("rho_teste", float("nan")), 4) if "rho_teste" in res else None,
                         "p_teste": round(res.get("p_teste", float("nan")), 4) if "p_teste" in res else None,
                         "cortes_faixas": [round(c, 2) for c in res.get("cortes", [])]},
           "pesos": {k: round(v, 4) for k, v in res["pesos"].items()}}
    (ROOT / "config/score.yaml").write_text(
        "# Gerado por scripts/validar_score.py — NÃO editar à mão.\n# O app só mostra o score se validacao.mostrar for true.\n"
        + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    md = [f"# Score de qualidade do sinal — metodologia e validação", "",
          f"Dados: Yahoo Finance, candles diários até {ref:%d/%m/%Y}; universo do Laboratório ({len(data)} ativos), 3 estratégias, custo de 0,10% por lado, "
          "execução na abertura seguinte. Gerado em " + date.today().strftime("%d/%m/%Y") + " por `scripts/validar_score.py`.", "",
          "## Metodologia",
          "Cada operação do backtest recebe 7 componentes (0–1) calculados **só com dados até o fechamento do sinal**:",
          *[f"- **{SC.ROTULOS[k]}**" for k in SC.COMPONENTES],
          "", "Calibração: peso de cada componente ∝ max(0, correlação de Spearman com o retorno da operação), usando só sinais **até 2019**. "
          "Faixas (baixa/média/alta) = tercis dos scores do treino. Teste: sinais **de 2020 em diante**, nunca vistos na calibração. "
          "Critérios para MOSTRAR o score: correlação fora da amostra > 0, p < 0,05 (permutação, 2000 sorteios), faixa alta com retorno médio maior que o da baixa e ≥ 30 operações em cada.", "",
          "## Resultado", f"Operações: treino {res['n_treino']} · teste {res['n_teste']}."]
    if res["pesos"]:
        md += ["", "Pesos calibrados: " + ", ".join(f"{SC.ROTULOS[k]} {v:.0%}" for k, v in res["pesos"].items()) + "."]
    if "tabela_teste" in res:
        md += ["", (f"Correlação (Spearman) fora da amostra: **{res['rho_teste']:+.3f}** (p = {res['p_teste']:.3f}); no treino: {res['rho_treino']:+.3f}").replace(".", ",") + ".",
               "", "### Faixas no treino (2016–2019)", _tab(res["tabela_treino"]), "", "### Faixas no TESTE (2020 em diante)", _tab(res["tabela_teste"])]
    md += ["", "## Decisão", ("**O score é mostrado no app.** " if res["mostrar"] else "**O score NÃO é mostrado no app.** ") + "; ".join(res["motivos"]) + ".",
           "" if res["mostrar"] else "No lugar dele, o app mostra o checklist de fatores a favor e contra (regras determinísticas, `engine/fatores.py`).",
           "", "## Limitações", "- Universo atual com viés de sobrevivência; amostra de ~10 anos e poucos regimes (2020 e 2022 dominam o teste).",
           "- Operações de um mesmo ativo/dia não são independentes; o p-valor é otimista.",
           "- Resultado passado não garante resultado futuro. Rodar de novo com mais dados pode mudar a decisão."]
    (ROOT / "docs/redesign/SCORE.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
