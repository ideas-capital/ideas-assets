import io

import numpy as np
import pandas as pd
import pytest

from pwass import export
from pwass.engine import relatorio as R


def _rel():
    opp = pd.DataFrame({"Ticker": ["NVDA", "SPY"], "Ativo": ["Nvidia", "S&P 500"], "Último": [193.1, 735.29], "Dia": [0.0123, -0.004],
                        "Situação": ["COMPRA", "PERTO"], "Histórico": ["Bom", "Regular"], "Operações": [33, 81], "Acerto": [0.7, 0.68],
                        "Profit factor": [3.24, 1.41], "Resultado médio": [0.0366, 0.002]})
    comp = pd.DataFrame({"Estratégia": ["Swing Trade — Pullback"], "id": ["pullback"], "Ativos": [35], "Operações": [3318],
                         "Taxa de acerto": [0.6], "Profit factor": [2.5], "Resultado médio": [0.03], "Ganho médio": [0.06], "Perda média": [-0.04],
                         "Exposição média": [0.15], "a.a. regra (média dos ativos)": [0.021], "a.a. buy & hold (média dos ativos)": [0.2],
                         "Pior queda (média dos ativos)": [-0.18]})
    idx = pd.bdate_range("2020-01-01", periods=200)
    curvas = {"Swing": pd.Series(np.linspace(1, 1.5, 200), index=idx), "Buy & hold": pd.Series(np.linspace(1, 2.0, 200), index=idx)}
    gtaa = pd.DataFrame({"Preço": [100.0], "Sinal": ["Manter"]}, index=pd.Index(["VTI"], name="Classe"))
    return R.montar(gerado_em="07/11/2026 10:00 BRT", data_dados="06/11/2026", estrategia="Swing Trade — Pullback",
                    regime={"rotulo": "MISTO", "acima": 3, "total": 7}, amplitude={"pct": 0.46, "acima": 16, "n": 35}, vix=26.4,
                    vix_percentil=0.94, oportunidades=opp, comparacao=comp, gem={"pick": "SPY", "ucits": "CSPX.L", "why": "EUA vence caixa."},
                    gtaa=gtaa, risco={"capital_laboratorio_usd": 5000, "risco_por_operacao": 0.01, "multiplo_atr_stop": 2.0, "posicao_maxima": 0.25},
                    satelite={"satellite_max_pct": 20, "single_position_max_pct": 5, "crypto_max_pct": 5},
                    novidades={"novos_setups": ["NVDA"], "cruzou_mm200_acima": [], "cruzou_mm200_abaixo": ["TSLA"]}, curvas=curvas)


def test_excel_tem_os_mesmos_valores_do_dict():
    from openpyxl import load_workbook
    rel = _rel()
    wb = load_workbook(io.BytesIO(export.para_excel(rel)))
    assert wb.sheetnames == ["Resumo", "Oportunidades", "Estratégias (backtest)", "Núcleo", "Riscos e fontes"]
    ws = wb["Oportunidades"]
    cab = [c.value for c in ws[1]]
    assert cab == list(export.opp_tabela(rel).columns)
    lin = {c: ws.cell(2, i + 1).value for i, c in enumerate(cab)}
    assert lin["Ticker"] == "NVDA" and lin["Último"] == 193.1 and lin["Profit factor"] == 3.24 and lin["Acerto"] == 0.7
    est = wb["Estratégias (backtest)"]
    assert est.cell(2, 3).value == rel["estrategias"].iloc[0]["Operações"] and "id" not in [c.value for c in est[1]]
    resumo = {r[0].value: r[1].value for r in wb["Resumo"].iter_rows(min_row=2) if r[0].value}
    assert resumo["Regime de mercado"].startswith("MISTO") and "46%" in resumo["Amplitude (ativos acima da MM200)"]


def test_pdf_contem_os_mesmos_numeros_e_acentos():
    from pypdf import PdfReader
    rel = _rel()
    pdf = export.para_pdf(rel)
    assert pdf[:5] == b"%PDF-"
    txt = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    for esperado in ("MISTO", "46%", "26,4", "NVDA", "193,10", "3,24", "70,0%", "Núcleo" if False else "Nucleo", "CSPX.L", "07/11/2026 10:00 BRT",
                     "IDEAS CAPITAL assets"):
        assert esperado in txt, esperado
    assert "Swing Trade" in txt and "60,0%" in txt                  # taxa de acerto da estratégia


def test_formatadores():
    assert export.br(1234.5) == "1.234,50" and export.br_pct(0.0366) == "3,7%" and export.br(float("nan")) == "—"
    assert export.br_pct(None) == "—" and export._l1("a≥b — c") == "a>=b - c"


def test_relatorio_sem_oportunidades_nao_quebra():
    rel = _rel()
    rel["oportunidades"] = rel["oportunidades"].iloc[0:0]
    assert export.para_pdf(rel)[:4] == b"%PDF" and export.para_excel(rel)[:2] == b"PK"
