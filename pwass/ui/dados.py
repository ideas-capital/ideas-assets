"""Ações do usuário sobre o store: watchlists, alertas e a contagem da topbar. Só apresentação (sem cálculo).

Persistência via `cache.store()` (local ou Supabase). Tudo aqui trata falha do store mostrando o motivo.
"""
from __future__ import annotations

import json
import uuid

import streamlit as st

from pwass import store as _store
from pwass.engine import alertas as AL
from pwass.ui import cache, components as ds

FAVORITOS = "favoritos"


def listas() -> list[dict]:
    try:
        return sorted(cache.store().list("watchlists"), key=lambda d: d.get("nome", ""))
    except _store.StoreError as e:
        ds.error_state("Não foi possível ler as watchlists", str(e))
        return []


def salvar_lista(id_: str, nome: str, tickers: list[str]) -> None:
    cache.store().put("watchlists", id_, {"nome": nome, "tickers": list(dict.fromkeys(tickers))})


def nova_lista(nome: str) -> str:
    id_ = uuid.uuid4().hex[:8]
    salvar_lista(id_, nome.strip(), [])
    return id_


def e_favorito(ticker: str) -> bool:
    d = cache.store().get("watchlists", FAVORITOS)
    return bool(d and ticker in d.get("tickers", []))


def alternar_favorito(ticker: str) -> bool:
    """Adiciona/remove da lista 'Favoritos' (criada na primeira vez). Retorna o novo estado."""
    st_ = cache.store()
    d = st_.get("watchlists", FAVORITOS) or {"nome": "Favoritos", "tickers": []}
    tks = [t for t in d["tickers"] if t != ticker]
    novo = ticker not in d["tickers"]
    if novo:
        tks.append(ticker)
    salvar_lista(FAVORITOS, d["nome"], tks)
    return novo


def alertas() -> list[dict]:
    try:
        return sorted(cache.store().list("alertas"), key=lambda a: (a.get("ticker", ""), a.get("tipo", "")))
    except _store.StoreError as e:
        ds.error_state("Não foi possível ler os alertas", str(e))
        return []


def disparados(lista: list[dict] | None = None) -> list[dict]:
    lista = alertas() if lista is None else lista
    return cache.alert_hits(json.dumps([a for a in lista if a.get("ativo", True)], sort_keys=True, default=str)) if lista else []


def contagem_topbar() -> int | None:
    """Nº real de alertas disparados; None (não mostrar) se não há nenhum alerta configurado ou o store falhou."""
    try:
        lista = cache.store().list("alertas")
        if not any(a.get("ativo", True) for a in lista):
            return None
        return len(disparados(lista))
    except Exception:  # noqa: BLE001 — a topbar nunca derruba a página
        return None


def formulario_alerta(ticker: str, key: str, sw: dict) -> None:
    """Formulário de criação de alerta para `ticker`. Mostra só campos que têm efeito real."""
    tipo = st.selectbox("Tipo de alerta", list(AL.TIPOS), format_func=AL.TIPOS.get, key=f"{key}_tipo")
    p: dict = {}
    c1, c2 = st.columns(2)
    if tipo == "preco":
        p = {"direcao": c1.selectbox("Quando o preço ficar", ["acima", "abaixo"], key=f"{key}_dir"),
             "valor": c2.number_input("de", min_value=0.0, value=0.0, step=1.0, key=f"{key}_val")}
    elif tipo == "variacao":
        p = {"direcao": c1.selectbox("Direção", ["qualquer", "alta", "queda"], key=f"{key}_dir"),
             "limite_pct": c2.number_input("Variação mínima no dia (%)", 0.1, 50.0, 5.0, 0.5, key=f"{key}_lim")}
    elif tipo == "rsi":
        p = {"direcao": c1.selectbox("RSI fica", ["abaixo", "acima"], key=f"{key}_dir"),
             "valor": c2.number_input("de", 1.0, 99.0, 30.0, 1.0, key=f"{key}_val"), "periodo": 14}
    elif tipo == "cruzamento":
        p = {"media": c1.selectbox("Média", [50, 200], key=f"{key}_mm"),
             "sentido": c2.selectbox("Preço cruza para", ["acima", "abaixo"], key=f"{key}_sent")}
    elif tipo == "rompimento":
        p = {"dias": c1.selectbox("Canal de (dias)", [20, 55, 100], index=1, key=f"{key}_dias"),
             "lado": c2.selectbox("Fecha", ["maxima", "minima"], format_func=lambda x: "acima da máxima" if x == "maxima" else "abaixo da mínima",
                                  key=f"{key}_lado")}
    elif tipo == "volume":
        p = {"multiplo": c1.number_input("Múltiplo da média de 20 sessões", 1.1, 20.0, 2.0, 0.5, key=f"{key}_mult")}
    elif tipo == "sinal":
        p = {"estrategia": c1.selectbox("Estratégia", list(sw["estrategias"]), format_func=lambda k: sw["estrategias"][k]["curto"], key=f"{key}_est"),
             "situacao": c2.selectbox("Situação", ["COMPRA", "PERTO", "SAIR"], key=f"{key}_sit")}
    invalido = tipo == "preco" and not p["valor"]
    if st.button("Criar alerta", key=f"{key}_ok", disabled=invalido, type="primary"):
        id_ = f"{ticker}-{tipo}-{uuid.uuid4().hex[:6]}"
        try:
            cache.store().put("alertas", id_, {"ticker": ticker, "tipo": tipo, "params": p, "ativo": True})
            st.success(f"Alerta criado: {ticker} · {AL.descrever({'tipo': tipo, 'params': p})}")
        except _store.StoreError as e:
            st.error(str(e))
