import pytest

from pwass import store


def test_local_crud(tmp_path):
    s = store.get_store(root=tmp_path, env={})
    assert s.backend == "local" and s.list("watchlists") == [] and s.get("watchlists", "x") is None
    s.put("watchlists", "fav", {"nome": "Favoritos", "tickers": ["SPY", "QQQ"]})
    s.put("watchlists", "tec", {"nome": "Tec", "tickers": ["NVDA"]})
    assert s.get("watchlists", "fav") == {"nome": "Favoritos", "tickers": ["SPY", "QQQ"], "id": "fav"}
    assert {d["id"] for d in s.list("watchlists")} == {"fav", "tec"}
    s.put("watchlists", "fav", {"nome": "Favoritos", "tickers": ["SPY"]})          # sobrescreve
    assert s.get("watchlists", "fav")["tickers"] == ["SPY"]
    s.delete("watchlists", "tec")
    s.delete("watchlists", "inexistente")                                           # idempotente
    assert [d["id"] for d in s.list("watchlists")] == ["fav"]
    assert (tmp_path / "watchlists.local.json").exists()


def test_persiste_entre_instancias_e_unicode(tmp_path):
    store.LocalStore(tmp_path).put("diario", "1", {"motivo": "pullback — regra seguida ✓"})
    assert store.LocalStore(tmp_path).get("diario", "1")["motivo"] == "pullback — regra seguida ✓"


def test_recusa_colecao_desconhecida_e_campos_sensiveis(tmp_path):
    s = store.LocalStore(tmp_path)
    with pytest.raises(store.StoreError):
        s.put("outra", "1", {})
    for campo in ("saldo", "senha", "seed_phrase", "numero_conta", "api_key", "telegram_token"):
        with pytest.raises(store.StoreError):
            s.put("diario", "1", {"ok": 1, "aninhado": {campo: "x"}})
    assert s.list("diario") == []


def test_arquivo_corrompido_da_erro_claro(tmp_path):
    (tmp_path / "alertas.local.json").write_text("{quebrado")
    with pytest.raises(store.StoreError):
        store.LocalStore(tmp_path).list("alertas")


def test_escolha_do_backend_e_supabase_via_http(tmp_path):
    s = store.get_store(env={"SUPABASE_URL": "https://x.supabase.co/", "SUPABASE_KEY": "k"})
    assert s.backend == "supabase" and s.base == "https://x.supabase.co/rest/v1"

    chamadas = []

    class R:
        def __init__(self, code=200, body=None): self.status_code, self._b, self.text = code, body, ""
        def json(self): return self._b

    class Sess:
        def request(self, method, url, headers=None, timeout=None, params=None, json=None):
            chamadas.append((method, url, params, json, headers))
            if method == "GET" and params.get("id"):
                return R(200, [{"id": "a", "doc": {"n": 1}}])
            if method == "GET":
                return R(200, [{"id": "a", "doc": {"n": 1}}, {"id": "b", "doc": {"n": 2}}])
            return R(201, None)

    sb = store.SupabaseStore("https://x.supabase.co", "k", session=Sess())
    sb.put("alertas", "a", {"n": 1})
    assert chamadas[-1][0] == "POST" and chamadas[-1][3] == {"id": "a", "doc": {"n": 1, "id": "a"}}
    assert "merge-duplicates" in chamadas[-1][4]["Prefer"] and chamadas[-1][4]["apikey"] == "k"
    assert sb.get("alertas", "a") == {"n": 1, "id": "a"} and len(sb.list("alertas")) == 2
    sb.delete("alertas", "a")
    assert chamadas[-1][0] == "DELETE" and chamadas[-1][2] == {"id": "eq.a"}
    with pytest.raises(store.StoreError):
        sb.put("alertas", "a", {"saldo": 1})
