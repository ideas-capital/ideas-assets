"""Renda fixa brasileira e câmbio — fontes oficiais e gratuitas, sem chave.

- Banco Central (SGS): Selic, CDI, IPCA, PTAX.  https://api.bcb.gov.br
- Banco Central (Focus): expectativa de inflação do mercado.
- Tesouro Transparente: taxas diárias de todos os títulos do Tesouro Direto
  desde 2004 (arquivo CSV de ~15 MB; o app guarda em cache por 12 h).
"""
from __future__ import annotations

import io
import time

import pandas as pd
import requests

SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sid}/dados"
FOCUS_URL = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
             "ExpectativasMercadoInflacao12Meses?$top=1&$format=json&$orderby=Data%20desc"
             "&$filter=Indicador%20eq%20'IPCA'%20and%20Suavizada%20eq%20'S'%20and%20baseCalculo%20eq%200")
TESOURO_URL = ("https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
               "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")

# Séries do SGS usadas no app
SGS = {
    "selic_meta": 432,     # Selic meta, % a.a.
    "cdi_aa": 4389,        # CDI anualizado (base 252), % a.a.
    "cdi_mes": 4391,       # CDI acumulado no mês, %
    "ipca_12m": 13522,     # IPCA acumulado em 12 meses, %
    "ptax": 1,             # Dólar PTAX venda, R$
}

PRINCIPAIS = ["Tesouro Selic", "Tesouro Prefixado", "Tesouro IPCA+",
              "Tesouro IPCA+ com Juros Semestrais", "Tesouro Renda+ Aposentadoria Extra"]


def _get(url: str, params: dict | None = None, timeout: int = 60, tries: int = 3) -> requests.Response:
    """GET com até 3 tentativas: as APIs públicas às vezes derrubam a conexão."""
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("inalcançável")


def sgs(sid: int, start: str | None = None, last: int | None = None, timeout: int = 60) -> pd.Series:
    """Série do SGS. Use `last` para os N últimos valores ou `start` (dd/mm/aaaa)."""
    url = SGS_URL.format(sid=sid) + (f"/ultimos/{last}" if last else "")
    params = {"formato": "json"}
    if start and not last:
        params["dataInicial"] = start
    df = pd.DataFrame(_get(url, params, timeout).json())
    return pd.Series(pd.to_numeric(df["valor"]).values,
                     index=pd.to_datetime(df["data"], dayfirst=True), name=str(sid))


def focus_ipca_12m(timeout: int = 30) -> tuple[float, str]:
    """Mediana da expectativa de IPCA para os próximos 12 meses (Focus, suavizada)."""
    v = _get(FOCUS_URL, timeout=timeout).json()["value"][0]
    return float(v["Mediana"]), pd.Timestamp(v["Data"]).strftime("%d/%m/%Y")


def tesouro(timeout: int = 180) -> pd.DataFrame:
    """Histórico completo de taxas e preços do Tesouro Direto."""
    return parse_tesouro(_get(TESOURO_URL, timeout=timeout).content)


def parse_tesouro(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), sep=";", decimal=",")
    df["Data Base"] = pd.to_datetime(df["Data Base"], dayfirst=True)
    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], dayfirst=True)
    return df.rename(columns={"Tipo Titulo": "Titulo", "Data Vencimento": "Vencimento",
                              "Data Base": "Data", "Taxa Compra Manha": "Taxa",
                              "PU Compra Manha": "Preco"})[["Titulo", "Vencimento", "Data", "Taxa", "Preco"]]


def tesouro_hoje(df: pd.DataFrame) -> pd.DataFrame:
    """Taxas do último dia disponível, só dos títulos principais."""
    last = df[df["Data"] == df["Data"].max()]
    last = last[last["Titulo"].isin(PRINCIPAIS)].sort_values(["Titulo", "Vencimento"])
    return last.reset_index(drop=True)


def ipca_plus_history(df: pd.DataFrame, since: str = "2010-01-01") -> pd.Series:
    """Taxa real média diária dos títulos IPCA+ (NTN-B), para comparar com a história."""
    m = df[df["Titulo"].isin(["Tesouro IPCA+", "Tesouro IPCA+ com Juros Semestrais"])
           & (df["Data"] >= since) & (df["Vencimento"] - df["Data"] > pd.Timedelta(days=5 * 365))]
    return m.groupby("Data")["Taxa"].median().rename("IPCA+ longo (taxa real)")


def implied_inflation(today: pd.DataFrame) -> pd.DataFrame:
    """Inflação implícita = (1 + prefixado) / (1 + IPCA+ de prazo parecido) − 1."""
    pre = today[today["Titulo"] == "Tesouro Prefixado"]
    ipca = today[today["Titulo"] == "Tesouro IPCA+"]
    rows = []
    for _, p in pre.iterrows():
        if ipca.empty:
            break
        gap = (ipca["Vencimento"] - p["Vencimento"]).abs()
        j = gap.idxmin()
        if gap[j] <= pd.Timedelta(days=400):
            i = ipca.loc[j]
            rows.append({"Prazo": p["Vencimento"].year, "Prefixado %": p["Taxa"],
                         "IPCA+ %": i["Taxa"],
                         "Inflação implícita %": ((1 + p["Taxa"] / 100) / (1 + i["Taxa"] / 100) - 1) * 100})
    return pd.DataFrame(rows)
