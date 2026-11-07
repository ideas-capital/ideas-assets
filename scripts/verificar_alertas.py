"""Verifica os alertas salvos no store e avisa por Telegram (opcional).

Uso (GitHub Actions ou local):  python scripts/verificar_alertas.py
- Lê alertas do Supabase (SUPABASE_URL/SUPABASE_KEY) ou de data/alertas.local.json.
- Se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID existirem, envia os disparados; senão só imprime.
- Não reenvia o mesmo alerta no mesmo dia (campo `ultimo_disparo` do alerta).
Sai com código 0 mesmo sem alertas ou sem credenciais (o workflow não deve falhar por isso).
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pwass import store  # noqa: E402
from pwass.data import market, notify  # noqa: E402
from pwass.engine import alertas  # noqa: E402


def main() -> int:
    st = store.get_store()
    lista = st.list("alertas")
    ativos = [a for a in lista if a.get("ativo", True)]
    print(f"Backend: {st.backend} · {len(ativos)} alerta(s) ativo(s) de {len(lista)}")
    if not ativos:
        return 0
    sw = yaml.safe_load((ROOT / "config" / "swing.yaml").read_text(encoding="utf-8"))
    tickers = sorted({a["ticker"] for a in ativos})
    dados = market.ohlcv(tickers, "5y")
    hoje = date.today().isoformat()
    disp = [d for d in alertas.avaliar_todos(ativos, dados, sw) if d["alerta"].get("ultimo_disparo") != hoje]
    for d in disp:
        print("DISPAROU:", d["mensagem"])
    if not disp:
        print("Nenhum alerta novo hoje.")
        return 0
    data_ref = max(df.index[-1] for df in dados.values()).strftime("%d/%m/%Y")
    texto = notify.formatar(disp, data_ref)
    enviado = notify.telegram(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"), texto)
    print("Telegram:", "enviado" if enviado else "sem credenciais — nada enviado")
    if enviado:  # só marca como enviado se de fato avisou
        for d in disp:
            st.put("alertas", d["alerta"]["id"], {**d["alerta"], "ultimo_disparo": hoje})
    return 0


if __name__ == "__main__":
    sys.exit(main())
