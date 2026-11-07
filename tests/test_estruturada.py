from pwass.ai import estruturada as E

PAY = {"data_referencia": "05/11/2026", "tecnica": {"rsi14": 28.4, "price": 535.93, "sma200": 480.12},
       "retornos": {"1m": 0.0203}, "plano_pela_regra_de_risco": {"stop": 500.5}}

BOM = """## Dados observados
RSI 14 em 28,4; preço 535,93; retorno de 1 mês de +2,0% (05/11/2026).
## Interpretação
Sobrevendido em tendência de alta.
## Hipóteses
1. Pullback saudável.
## Decisão
**AGUARDAR** · convicção média. Esperar confirmação.
## Riscos e limitações
Sem fundamentos."""


def test_resposta_valida():
    v = E.validar(BOM, PAY)
    assert v["ok"] and v["decisao"] == "AGUARDAR" and v["conviccao"] == "média" and v["numeros_fora"] == []
    assert list(v["secoes"]) == E.SECOES


def test_formato_incompleto_e_confianca_em_percentual():
    ruim = BOM.replace("## Hipóteses\n1. Pullback saudável.\n", "").replace("convicção média", "confiança de 85%")
    v = E.validar(ruim, PAY)
    assert "Hipóteses" in v["faltando"] and v["percentual_de_confianca"] and not v["ok"]


def test_numero_inventado_e_detectado():
    inventado = BOM.replace("535,93", "612,40")
    assert E.validar(inventado, PAY)["numeros_fora"] == [612.4]
    assert E.numeros_fora_dos_dados("sma200 em 480,1 e retorno 2,03%", PAY) == []     # arredondamento e fração×100 aceitos


def test_decisao_invalida():
    v = E.validar(BOM.replace("AGUARDAR", "TALVEZ"), PAY)
    assert v["decisao"] is None and not v["ok"]


def test_payload_sem_fundamentos_para_etf():
    p = E.montar_payload(ticker="SPY", classe="ETF", moeda="US$", data_ref="x", tecnica={}, estrategias={}, plano=None,
                         riscos={}, fundamentos={"pe": 20}, retornos=None)
    assert p["fundamentos"] is None
