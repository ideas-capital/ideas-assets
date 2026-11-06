# MASTER PROMPT — IDEAS CAPITAL assets v5
## Redesign de UX/UI, Design System e inteligência de análise

> **Como usar:** abra o Claude Code (Opus ou Sonnet) conectado ao repositório `ideas-capital-assets` e envie:
> *"Leia `CLAUDE.md` e `docs/redesign/PROMPT-REDESIGN-v5.md` e execute a próxima fase pendente. Registre o progresso em `docs/redesign/PROGRESSO.md`."*
> O trabalho foi dividido em sessões curtas para economizar créditos. Cada sessão retoma a partir do `PROGRESSO.md`.

---

## 0. Papel e postura

Você vai atuar como Product Designer sênior, engenheiro de frontend Python/Streamlit e especialista em visualização de dados financeiros.

- Você é o responsável pela evolução do produto.
- Decida com autonomia, mas não altere em silêncio cálculos, regras de estratégia, fontes de dados ou funcionalidades.
- O app é de **uso pessoal e exclusivo do dono (Renan Cotta)**. Não há regras de CVM nem plano pago. Não crie upsell, login multiusuário, "Plano Pro" ou recursos de rede social (aba "Discussão", comentários, etc.).
- O rodapé de responsabilidade pessoal que já existe deve ser mantido.

---

## 1. O que já existe (não precisa redescobrir)

Leia primeiro `CLAUDE.md`, `README.md`, `docs/GUIA.md` e `docs/INSTALACAO.md`. Resumo do estado atual (v4):

| Camada | Onde | Observação |
|---|---|---|
| Framework | Streamlit 1.67, Python 3.12 | **Manter.** Não migrar para React/Next. |
| Navegação | `app.py` | `st.navigation(position="hidden")` + `st.page_link` em sidebar customizada; dicionário `MENU` |
| Tema | `pwass/ui/theme.py` | Tokens `TOKENS["dark"/"light"]`, CSS injetado, componentes HTML (`card`, `badge`, `table`, `sparkline`, `signal_box`…). Troca via `st._config.set_option` (API privada, global ao processo) |
| Gráfico principal | `pwass/ui/tvchart.py` | `streamlit-lightweight-charts-v5` (TradingView, Apache-2.0: **manter o logo de atribuição**) |
| Gráficos analíticos | `pwass/ui/charts.py` | Plotly com `layout()` sensível ao tema |
| Dados | `pwass/data/` | yfinance, FRED (CSV sem chave), SEC EDGAR, BCB SGS/Focus, Tesouro Transparente. Cache em `pwass/ui/cache.py` |
| Motores | `pwass/engine/` | `swing.py` (3 estratégias + backtest + plano ATR), `health.py` (semáforo), `strategies.py` / `backtest.py` (carteiras em BRL vs CDI), `factors.py`, `valuation.py`, `indicators.py`; `pwass/radar.py` |
| IA | `pwass/ai/` | Cliente OpenAI-compatível multi-provedor (OpenRouter / `gemini:` / `ollama:`), comitê de 3 agentes + juiz, presets em `config/ai.yaml` |
| Páginas | `paginas/` | `terminal.py` (Mercado hoje, padrão), `radar_ativos.py`, `estrategias.py`, `scanner.py`, `ativo.py`, `radar.py` (Zonas de entrada), `analista.py`, `guia.py`. **`mercado.py` está fora do menu**: avalie fundir ou remover |
| Config | `config/*.yaml` | `swing.yaml`, `estrategias.yaml`, `radar.yaml`, `universe.yaml`, `watchlist.yaml`, `ai.yaml` |
| Automação | `.github/workflows/` | `radar-diario.yml` (gera `RADAR.md` e `site/`), `relatorio-mensal.yml` |
| Testes | `tests/` | 31 testes em pytest |

**Deploy:** Streamlit Community Cloud, app privado, publicado a partir da branch `main`.
Restrições que isso impõe:
- **Disco efêmero:** arquivos gravados pelo app somem a cada reinício.
- **Até ~2,7 GB de RAM.**
- **O app dorme** depois de 12 h sem uso.
- **Só dependências pip,** sem pacotes de sistema (apt).

