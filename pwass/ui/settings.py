"""Configurações do usuário (barra lateral) e chamada segura à IA.

Segurança das chaves (OpenRouter e Google AI Studio):
- No seu computador: defina OPENROUTER_API_KEY e/ou GEMINI_API_KEY.
- Na nuvem (uso pessoal): guarde as chaves em Settings → Secrets e ligue
  PWASS_USAR_CHAVE_DO_SERVIDOR = true.
- Também dá para colar a chave na barra lateral: fica só na sessão do navegador.
"""
from __future__ import annotations

import os

import streamlit as st

from pwass.ai import openrouter
from pwass.ui import cache

DEFAULT_SEC_UA = "PWASS app pessoal contato@exemplo.com"


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # noqa: BLE001 — sem arquivo secrets.toml
        return default


SESSION_KEYS = {"openrouter": "or_key", "gemini": "gemini_key"}


def api_key(provider: str = "openrouter") -> str | None:
    """Chave do provedor: sessão do navegador > variável de ambiente > secret do servidor (se liberado)."""
    if provider == "ollama":
        return None
    env = openrouter.PROVIDERS[provider]["env"]
    if st.session_state.get(SESSION_KEYS[provider]):
        return st.session_state[SESSION_KEYS[provider]]
    if os.getenv(env):
        return os.environ[env]
    if str(_secret("PWASS_USAR_CHAVE_DO_SERVIDOR", "false")).lower() == "true":
        return _secret(env)
    return None


def any_ai() -> bool:
    return bool(api_key("openrouter") or api_key("gemini"))


def sec_user_agent() -> str:
    return (st.session_state.get("sec_ua") or os.getenv("SEC_USER_AGENT")
            or _secret("SEC_USER_AGENT") or DEFAULT_SEC_UA)


def presets() -> dict:
    return cache.config("ai")["presets"]


def selected_model() -> str:
    """Modelo personalizado (se preenchido) > preset escolhido > preset padrão."""
    cfg = cache.config("ai")
    custom = (st.session_state.get("modelo_custom") or "").strip()
    preset = st.session_state.get("modelo_preset") or cfg["default"]
    return custom or cfg["presets"][preset]["model"]


def model_picker(key: str, default_preset: str | None = None, label: str = "Modelo") -> str:
    """Seletor de modelo para uma ação específica (sobrepõe o padrão)."""
    p = presets()
    names = list(p)
    current = selected_model()
    idx = names.index(default_preset) if default_preset in names else next(
        (i for i, n in enumerate(names) if p[n]["model"] == current), 0)
    choice = st.selectbox(label, names, index=idx, key=key,
                          format_func=lambda n: f"{p[n]['label']}  ·  US$ {p[n]['preco']}")
    return p[choice]["model"]


def estimate_cost(model: str, input_chars: int, out_tokens: int = 2500) -> float | None:
    for m in cache.ai_models():
        if m["id"] == model:
            pin, pout = openrouter.price_per_million(m)
            return (input_chars / 4) / 1e6 * pin + out_tokens / 1e6 * pout
    return None


def sidebar() -> None:
    with st.sidebar:
        with st.expander("Chaves de IA e modelos", icon=":material/key:", expanded=False):
            st.text_input("Chave da OpenRouter", type="password", key="or_key",
                          placeholder="sk-or-...",
                          help="Crie em openrouter.ai/keys. Fica só nesta sessão do navegador.")
            st.text_input("Chave do Google AI Studio (opcional)", type="password", key="gemini_key",
                          placeholder="AIza...",
                          help="Grátis em aistudio.google.com/apikey. Libera os modelos 'gemini:'.")
            p = presets()
            names = list(p)
            default = cache.config("ai")["default"]
            st.selectbox("Modelo padrão", names, key="modelo_preset", index=names.index(default),
                         format_func=lambda n: p[n]["label"],
                         help="Usado quando a tela não pede um modelo específico.")
            st.text_input("Modelo personalizado (opcional)", key="modelo_custom",
                          placeholder="ex.: anthropic/claude-opus-5.5",
                          help="Qualquer id da lista em openrouter.ai/models. Tem prioridade sobre o padrão.")
            found = [n for p, n in (("openrouter", "OpenRouter"), ("gemini", "Google")) if api_key(p)]
            st.caption(f"🔑 Chave detectada: {', '.join(found)}" if found
                       else "Sem chave: as funções de IA ficam desativadas (exceto Ollama local).")
        with st.expander("SEC (relatórios oficiais)", icon=":material/account_balance:"):
            st.text_input("Identificação para a SEC", key="sec_ua", placeholder="Seu Nome seu@email.com",
                          help="A SEC pede nome e e-mail de contato em cada requisição.")


def ask_ai(messages: list[dict], model: str | None = None, web: bool = False,
           temperature: float = 0.3) -> openrouter.AIResult | None:
    """Chama a IA mostrando erros de forma amigável. Retorna None se falhar."""
    model = model or selected_model()
    provider, _ = openrouter.split_model(model)
    key = api_key(provider)
    if provider != "ollama" and not key:
        name = openrouter.PROVIDERS[provider]["nome"]
        st.warning(f"Este modelo usa o {name}. Cole a chave na barra lateral (⚙️ Configurações).")
        return None
    try:
        with st.spinner(f"Consultando {model}..."):
            return openrouter.chat(key, model, messages, web_search=web, temperature=temperature)
    except openrouter.OpenRouterError as e:
        st.error(str(e))
        return None


def show_result(res: openrouter.AIResult, filename: str = "analise.md") -> None:
    st.markdown(res.text)
    cost = f" · custo US$ {res.cost_usd:.4f}" if res.cost_usd is not None else ""
    st.caption(f"Modelo: {res.model} · tokens {res.prompt_tokens or '?'} → {res.completion_tokens or '?'}{cost}")
    st.download_button("Baixar análise (.md)", res.text, file_name=filename, mime="text/markdown")
