"""Relatório mensal em Markdown: sinais GEM/GTAA, regime, macro e top do scanner.

Uso:  python scripts/relatorio_mensal.py            -> grava relatorios/AAAA-MM.md
      OPENROUTER_API_KEY=... python scripts/...      -> inclui comentário da IA
Roda sozinho todo mês pelo GitHub Actions (.github/workflows/relatorio-mensal.yml).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pwass.ai import openrouter, prompts  # noqa: E402
from pwass.data import fred, market  # noqa: E402
from pwass.engine import factors, indicators, strategies as S  # noqa: E402

REGIME = {"SPY": "S&P 500", "VEU": "Mundo ex-EUA", "EEM": "Emergentes", "VNQ": "REITs",
          "DBC": "Commodities", "TLT": "Treasury 20+", "GLD": "Ouro", "BTC-USD": "Bitcoin"}


def main() -> None:
    px = market.prices(["SPY", "VEU", "BIL", "AGG", "VTI", "IEF", "VNQ", "DBC", "EEM", "TLT", "GLD", "BTC-USD"])
    m = S.completed_months(S.monthly(px))
    month = m.index[-1]
    lines = [f"# Relatório PWASS — {month:%m/%Y}", "",
             "_Sinais calculados no último pregão do mês. Uso pessoal; decisão e risco são do usuário._", ""]

    g = S.gem_explain(m)
    lines += ["## Dual Momentum (GEM)", f"**Posição para o próximo mês: {S.NAMES[g['pick']]} — {g['pick']}"
              f" (UCITS: {g['ucits']})**", "", g["why"], ""]

    ex = S.gtaa_explain(m)
    lines += ["## GTAA (Faber)", "| Classe | vs média 10m | Sinal | UCITS |", "|---|---|---|---|"]
    lines += [f"| {r.Classe} | {r.Distância:+.1%} | {r.Sinal} | {r.UCITS} |" for r in ex.itertuples()]
    lines.append("")

    lines += ["## Regime (preço vs média de 200 dias)", "| Ativo | Retorno 12m | Tendência |", "|---|---|---|"]
    for t, name in REGIME.items():
        s = px[t].dropna()
        up = s.iloc[-1] > indicators.sma(s, 200).iloc[-1]
        r12 = s.iloc[-1] / s[s.index <= s.index[-1] - pd.DateOffset(years=1)].iloc[-1] - 1
        lines.append(f"| {name} | {r12:+.1%} | {'▲ alta' if up else '▼ baixa'} |")
    lines.append("")

    lines += ["## Macro EUA", "| Indicador | Último |", "|---|---|"]
    for sid, (name, unit, _) in fred.SERIES.items():
        try:
            s = fred.series(sid)
            lines.append(f"| {name} | {s.iloc[-1]:.2f} {unit} ({s.index[-1]:%m/%Y}) |")
        except Exception as e:  # noqa: BLE001
            lines.append(f"| {name} | indisponível ({e}) |")
    lines.append("")

    try:
        uni = yaml.safe_load((ROOT / "config" / "universe.yaml").read_text(encoding="utf-8"))
        tickers = list(dict.fromkeys(t for g_ in uni["grupos"].values() for t in g_))
        res = factors.qvm(market.fundamentals_many(tickers, workers=4), market.prices(tickers, "2y"), uni.get("pesos"))
        top = res.head(15)
        lines += ["## Scanner QVM — Top 15 (para estudar, não para comprar)",
                  "| # | Ticker | Nome | Nota | Q | V | M | MM200 |", "|---|---|---|---|---|---|---|---|"]
        for i, (t, r) in enumerate(top.iterrows(), 1):
            lines.append(f"| {i} | {t} | {r['Nome']} | {r['Nota']:.0f} | {r['Qualidade']:.0f} | "
                         f"{r['Valor']:.0f} | {r['Momento']:.0f} | {'✅' if r['Acima MM200'] else '—'} |")
        lines.append("")
    except Exception as e:  # noqa: BLE001
        lines += [f"_Scanner indisponível: {e}_", ""]

    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        model = os.getenv("PWASS_MODELO", "anthropic/claude-haiku-5.5")
        ask = ("Comente este relatório mensal em até 200 palavras: o que mudou no regime, se os sinais de "
               "GEM e GTAA concordam e o que observar no próximo mês.\n\n" + "\n".join(lines))
        try:
            r = openrouter.chat(key, model, [{"role": "system", "content": prompts.SYSTEM},
                                             {"role": "user", "content": ask}], max_tokens=2500)
            lines += ["## Comentário da IA", f"_Modelo: {r.model}_", "", r.text, ""]
        except openrouter.OpenRouterError as e:
            lines += [f"_IA indisponível: {e}_", ""]

    out = ROOT / "relatorios" / f"{month:%Y-%m}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Gravado {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