---

## 2. Regras invioláveis

### 2.1 Integridade financeira
1. Não altere fórmulas, regras de entrada/saída, custos (0,10% por lado), execução na abertura seguinte nem o dimensionamento por ATR sem justificativa escrita e teste que prove a equivalência ou a correção.
2. Nunca ajuste backtest para melhorar resultado.
3. Nunca use dados fictícios em produção.
   - Fixtures e mocks só em `tests/`.
   - O mockup de referência tem números inventados (ex.: "Market Cap" do SPY, "Sentimento 73%"); não copie números.
4. Todo número exibido precisa de **fonte** e **data/hora de referência** visíveis, no componente ou num tooltip.
5. Dado ausente aparece como indisponível (`—` + motivo no tooltip). Nunca o substitua por estimativa sem rótulo.
6. Diferencie visualmente **observado**, **calculado**, **simulado/backtest** e **interpretação da IA**.
7. Respeite as classes de ativo:
   - ETF não tem P/L de empresa nem market cap de empresa.
   - Cripto negocia 7 dias por semana, enquanto ações e ETFs negociam só em dias úteis.
   - Não misture calendários em correlações e comparações sem alinhar as datas.
8. Moeda sempre explícita (US$, R$). Conversão só pela PTAX ou pelo câmbio do yfinance, com a fonte indicada.

### 2.2 Segurança
- Nunca commitar segredos: `.streamlit/secrets.toml`, `*.local.yaml`, `vault/`, `exports/` continuam no `.gitignore`.
- Nada de seed phrase, senha, número de conta ou saldo em código, config versionada ou logs.
- Não envie dados pessoais do dono para serviços externos. O User-Agent da SEC vem de `secrets`.

### 2.3 Engenharia
- Trabalhe na branch **`redesign-v5`**. Faça commits pequenos e lógicos por etapa e abra um PR para `main` no fim. Não quebre o app publicado no meio do caminho.
- Separe as camadas:
  - **dados** (`pwass/data`);
  - **cálculo** (`pwass/engine`);
  - **apresentação** (`pwass/ui`, `paginas`).
- Página não calcula indicador nem chama API direto.
- Nenhuma cor hardcoded em página. Tudo vem dos tokens.
- Antes de adicionar uma dependência, justifique (ganho, licença, peso, compatibilidade com Streamlit Cloud). Prefira o que já está no `requirements.txt`.
- Nenhum botão ou controle sem ação. Se algo não puder ser feito (falta de API, dado ou chave), não o mostre e documente em `PENDENCIAS.md`.
- Não lute contra o framework. Quando o Streamlit não permitir algo (ex.: tooltips na sidebar recolhida), adote a alternativa nativa mais próxima e registre a decisão.

### 2.4 Economia de créditos e de contexto
- Não releia arquivos grandes inteiros sem necessidade. Use busca e trechos.
- Ao fim de cada fase, atualize `docs/redesign/PROGRESSO.md` com: o que foi feito, commits, testes, o que falta e a próxima ação exata.
- Se o contexto estiver acabando, pare num ponto estável, faça commit e atualize o `PROGRESSO.md`.

### 2.5 Ambiente de execução
- No início, teste se há acesso à internet para Yahoo, FRED, BCB e SEC (uma chamada curta de cada).
- Se a rede estiver bloqueada, valide com **fixtures gravadas** em `tests/fixtures/` (parquet pequeno com OHLCV real de poucos ativos). Diga isso no relatório.
- Rode `pytest` e um smoke test de **todas** as páginas com `streamlit.testing.v1.AppTest` (caminho absoluto + `PYTHONPATH`) nos dois temas.
- Se o Playwright estiver disponível, gere screenshots em `docs/redesign/screens/` (desktop 1440 px e mobile 390 px, dark e light).

---

## 3. Direção visual

