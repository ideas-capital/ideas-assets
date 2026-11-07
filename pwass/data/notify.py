"""Envio opcional de alertas por Telegram. Sem credenciais, nada é enviado (os alertas ficam só no app)."""
from __future__ import annotations

import requests


def formatar(disparados: list[dict], data_ref: str) -> str:
    """Texto do aviso. Só tickers, valores e a data de referência — nada pessoal."""
    linhas = [f"IDEAS CAPITAL assets · alertas de {data_ref}"] + [f"• {d['mensagem']}" for d in disparados]
    linhas.append("Dados diários do Yahoo Finance; decisão e risco são seus.")
    return "\n".join(linhas)


def telegram(token: str | None, chat_id: str | None, texto: str, sessao=None) -> bool:
    """True se enviou. Sem token/chat_id → False (sem erro)."""
    if not token or not chat_id:
        return False
    r = (sessao or requests).post(f"https://api.telegram.org/bot{token}/sendMessage",
                                  json={"chat_id": chat_id, "text": texto, "disable_web_page_preview": True}, timeout=20)
    r.raise_for_status()
    return True
