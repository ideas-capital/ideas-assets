# CLAUDE.md — instruções para sessões do Claude neste repositório

## O projeto
IDEAS CAPITAL assets: terminal pessoal de investimentos no exterior de Renan Cotta (uso exclusivo dele).
Python 3.12 + Streamlit. Tudo em pt-BR: interface, comentários, docs. Custo operacional zero.

## Filosofia (não violar sem avisar)
- Núcleo-Satélite: 80–90% preservação (carteiras-modelo, renda fixa), 10–20% satélite.
- Laboratório de swing limitado (padrão US$ 5 mil, 1% de risco por operação, stop em ATR).
- Regras fixas e backtests honestos: sinal no fechamento, execução na ABERTURA seguinte, custos incluídos.
- Só candles diários/semanais (dados intradiários grátis não sustentam backtest).
- A IA interpreta números calculados em Python; nunca inventa níveis nem "confiança X%".
- Uso pessoal: o app pode recomendar (COMPRA/AGUARDAR/SAIR...), mas sempre mostrando o histórico
  real da regra naquele ativo (setups com histórico fraco aparecem como "EVITAR").

## Arquitetura
- `app.py`: marca, menu lateral próprio (`st.navigation(position="hidden")` + `st.page_link`),
  botões de estratégia (`st.session_state["estrategia_swing"]`), tema claro/escuro.
- `paginas/`: uma tela por arquivo. `terminal.py` é a inicial.
- `pwass/engine/`: funções puras e testadas. `swing.py` (3 estratégias + backtest), `strategies.py`
  (GEM/GTAA/carteiras), `backtest.py`, `factors.py` (QVM), `valuation.py`, `health.py` (semáforo), `radar.py`.
- `pwass/data/`: toda chamada de rede (Yahoo, FRED CSV, SEC, BCB SGS/Focus, Tesouro Transparente).
- `pwass/ai/`: `openrouter.py` (cliente OpenAI-compatível; prefixos `gemini:`/`ollama:`), `prompts.py`,
  `committee.py` (3 agentes + juiz), `documents.py`.
- `pwass/ui/`: `theme.py` (tokens claro/escuro aplicados em runtime + CSS + tabelas HTML),
  `tvchart.py` (Lightweight Charts v5 — manter o logo de atribuição da TradingView), `cache.py`, `settings.py`.
- `pwass/radar.py`: monta o Radar de ativos (usado pela página e por `scripts/gerar_radar.py`).
- `config/*.yaml`: parâmetros editáveis — preferir mudar config a mudar código.

## Convenções
- Antes de criar arquivo, verifique se já existe algo parecido (evitar duplicação).
- Cálculo novo vai para `pwass/engine/` com teste em `tests/`; rede vai para `pwass/data/` com cache em `pwass/ui/cache.py`.
- Cores só via tokens de `theme.py` (`var(--up)`, `var(--down)`, ...), para funcionar nos dois temas.
- Números exibidos no formato brasileiro (`theme.num`, `theme.pct`).
- Nunca commitar segredos, saldos ou dados pessoais (`.streamlit/secrets.toml`, `*.local.yaml`, `vault/`).
- Rodar `pytest` antes de commitar.

## Roadmap
1. Módulo de carteira (posições locais em `*.local.yaml`, limites do Satélite, rebalanceamento).
2. Diário de operações do laboratório (registrar sinais seguidos e medir acerto real vs backtest).
3. Módulo fiscal (Lei 14.754, custo médio do dólar).
4. Protocolo de Emergência / sucessão (local, cifrado).
5. Fundamentos oficiais via edgartools (XBRL da SEC).

## Redesign v5 (em andamento)
Design System: `docs/redesign/DESIGN-SYSTEM.md`; tokens em `pwass/ui/tokens.py` (fonte única de cores; `.streamlit/config.toml` espelha). Componentes novos em `pwass/ui/components.py`.
Instruções completas em `docs/redesign/PROMPT-REDESIGN-v5.md`; progresso em `docs/redesign/PROGRESSO.md`.
Trabalhar na branch `redesign-v5` e retomar sempre pela próxima ação registrada no PROGRESSO.
