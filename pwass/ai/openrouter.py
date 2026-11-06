"""Cliente de IA no formato OpenAI, usado com três provedores:

- OpenRouter (padrão): uma chave dá acesso a Claude, Gemini, GPT, DeepSeek,
  Perplexity e centenas de outros. Paga por uso. https://openrouter.ai/docs
- Gemini direto (Google AI Studio): Gemini Flash tem camada GRATUITA. Atenção:
  na camada grátis o Google pode usar o conteúdo para melhorar produtos —
  mande só dados de mercado, nunca dados pessoais.
- Ollama (local, no seu computador): grátis e privado, qualidade menor.

O modelo indica o provedor pelo prefixo:
  "anthropic/claude-haiku-5.5"   -> OpenRouter (sem prefixo)
  "gemini:gemini-3.8-flash"      -> Google AI Studio
  "ollama:qwen3:8b"              -> Ollama local
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import requests

BASE_URL = "https://openrouter.ai/api/v1"
APP_HEADERS = {"HTTP-Referer": "https://github.com/pwass-app", "X-Title": "PWASS"}

PROVIDERS = {
    "openrouter": {"nome": "OpenRouter", "base_url": BASE_URL, "env": "OPENROUTER_API_KEY"},
    "gemini": {"nome": "Google AI Studio", "env": "GEMINI_API_KEY",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    "ollama": {"nome": "Ollama (local)", "env": None,
               "base_url": os.getenv("OLLAMA_URL", "http://localhost:11434/v1")},
}


class OpenRouterError(RuntimeError):
    """Erro amigável de qualquer provedor de IA (nome mantido por compatibilidade)."""


@dataclass
class AIResult:
    text: str
    model: str
    cost_usd: float | None
    prompt_tokens: int | None
    completion_tokens: int | None


def split_model(model: str) -> tuple[str, str]:
    """'gemini:gemini-3.8-flash' -> ('gemini', 'gemini-3.8-flash'); sem prefixo -> OpenRouter."""
    prefix, _, rest = model.partition(":")
    if prefix in ("gemini", "ollama") and rest:
        return prefix, rest
    return "openrouter", model


def list_models(timeout: int = 30) -> list[dict]:
    """Catálogo público da OpenRouter (não precisa de chave)."""
    r = requests.get(f"{BASE_URL}/models", timeout=timeout)
    r.raise_for_status()
    return r.json()["data"]


def price_per_million(model: dict) -> tuple[float, float]:
    p = model.get("pricing", {})
    return float(p.get("prompt", 0)) * 1e6, float(p.get("completion", 0)) * 1e6


def user_message(text: str, image_urls: list[str] | None = None) -> dict:
    """Mensagem do usuário; imagens viram partes do conteúdo (modelos com visão)."""
    if not image_urls:
        return {"role": "user", "content": text}
    parts = [{"type": "text", "text": text}]
    parts += [{"type": "image_url", "image_url": {"url": u}} for u in image_urls]
    return {"role": "user", "content": parts}


def build_payload(model: str, messages: list[dict], temperature: float = 0.3,
                  max_tokens: int = 6000, web_search: bool = False) -> dict:
    provider, model_id = split_model(model)
    payload = {"model": model_id, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    if web_search and provider == "openrouter":
        payload["plugins"] = [{"id": "web"}]  # busca na web, cobrada à parte pela OpenRouter
    return payload


def chat(api_key: str | None, model: str, messages: list[dict], *, temperature: float = 0.3,
         max_tokens: int = 6000, web_search: bool = False, timeout: int = 240) -> AIResult:
    provider, model_id = split_model(model)
    cfg = PROVIDERS[provider]
    if cfg["env"] and not api_key:
        raise OpenRouterError(f"Informe a chave do {cfg['nome']} em Configurações.")
    headers = dict(APP_HEADERS) if provider == "openrouter" else {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = build_payload(model, messages, temperature, max_tokens, web_search)
    try:
        r = requests.post(f"{cfg['base_url']}/chat/completions", json=payload,
                          headers=headers, timeout=timeout)
    except requests.RequestException as e:
        hint = " (o Ollama está aberto?)" if provider == "ollama" else ""
        raise OpenRouterError(f"Falha de conexão com {cfg['nome']}{hint}: {e}") from e
    try:
        data = r.json()
    except ValueError:
        data = {}
    if isinstance(data, list):  # o Gemini às vezes devolve o erro dentro de uma lista
        data = data[0] if data else {}
    if r.status_code != 200 or "error" in data:
        err = data.get("error") or {}
        msg = err.get("message") if isinstance(err, dict) else str(err)
        hint = {401: " (chave inválida)", 402: " (sem créditos)", 403: " (sem permissão)",
                429: " (limite de uso; tente em instantes)"}
        raise OpenRouterError(f"{cfg['nome']} {r.status_code}{hint.get(r.status_code, '')}: "
                              f"{msg or r.text[:300]}")
    message = data["choices"][0]["message"]
    usage = data.get("usage") or {}
    return AIResult(
        text=message.get("content") or "",
        model=f"{provider}:{data.get('model', model_id)}" if provider != "openrouter" else data.get("model", model),
        cost_usd=usage.get("cost") if provider == "openrouter" else (0.0 if provider == "ollama" else None),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
    )