### 3.1 Identidade
- **Dark Professional** é o padrão; **Light Clean** é a alternativa completa.
- Mesma estrutura e mesmos componentes nos dois. Só os tokens mudam.
- Logo: use `assets/logo.svg` (ou `.png`) via `st.logo()` se existir. Se não existir, mantenha a marca "IC" atual e registre a pendência. Não invente outro logo.

### 3.2 Tokens iniciais

Ajuste se for preciso para atingir **WCAG AA**: contraste ≥ 4,5:1 para texto e ≥ 3:1 para elementos gráficos. Valide com um teste automatizado de contraste.

| Token | Dark | Light |
|---|---|---|
| `bg` | #0B1019 | #F5F7FA |
| `bg2` | #101827 | #FFFFFF |
| `surface` (card) | #151D2B | #FFFFFF |
| `surface-raised` | #1B2638 | #F1F5F9 |
| `border` | #263247 | #E2E8F0 |
| `text` | #F1F5F9 | #172033 |
| `text-muted` | #94A3B8 | #64748B |
| `primary` | #2563EB (texto sobre escuro: #60A5FA) | #2563EB |
| `up` | #10B981 | #059669 |
| `down` | #EF4444 | #DC2626 |
| `warn` | #F59E0B | #B45309 |
| `indicator` | #A855F7 | #9333EA |
| `grid` (gráfico) | #1A2333 | #EEF2F6 |

Cores de série fixas nos dois temas:
- MM20 azul;
- MM50 laranja;
- MM200 roxo;
- Bollinger cinza;
- RSI roxo;
- volume com a cor do candle a 40% de opacidade.

Defina-as num só lugar (`pwass/ui/tokens.py`).

### 3.3 Escalas
- **Tipografia:** Inter (Google Fonts via `[theme] font` / `fontFaces`, ou fallback do sistema).
  - Título de página: 24 px.
  - Seção: 18 px.
  - Card: 14 px.
  - Corpo: 14 px.
  - Auxiliar: 12 px (mínimo 11 px).
  - KPI: 24–28 px com números tabulares (`font-variant-numeric: tabular-nums`).
- **Espaçamento:** 4 · 8 · 12 · 16 · 24 · 32 · 48.
- **Raio:** 6 (controles) · 10 (cards).
- **Sombras:** só no tema claro e discretas.
- **Breakpoints:** ≥1280 (desktop), 768–1279 (notebook/tablet), <768 (mobile: colunas empilham, tabelas com scroll horizontal, gráfico com altura reduzida e legível).

### 3.4 Evitar
- Card dentro de card.
- Borda em tudo.
- Gradientes.
- Gauges decorativos.
- Badge colorido para informação neutra.
- A mesma informação repetida em várias regiões da tela.
- Fonte miúda para caber colunas.
- Animações.

---

## 4. Tema: implementação correta no Streamlit

O Streamlit 1.67 aceita `[theme.light]`, `[theme.dark]`, `[theme.light.sidebar]` e `[theme.dark.sidebar]` no `config.toml`. O usuário alterna pelo menu do app (Light / Dark / System), e `st.context.theme.type` informa o tema ativo.

1. Defina os dois temas completos em `.streamlit/config.toml`, com cores, fonte e sidebar, a partir dos tokens.
2. Faça o CSS próprio (`theme.inject()`), o gráfico TradingView e o Plotly lerem o tema ativo via `st.context.theme.type`. Fallback: o tema padrão do config.
3. **Remova** o `st._config.set_option`: é API privada e global ao processo.
4. Seletor Dark / Light / Sistema dentro do app:
   - Use o mecanismo nativo se existir uma forma suportada de acioná-lo.
   - Se não existir, mantenha só o menu nativo e mostre uma dica curta na sidebar de onde trocar.
   - Verifique se a escolha persiste por navegador e documente o resultado.
5. Teste: trocar o tema não pode deixar nenhum componente (tabela HTML, popover, tooltip, gráfico, sparkline, badge) com cor do tema anterior.

