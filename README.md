# IDEAS CAPITAL assets

Terminal pessoal de investimentos no exterior, em Python/Streamlit. Junta num lugar só:
radar de mercado, carteiras-modelo para o patrimônio de longo prazo, um laboratório de
swing trade com backtest real e um comitê de IA que dá a leitura final.

> **Uso pessoal.** O app recomenda com base em regras fixas e IA; a decisão, o aporte e o
> risco são exclusivamente do usuário.

## Rodar em 1 minuto

| Onde | Como |
|---|---|
| **Windows** | Duplo clique em `rodar.bat` (na 1ª vez instala tudo, ~2 min) |
| **Mac/Linux** | `./rodar.sh` |
| **Manual** | `python -m venv .venv` → ativar → `pip install -r requirements.txt` → `streamlit run app.py` |

Abre em `http://localhost:8501`. Para IA, copie `.streamlit/secrets.toml.example` para
`.streamlit/secrets.toml` e cole sua chave. Passo a passo completo, inclusive como publicar
na web só para você: **[docs/INSTALACAO.md](docs/INSTALACAO.md)**.

## O que tem

| Tela | O que faz |
|---|---|
| **Mercado hoje** (Terminal) | Regime, alertas, cotações com mini-gráficos, sinal do dia da estratégia ativa (entrada, stop, alvos e tamanho da posição), gráfico estilo TradingView, métricas reais do backtest, radar de sinais e comitê de IA |
| Radar de ativos | Semáforo de prudência: cripto, ações, ETFs, Treasuries, Tesouro Direto, Selic/CDI/IPCA e dólar |
| Estratégias e carteiras | 8 carteiras-modelo trocáveis para o Núcleo, sinais GEM/GTAA, backtest em USD ou em reais vs CDI |
| Scanner de ações | Nota Qualidade + Valor + Momento para ~100 empresas globais |
| Raio-X do ativo | Fundamentos, Piotroski, DCF reverso, gráfico, auditoria e debate por IA |
| Zonas de entrada | Suas faixas de preço com filtro anti-hype |
| Analista IA | Lê PDFs, prints de gráfico, filings da SEC e audita posts de terceiros |
| Guia e rotina | Como cada método funciona e a rotina de uso |

**Fora do app:** `RADAR.md` e `site/index.html` são atualizados todo dia útil pelo GitHub Actions.

## Organização

```
app.py                  marca, menu lateral, estratégia ativa, tema claro/escuro
paginas/                uma tela por arquivo (terminal.py é a inicial)
pwass/engine/           cálculos puros e testados: swing, estratégias, fatores, valuation, saúde
pwass/data/             Yahoo, FRED, SEC, Banco Central, Tesouro (toda chamada de rede)
pwass/ai/               OpenRouter / Gemini / Ollama, prompts, comitê de IA, leitura de documentos
pwass/ui/               tema, gráfico TradingView, cache, configurações
config/                 *.yaml editáveis: swing, radar, carteiras, universo, watchlist, IA
docs/                   GUIA.md (aparece no app) e INSTALACAO.md
scripts/                radar diário e relatório mensal (rodam no GitHub Actions)
tests/                  pytest (31 testes)
```

O pacote interno continua se chamando `pwass` (nome do projeto original); a marca no app é IDEAS CAPITAL assets.

## Regra de ouro
Saldos, números de conta, senhas e seeds nunca entram no repositório. `secrets.toml`, `*.local.yaml`,
`vault/` e `exports/` estão no `.gitignore`.
