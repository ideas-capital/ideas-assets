"""Armazenamento de dados do usuário (watchlists, alertas, diário, análises de IA, filtros salvos).

Interface única por coleção — `get / put / list / delete` — com dois backends:
- **Local** (padrão): `data/<coleção>.local.json` (ignorado pelo git; pasta alterável por `PWASS_DATA_DIR`). No Streamlit Cloud o disco é
  efêmero: some a cada reinício. Serve para uso no computador e como fallback.
- **Supabase** (opcional): ativado se `SUPABASE_URL` e `SUPABASE_KEY` existirem (env ou secrets).
  Tabelas em docs/redesign/supabase.sql, com RLS.

Nada sensível: `put` recusa documentos com chaves como saldo, senha, seed, conta, token.

Exemplo:
    >>> s = get_store(root="/tmp/dados")
    >>> s.put("watchlists", "favoritos", {"nome": "Favoritos", "tickers": ["SPY"]})
    >>> s.get("watchlists", "favoritos")["tickers"]
    ['SPY']
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol

COLECOES = ("watchlists", "alertas", "diario", "analises_ia", "filtros_salvos")
ROOT = Path(__file__).resolve().parents[1]
PROIBIDAS = re.compile(r"saldo|senha|password|seed|mnemonic|conta|account|token|secret|api_?key|cpf", re.I)


class StoreError(RuntimeError):
    pass


class Store(Protocol):
    backend: str

    def get(self, col: str, id_: str) -> dict | None: ...
    def put(self, col: str, id_: str, doc: dict) -> None: ...
    def list(self, col: str) -> list[dict]: ...
    def delete(self, col: str, id_: str) -> None: ...


def _checar(col: str, doc: dict | None = None) -> None:
    if col not in COLECOES:
        raise StoreError(f"coleção desconhecida: {col!r}; use uma de {COLECOES}")
    if doc is not None:
        _sem_sensivel(doc)


def _sem_sensivel(x, caminho: str = "") -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            if PROIBIDAS.search(str(k)):
                raise StoreError(f"campo sensível não permitido no armazenamento: {caminho}{k}")
            _sem_sensivel(v, f"{caminho}{k}.")
    elif isinstance(x, list):
        for v in x:
            _sem_sensivel(v, caminho)


class LocalStore:
    backend = "local"

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root else ROOT / "data"

    def _path(self, col: str) -> Path:
        return self.root / f"{col}.local.json"

    def _read(self, col: str) -> dict:
        p = self._path(col)
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StoreError(f"{p.name} corrompido: {e}") from e

    def _write(self, col: str, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, default=str)
        os.replace(tmp, self._path(col))     # troca atômica: nunca deixa arquivo pela metade

    def get(self, col, id_):
        _checar(col)
        return self._read(col).get(id_)

    def put(self, col, id_, doc):
        _checar(col, doc)
        data = self._read(col)
        data[id_] = {**doc, "id": id_}
        self._write(col, data)

    def list(self, col):
        _checar(col)
        return list(self._read(col).values())

    def delete(self, col, id_):
        _checar(col)
        data = self._read(col)
        if data.pop(id_, None) is not None:
            self._write(col, data)


class SupabaseStore:
    """Backend REST (PostgREST). Tabela por coleção: id text PK, doc jsonb, updated_at timestamptz."""
    backend = "supabase"

    def __init__(self, url: str, key: str, session=None):
        import requests
        self.base = url.rstrip("/") + "/rest/v1"
        self.s = session or requests.Session()
        self.h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _req(self, method: str, col: str, **kw):
        r = self.s.request(method, f"{self.base}/{col}", headers={**self.h, **kw.pop("headers", {})}, timeout=20, **kw)
        if r.status_code >= 300:
            raise StoreError(f"Supabase {method} {col}: HTTP {r.status_code} {r.text[:200]}")
        return r

    def get(self, col, id_):
        _checar(col)
        rows = self._req("GET", col, params={"id": f"eq.{id_}", "select": "id,doc"}).json()
        return {**rows[0]["doc"], "id": id_} if rows else None

    def put(self, col, id_, doc):
        _checar(col, doc)
        self._req("POST", col, json={"id": id_, "doc": {**doc, "id": id_}},
                  headers={"Prefer": "resolution=merge-duplicates"})

    def list(self, col):
        _checar(col)
        return [{**r["doc"], "id": r["id"]} for r in self._req("GET", col, params={"select": "id,doc"}).json()]

    def delete(self, col, id_):
        _checar(col)
        self._req("DELETE", col, params={"id": f"eq.{id_}"})


def get_store(root: Path | str | None = None, env: dict | None = None) -> Store:
    """Supabase se SUPABASE_URL e SUPABASE_KEY existirem; senão, local. `env` permite injetar (testes/secrets)."""
    e = env if env is not None else os.environ
    if e.get("SUPABASE_URL") and e.get("SUPABASE_KEY"):
        return SupabaseStore(e["SUPABASE_URL"], e["SUPABASE_KEY"])
    return LocalStore(root or e.get("PWASS_DATA_DIR"))