Se `st.context.theme` não disparar rerun ao trocar o tema, documente e use a alternativa mais simples que funcione (ex.: parâmetro `?tema=` na URL + `st.query_params`).

---

## 5. Design System (`pwass/ui/`)

Organize em módulos pequenos e documentados (docstring com exemplo):

- `tokens.py`: cores dos dois temas, escalas, cores de séries.
- `theme.py`: aplicação do tema, CSS global, formatação (`pct`, `num`, `money`, `esc`).
- `components.py`, um componente por função, cada um com estados **normal / carregando / vazio / erro**:

| Componente | O que mostra |
|---|---|
| `page_header` | título, subtítulo, fonte/atualização, ações |
| `topbar` | busca global, contexto, alertas, status dos dados |
| `kpi` | valor, variação, sparkline opcional, fonte |
| `ticker_strip` | faixa de cotações configurável |
| `asset_header` | nome, ticker, mercado, classe, preço, variação, favorito, horário |
| `badge` | status com semântica fixa: COMPRA, PERTO, EM POSIÇÃO, AGUARDAR, EVITAR, SAIR |
| `data_table` | padrão global de tabela (ver §8) |
| `chart_container` | título, controles, gráfico, legenda e fonte |
| `insight_card` | observado → interpretação → limitação |
| `empty_state` / `error_state` | com motivo e ação sugerida |
| `source_note` | "Fonte: Yahoo Finance · 06/11/2026 18:05 BRT · diário" |

- `tvchart.py` (TradingView) e `charts.py` (Plotly), ambos com o mesmo tema e as mesmas cores de série.

Escreva o catálogo em `docs/redesign/DESIGN-SYSTEM.md` e crie uma página oculta `paginas/_componentes.py` (fora do menu, acessível por URL) que renderiza todos os componentes nos estados possíveis. Ela serve de checagem visual.

---

## 6. Navegação

Menu enxuto, sem perder função. Proposta (avalie e ajuste):

| Seção | Páginas | Origem |
|---|---|---|
| **Visão geral** | Painel (Mercado hoje) · Radar de mercado | `terminal.py` · `radar_ativos.py` (+ `mercado.py` fundido onde fizer sentido) |
| **Análise** | Ativo · Scanner · Comparar · Zonas de entrada | `ativo.py` + parte técnica do terminal · `scanner.py` · **novo** · `radar.py` |
| **Estratégias** | Laboratório de swing · Carteiras do Núcleo | **novo** (as 3 estratégias numa página com seletor e comparação) · `estrategias.py` |
| **Inteligência** | Analista IA · Alertas e watchlist | `analista.py` · **novo** |
| **Sistema** | Relatórios · Configurações e fontes · Guia | **novo** · `settings.py` + status das fontes + "Sobre" · `guia.py` |

- **Não** crie três itens de menu (Swing, Cruzamento, Rompimento) para a mesma página. A estratégia é um seletor, como já é hoje.
- Sidebar:
  - logo;
  - seções com `st.page_link` (ícones Material);
  - página ativa destacada;
  - seletor de estratégia só onde for usado;
  - status do mercado (aberto/fechado NYSE e B3, calculado pelo calendário e pelo horário, com a fonte indicada);
  - atalho para Configurações.
- **Topbar** (componente chamado no topo de cada página): busca global, contexto, popover de alertas (contagem real) e "Dados de: <data/hora>" com indicação de atraso.
- **Busca global:** `st.selectbox` com o universo configurado (`universe.yaml` + `swing.yaml` + `watchlist.yaml`), com nome e classe. Aceite ticker livre validado no yfinance; o sufixo `.SA` cobre a B3. Ao escolher, abre a página Ativo (`st.switch_page` + `st.query_params["t"]`).

---

## 7. Páginas

Prioridade de execução: 1 → 9. Cada página tem **um objetivo**, cabeçalho padrão, fonte/data visível, estados vazio/erro e funciona nos dois temas e no mobile.

