from pwass.data import status


def test_checar_isola_falhas_e_mede():
    def ok(): return "06/11/2026"
    def quebra(): raise RuntimeError("HTTP 429 " + "x" * 400)
    r = status.checar({"A": ok, "B": quebra, "C": ok})
    assert [x["fonte"] for x in r] == ["A", "B", "C"] and [x["ok"] for x in r] == [True, False, True]
    assert r[0]["ultimo_dado"] == "06/11/2026" and r[1]["ultimo_dado"] == "—" and len(r[1]["erro"]) <= 160 and r[1]["latencia_s"] >= 0
