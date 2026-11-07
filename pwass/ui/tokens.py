"""Tokens do Design System (fonte única de cores e escalas).

Tudo que é cor ou escala nasce aqui; `theme.py` injeta no CSS, `.streamlit/config.toml`
espelha os mesmos valores para o tema nativo, e gráficos leem de `THEMES[modo]`.

Exemplo:
    >>> from pwass.ui import tokens
    >>> tokens.THEMES["dark"]["up"]
    '#10B981'
    >>> tokens.contrast("#FFFFFF", "#000000")
    21.0

Ajustes em relação ao prompt v5 (§3.2), exigidos pelo teste de contraste WCAG AA:
- dark `down` #EF4444 → #F87171 e `indicator` #A855F7 → #C084FC (texto em cartões elevados);
- light `up` #059669 → #047857, `down` #DC2626 → #CC2222 e `text-muted` #64748B → #5B6B82.
As cores de SÉRIES (SERIES) são elementos gráficos (≥3:1 nos dois fundos) e não mudam entre temas;
por isso mm50, bollinger e candle_up são um pouco mais escuros que os do prompt.
"""
from __future__ import annotations

THEMES: dict[str, dict[str, str]] = {
    "dark": {"bg": "#0B1019", "bg2": "#101827", "surface": "#151D2B", "surface_raised": "#1B2638",
             "border": "#263247", "text": "#F1F5F9", "text_muted": "#94A3B8",
             "primary": "#2563EB", "primary_text": "#60A5FA",
             "up": "#10B981", "down": "#F87171", "warn": "#F59E0B", "indicator": "#C084FC",
             "grid": "#1A2333"},
    "light": {"bg": "#F5F7FA", "bg2": "#FFFFFF", "surface": "#FFFFFF", "surface_raised": "#F1F5F9",
              "border": "#E2E8F0", "text": "#172033", "text_muted": "#5B6B82",
              "primary": "#2563EB", "primary_text": "#2563EB",
              "up": "#047857", "down": "#CC2222", "warn": "#B45309", "indicator": "#9333EA",
              "grid": "#EEF2F6"},
}

# Cores de série dos gráficos — iguais nos dois temas (§3.2).
SERIES = {"mm20": "#3B82F6", "mm50": "#EA580C", "mm200": "#A855F7", "bollinger": "#6B7A90",
          "rsi": "#A855F7", "macd": "#3B82F6", "macd_signal": "#EA580C",
          "candle_up": "#059669", "candle_down": "#EF4444"}

# Escalas (px). Tipografia: Inter com fallback do sistema.
SPACE = (4, 8, 12, 16, 24, 32, 48)
RADIUS = {"control": 6, "card": 10}
FONT = {"page_title": 24, "section": 18, "card": 14, "body": 14, "aux": 12, "kpi": 26}
FONT_FAMILY = "Inter, -apple-system, 'Segoe UI', Roboto, sans-serif"
BREAKPOINTS = {"desktop": 1280, "tablet": 768}

# Semântica fixa dos selos de status (§5): nome → tipo de cor.
BADGE_KIND = {"COMPRA": "ok", "PERTO": "info", "EM POSIÇÃO": "info", "AGUARDAR": "mute",
              "EVITAR": "bad", "SAIR": "warn"}

# Chaves antigas (v4) que as páginas ainda usam → chave nova. Remover quando as páginas migrarem.
LEGACY = {"panel": "surface", "panel2": "surface_raised", "muted": "text_muted",
          "accent": "primary", "accent2": "primary_text"}


def theme_tokens(mode: str) -> dict[str, str]:
    """Tokens do modo, já com os apelidos v4 (`panel`, `muted`, `accent`...) para compatibilidade."""
    t = dict(THEMES[mode])
    t.update({old: t[new] for old, new in LEGACY.items()})
    t["warn_text"] = t["warn"]
    return t


def _lum(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a: str, b: str) -> float:
    """Razão de contraste WCAG 2.1 entre duas cores hex."""
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 2)