### 7.1 Painel (Mercado hoje)
Objetivo: em 30 segundos saber o regime e se há algo a fazer hoje.
1. **Faixa de mercado** configurável: S&P 500, Nasdaq 100, Dow, Ibovespa, BTC, ETH, ouro, USD/BRL, VIX, US10Y. Cada item mostra último valor, variação, sparkline e horário.
2. **Inteligência de mercado:** regime (já existe), amplitude (% de ativos acima da MM200), volatilidade (VIX e seu percentil), tendência predominante, eventos da semana (resultados das empresas da watchlist via calendário do yfinance, se disponível) e alertas.
   - **Nada de "Sentimento %"** sem metodologia. Se criar um índice, ver §9.2.
3. **Ativo em destaque:** gráfico TradingView grande, com indicadores ligáveis.
4. **Oportunidades:** tabela do scanner de swing (status, qualidade do histórico, plano).
5. **Insights:** o que mudou desde o último pregão (novos sinais, saídas, ativos que cruzaram a MM200), sem repetir o que já está acima.

### 7.2 Ativo (página mais importante)
- Cabeçalho do ativo, com ★ que adiciona à watchlist.
- Abas:
  - **Visão geral:** gráfico, performance 1M/3M/6M/1A/5A, sinais ativos, semáforo.
  - **Técnica:** candles, MM/EMA, Bollinger, RSI, **MACD** (novo), volume, Fibonacci e suporte/resistência por pivôs, tudo ligável.
  - **Fundamentos:** só para ações; inclui Piotroski, valuation reverso e saúde financeira. ETF mostra taxa, AUM e composição, quando disponíveis.
  - **Histórico:** trades do backtest de cada estratégia neste ativo e suas métricas.
  - **Notícias e eventos:** yfinance `news`/`calendar` e filings da SEC (8-K, 10-Q). Mostrar só o que vier com fonte e link.
- Fundir aqui o "Raio-X" atual. Nenhuma métrica incompatível com a classe do ativo.

### 7.3 Scanner
- Filtros combináveis: classe, setor, variação, volume relativo, RSI, posição vs MM50/MM200, market cap (só ações), tendência, sinal por estratégia, profit factor, volatilidade (ATR%).
- Critérios aplicados sempre visíveis em chips.
- Filtros salvos (ver §10, persistência).
- Exportação CSV/XLSX.

### 7.4 Laboratório de swing
- Seletor de estratégia e ficha da estratégia: regras de entrada/saída, indicadores, timeframe (diário), custos, fonte bibliográfica.
- Métricas: taxa de acerto, profit factor, retorno acumulado, drawdown máximo, nº de operações, média, ganho médio, perda média, exposição (% do tempo posicionado), comparação com buy & hold.
- Gráficos: curva de capital, drawdown, histograma de resultados por operação, retorno por ano, comparação entre as 3 estratégias.
- Separe **backtest** de **operações reais** (diário de trades, ver §9.5) com rótulos e cores distintos.
- Mostre o aviso de viés de sobrevivência do universo.

### 7.5 Carteiras do Núcleo
Manter o que existe (backtest em BRL vs CDI, QuantStats) no novo padrão visual. Acrescentar a comparação lado a lado de 2–3 carteiras.

### 7.6 Zonas de entrada
- Zonas da watchlist sobre o gráfico (retângulos/linhas), com suporte, resistência, zona de compra, stop, alvos e R/R.
- Cada zona traz a justificativa técnica e o dado de origem.

### 7.7 Analista IA
- A IA recebe **apenas** dados calculados pelo app, num bloco JSON com data de referência.
- Resposta em formato fixo:
  - **Dados observados**;
  - **Interpretação**;
  - **Hipóteses**;
  - **Decisão** (COMPRAR/AGUARDAR/MANTER/REDUZIR/VENDER/EVITAR + convicção baixa/média/alta, sem %);
  - **Riscos e limitações**.
- Mostre o modelo usado, o custo e a data.
- Salve as análises no armazenamento persistente (§10).

