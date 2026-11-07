"""Montagem do relatório (dados) — a ÚNICA fonte dos números do PDF, do Excel e da pré-visualização na tela.

Recebe resultados já calculados pelos motores (nada é recalculado aqui) e devolve um dict pronto para os
renderizadores de `pwass/export.py`. Assim o relatório não pode divergir do app.
"""
from __future__ import annotations

import pandas as pd

FONTES = ["Yahoo Finance (cotações diárias, preços ajustados)", "Banco Central do Brasil (CDI)",
          "Cálculos do próprio app (regras em config/*.yaml); backtests são simulações"]
AVISO = ("IDEAS CAPITAL assets · ferramenta pessoal de Renan Cotta. Sinais gerados por regras para apoiar a leitura do mercado; "
         "a decisão, o aporte e o risco são exclusivamente do usuário. Resultado passado não garante resultado futuro.")


def montar(*, gerado_em: str, data_dados: str, estrategia: str, regime: dict, amplitude: dict, vix: float | None,
           vix_percentil: float | None, oportunidades: pd.DataFrame, comparacao: pd.DataFrame, gem: dict | None,
           gtaa: pd.DataFrame | None, risco: dict, satelite: dict, novidades: dict[str, list[str]],
           curvas: dict[str, pd.Series] | None = None) -> dict:
    """Dict do relatório. Seções: meta, resumo, oportunidades, estrategias (inclui o histórico/backtest), nucleo, curvas, riscos, fontes."""
    comp = comparacao.drop(columns=[c for c in ("id",) if c in comparacao.columns])
    n_compra = int((oportunidades["Situação"] == "COMPRA").sum()) if len(oportunidades) else 0
    riscos = [
        f"Laboratório de swing: capital de US$ {risco['capital_laboratorio_usd']:,.0f}, risco de {risco['risco_por_operacao'] * 100:g}% por operação, "
        f"stop inicial de {risco['multiplo_atr_stop']:g}×ATR, posição máxima de {risco['posicao_maxima'] * 100:g}% do capital.".replace(",", "."),
        f"Satélite: até {satelite.get('satellite_max_pct')}% do patrimônio, {satelite.get('single_position_max_pct')}% por ativo e "
        f"{satelite.get('crypto_max_pct')}% em cripto.",
        f"Regime de mercado {regime['rotulo']} ({regime['acima']} de {regime['total']} classes de risco acima da MM200).",
        "Backtests têm viés de sobrevivência (universo atual de ativos líquidos) e custo de 0,10% por lado; não incluem impostos.",
        "Dados do Yahoo Finance podem ter atraso ou erro; confira antes de operar."]
    return {
        "meta": {"titulo": "Relatório de mercado e estratégias", "gerado_em": gerado_em, "data_dados": data_dados, "estrategia_ativa": estrategia},
        "resumo": {"regime": regime["rotulo"], "classes_acima": regime["acima"], "classes_total": regime["total"],
                   "amplitude_pct": amplitude.get("pct"), "amplitude_acima": amplitude.get("acima"), "amplitude_n": amplitude.get("n"),
                   "vix": vix, "vix_percentil": vix_percentil, "setups_de_compra": n_compra,
                   "novos_setups": novidades.get("novos_setups", []), "cruzaram_mm200_acima": novidades.get("cruzou_mm200_acima", []),
                   "cruzaram_mm200_abaixo": novidades.get("cruzou_mm200_abaixo", [])},
        "oportunidades": oportunidades.reset_index(drop=True),
        "estrategias": comp.reset_index(drop=True),
        "nucleo": {"gem": gem, "gtaa": gtaa.reset_index() if gtaa is not None else None},
        "curvas": curvas or {}, "riscos": riscos, "fontes": FONTES, "aviso": AVISO}