### 7.8 Relatórios
- PDF e Excel com identidade visual: resumo, regime, oportunidades, estratégias, riscos, histórico, gráficos, data de geração e fontes.
- Use bibliotecas pip puras (ex.: `fpdf2` ou `reportlab` + `openpyxl`). Nada que dependa de pacote de sistema.
- Reaproveite `scripts/relatorio_mensal.py`. Os valores devem bater exatamente com o app (teste).

### 7.9 Guia, Configurações e Fontes
- O Guia é atualizado para a nova navegação.
- Configurações: chaves de IA, presets, tema padrão, ativos da faixa de mercado, parâmetros de risco (leitura do YAML).
- Fontes: status de cada fonte (ok / falha / última atualização).
- Sobre: versão e responsabilidade pessoal.

---

## 8. Padrão de tabelas

- Use **`st.dataframe` com `column_config`** como padrão: ordenação, scroll, cabeçalho fixo, `NumberColumn` com formato, `ProgressColumn`, `LineChartColumn` para tendência, `LinkColumn`. É nativo, sensível ao tema e virtualizado.
- Tabela HTML customizada só onde o `dataframe` não atende (ex.: badges de status). Nesse caso, ela tem de suportar tema, scroll horizontal e alinhamento numérico.
- Colunas configuráveis (`column_order`), seleção de linha abrindo o Ativo (`on_select`), exportação CSV/XLSX.
- Números alinhados à direita, %, moeda, `—` para ausente.

---

## 9. Inteligência com utilidade real

### 9.1 Explicação de divergências
Para cada sinal, gere uma lista de **fatores a favor e contra**, todos calculados por regras determinísticas a partir dos motores existentes. Exemplos:
- "RSI(2) em sobrevenda" (a favor);
- "abaixo da MM200" (contra);
- "volume 0,6× a média" (contra);
- "regime DEFENSIVO" (contra).

A IA pode reescrever a explicação em linguagem natural, mas os fatores vêm do código.

### 9.2 Score de qualidade do sinal
Só crie o score se ele passar na validação:
1. Defina componentes (tendência, momento, volume, volatilidade, confirmação de outras estratégias, regime, histórico da regra no ativo) e pesos em `config/score.yaml`.
2. Documente a metodologia em `docs/redesign/SCORE.md`.
3. **Valide:** no backtest, os sinais com score alto precisam ter resultado médio melhor que os de score baixo, fora da amostra (ex.: calibrar até 2019 e testar de 2020 em diante). Publique a tabela por faixa de score.
4. Se não houver diferença significativa, **não mostre o score**. Mostre só o checklist de fatores e registre o resultado.

### 9.3 Watchlist
Múltiplas listas, adicionar/remover, ver sinais e variações, criar alerta a partir do ativo.

### 9.4 Comparar ativos
Novo:
- 2–4 ativos com performance normalizada (base 100) e mesmo período.
- Datas alinhadas (cripto × bolsa).
- Volatilidade anualizada, drawdown, retorno, correlação e indicadores escolhidos.

### 9.5 Alertas e diário de operações
- Alertas por preço, variação, RSI, cruzamento, rompimento, volume e sinal de estratégia, cada um ativável e configurável.
- A verificação roda no **GitHub Actions** (junto do radar diário). Envio opcional por Telegram (`TELEGRAM_BOT_TOKEN`/`CHAT_ID` em secrets) ou e-mail; sem credencial, os alertas aparecem só no app.
- **Diário de operações reais:** entrada, saída, motivo, print opcional. Comparação "o que fiz × o que a regra mandava".

---

## 10. Persistência

O Streamlit Cloud apaga os arquivos ao reiniciar. Crie `pwass/store.py` com uma interface única (`get/put/list/delete` por coleção) e dois backends:
- **Local** (padrão): arquivos `data/*.local.json`, ignorados pelo git.
- **Supabase** (opcional): ativado se existirem `SUPABASE_URL` e `SUPABASE_KEY` em secrets.
  - Tabelas: `watchlists`, `alertas`, `diario`, `analises_ia`, `filtros_salvos`.
  - Gere o SQL em `docs/redesign/supabase.sql` (com RLS ativo).
  - Mostre o backend ativo nas Configurações.

Nada sensível vai para o banco: sem saldo de conta, sem número de conta, sem seed.

---

## 11. Gráficos

- **Principal:** TradingView Lightweight Charts (já instalado). Não troque de biblioteca.
- Controles:
  - **intervalo** Diário / Semanal;
  - **período** 1M · 3M · 6M · 1A · 5A · Tudo;
  - indicadores ligáveis;
  - crosshair, zoom e legenda.
- **Intraday fica fora**: não há fonte gratuita confiável. Não mostre botão de intraday.
- **Analíticos** (curva de capital, distribuição, comparação): Plotly com `layout()` do tema. Não adicione ECharts.
- Cores de candles e séries idênticas nos dois temas (§3.2). Fonte e data abaixo de cada gráfico.

---

## 12. Fases e sessões

| Sessão | Fases | Entregáveis |
|---|---|---|
| **1** | Auditoria + plano + Design System | `docs/redesign/AUDITORIA.md` (achados objetivos, no máximo 2 páginas), `PLANO.md` (arquivos criados/alterados/descontinuados), tokens, temas no `config.toml`, `components.py`, página `_componentes`, sidebar e topbar, teste de contraste |
| **2** | Painel + Ativo + Scanner | Páginas no novo padrão, busca global, padrão de tabelas |
| **3** | Laboratório de swing + Carteiras + Zonas + Analista IA | Fusão das páginas, MACD/pivôs, formato fixo da IA |
| **4** | Watchlist, Comparar, Alertas, Diário, persistência | `store.py` (+ Supabase opcional), workflow de alertas |
| **5** | Relatórios + score (com validação) + Guia + Configurações | PDF/XLSX, `SCORE.md`, guia atualizado |
| **6** | Testes, screenshots, PR | Ver §13 |

Em cada sessão:
1. Leia `PROGRESSO.md`.
2. Execute.
3. Rode os testes.
4. Faça commit.
5. Atualize `PROGRESSO.md`.

---

## 13. Testes e critério de pronto

- `pytest` verde: os 31 testes antigos + novos.
- Testes novos:
  - **Regressão de números:** os resultados do backtest de swing e das carteiras para um conjunto fixo de fixtures têm de ser idênticos antes e depois do redesign.
  - Contraste dos tokens.
  - Formatação (`pct`, `money`, ausente → `—`).
  - Store local.
  - Score (se existir).
  - Relatório = valores do app.
- Smoke `AppTest` de todas as páginas, nos dois temas, sem exceção.
- Nenhuma cor hexadecimal em `paginas/*.py` (teste com grep).
- Screenshots desktop/mobile × dark/light das páginas principais.
- Checklist manual em `PROGRESSO.md`: navegação, busca, filtros, exportação, estados vazio/erro, mobile.

O trabalho só está pronto quando todas as páginas usarem o Design System, os dois temas estiverem completos e os números baterem com a versão anterior.

---

## 14. Entregáveis finais (em `docs/redesign/`)

1. `AUDITORIA.md`
2. `PLANO.md`
3. `DESIGN-SYSTEM.md` (paletas, escalas, componentes, exemplos)
4. `MUDANCAS.md` (páginas reformuladas, componentes criados/alterados, dependências adicionadas/removidas e o porquê)
5. `SCORE.md` (metodologia e validação, ou o motivo de não existir)
6. `PENDENCIAS.md` (o que não foi possível e por quê)
7. `PROXIMOS-PASSOS.md`
8. `screens/` (screenshots)
9. `README.md`, `CLAUDE.md` e `docs/GUIA.md` atualizados

---

## 15. Resultado esperado

Um terminal pessoal com:
- a profundidade de um terminal financeiro;
- a limpeza de um dashboard moderno;
- dois temas completos;
- navegação curta.

Cada número deve ter fonte e data, e cada sinal deve vir com a explicação do porquê.
Prioridade: **menos poluição, mais clareza; mais qualidade de análise, não mais indicadores; preservar o que funciona.**
