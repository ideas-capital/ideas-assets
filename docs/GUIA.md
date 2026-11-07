# Guia do IDEAS CAPITAL assets

## Comece aqui

O IDEAS CAPITAL assets é um terminal pessoal para investir **no mercado externo** com regras, não com palpite. Ele junta três coisas:

1. **Dados gratuitos** — cotações (Yahoo Finance), macroeconomia dos EUA (FRED, do Federal Reserve) e relatórios oficiais das empresas (SEC EDGAR).
2. **Métodos publicados e testados** — estratégias de alocação e fatores de seleção de ações com décadas de evidência acadêmica.
3. **IA como segunda opinião** — via OpenRouter, para ler relatórios, prints de gráficos e auditar teses de terceiros.

**Mapa das telas**

| Tela | Para quê | Frequência |
|---|---|---|
| **Painel** | Regime, amplitude, VIX, sinal do dia, oportunidades, o que mudou e resumo de IA | Todo dia útil, 5 min |
| Radar de mercado | Semáforo de prudência: cripto, ações, ETFs, Treasuries, renda fixa BR e dólar | Quando quiser (também no RADAR.md) |
| **Ativo** | Estudar um ativo em abas: visão geral, técnica, fundamentos, histórico das regras, notícias, IA | Antes de qualquer compra |
| Scanner | Encontrar empresas de qualidade, baratas e com momento, com 10 filtros e filtros salvos | 1× por semana |
| Comparar | 2 a 4 ativos em base 100, volatilidade, queda e correlação | Quando for escolher entre ativos |
| Zonas de entrada | Suas faixas de preço com plano de risco, justificativa e filtro anti-hype | 1× por semana |
| **Laboratório de swing** | As 3 regras: ficha, métricas, curvas, comparação e suas operações reais | Quando quiser entender uma regra |
| Carteiras do Núcleo | Comparar carteiras-modelo (lado a lado); sinal mensal do GEM e do GTAA | 1× por mês |
| **Diário de operações** | Registrar o que você fez e comparar com o que a regra mandava | A cada operação |
| Analista IA | Análise estruturada de um ativo, relatórios, gráficos, filings e posts | Temporada de resultados |
| **Alertas e watchlist** | Listas de acompanhamento e alertas (preço, RSI, cruzamento, rompimento, volume, sinal) | Configure uma vez |
| Relatórios | PDF e Excel com o retrato de hoje | Quando quiser guardar ou enviar |
| Configurações e fontes | Chaves de IA detectadas, parâmetros, status das fontes e armazenamento | Quando algo falhar |

**Como as telas se ligam:** clicar numa linha de tabela (Painel, Scanner, Alertas) abre o Ativo; a busca do topo vai direto para um ativo; no Ativo, ★ favorita e "Criar alerta" cria um alerta. **Tema:** menu ⋮ do topo → Settings → Theme (claro, escuro ou sistema). **Dados do usuário** (watchlists, alertas, diário, análises) ficam em arquivos locais ou, se configurado, no Supabase; na nuvem sem Supabase eles somem a cada reinício.

**Score de qualidade do sinal:** foi testado fora da amostra e **não passou** (docs/redesign/SCORE.md), então o app não o mostra. No lugar, "Por que este sinal?" lista fatores a favor e contra calculados por regras.

> Ferramenta de uso pessoal. As recomendações vêm de regras fixas e de IA; a decisão, o aporte e o risco são exclusivamente do usuário.

## A estratégia

**Núcleo-Satélite**

- **Núcleo (80–90%)**: preservação. ETFs amplos (ações globais), Treasuries/T-Bills e renda fixa de qualidade. As telas *Estratégias* e *Mercado* servem a ele.
- **Satélite (10–20%)**: apostas de crescimento — ações individuais e, no máximo, BTC/ETH. As telas *Scanner*, *Ativo* e *Zonas de entrada* servem a ele.
- Limites padrão (em `config/watchlist.yaml`): 20% no satélite, 5% por ação, 5% em cripto.

**O alerta mais importante para quem mora no Brasil: domicílio do ETF**

ETFs domiciliados nos EUA (VOO, VT, SCHD, SGOV, BIL...) são "ativos americanos" para o **Estate Tax** (imposto de herança dos EUA). Para não residentes, só os primeiros **US$ 60 mil** são isentos; o excedente paga de 18% a 40%. Contas com TOD ou conjuntas (JTWROS) evitam o inventário americano, **mas não esse imposto**. Além disso, sem tratado Brasil–EUA, dividendos americanos sofrem **30%** de retenção.

ETFs **UCITS** domiciliados na Irlanda (listados em Londres) dão a mesma exposição sem Estate Tax e com 15% de retenção dentro do fundo. Exemplos que o app usa:

| Exposição | EUA | UCITS (Irlanda) |
|---|---|---|
| S&P 500 | SPY / VOO | CSPX.L ou VUAA.L |
| Mundo todo | VT | VWRA.L |
| Mundo ex-EUA | VEU | EXUS.L |
| Emergentes | EEM | EIMI.L |
| T-Bills (caixa em dólar) | BIL / SGOV | IB01.L |
| Treasury 20+ anos | TLT | IDTL.L |
| Renda fixa global | AGG | AGGU.L |
| Ouro | GLD | IGLN.L |

Confirme regras e tributação com um contador. No Brasil, a Lei 14.754/2023 tributa aplicações no exterior em 15% ao ano sobre os rendimentos — um custo que nenhum backtest aqui inclui.

## Os métodos

**1. Dual Momentum — GEM** · Gary Antonacci, *Dual Momentum Investing* (2014)

Uma vez por mês, compare o retorno de 12 meses de ações EUA, ações ex-EUA e T-Bills. Se ações EUA perderam para T-Bills, vá para renda fixa. Senão, fique 100% no melhor entre EUA e ex-EUA. Uma decisão por mês, poucas trocas por ano.

**2. GTAA / Ivy 5** · Mebane Faber, *A Quantitative Approach to Tactical Asset Allocation* (2007)

Cinco classes com 20% cada (ações EUA, ações ex-EUA, Treasuries, imóveis, commodities). Classe abaixo da média de 10 meses vai para caixa. É um dos artigos mais baixados da história do SSRN.

> O backtest do app mostra o trade-off com honestidade: desde 2008, as duas renderam **menos** que o S&P 500 puro, mas com quedas máximas muito menores. Elas protegem o patrimônio; não prometem ganhar do índice.

**3. Scanner QVM (Qualidade + Valor + Momento)**

| Fator | Evidência |
|---|---|
| Valor | Fama & French (1992) |
| Momento (12 meses, pulando o último) | Jegadeesh & Titman (1993) |
| Qualidade / rentabilidade | Novy-Marx (2013); Asness, Frazzini & Pedersen, *Quality Minus Junk* |
| Filtro de tendência (MM200) | Faber (2007) |

Fatores funcionam na média de décadas, mas podem passar anos sem funcionar. Use o scanner para **escolher o que estudar**, não o que comprar.

**4. Piotroski F-Score** · Joseph Piotroski (2000)

Nove testes de saúde financeira: lucro, caixa, endividamento, liquidez, diluição, margem e eficiência. 8–9 é forte; 0–3, fraco.

**5. DCF reverso** · Mauboussin & Rappaport, *Expectations Investing*

Em vez de chutar o crescimento, o app calcula **quanto crescimento o preço atual já embute**. Se o mercado exige 30% ao ano por 5 anos de uma empresa que historicamente cresce 12%, o preço depende de perfeição.

**6. Carteiras-modelo trocáveis** (tela *Carteiras do Núcleo*, arquivo `config/estrategias.yaml`)

| Carteira | Fonte | Perfil |
|---|---|---|
| Núcleo conservador | Plano PWASS | 40% caixa em dólar, 15% Treasuries, 35% ações globais, 10% ouro |
| Três fundos | Bogleheads (Taylor Larimore) | Simples, barata, mais ações |
| 60/40 global | Padrão de fundos de pensão | Meio-termo clássico |
| Portfólio Permanente | Harry Browne | Um quarto para cada cenário econômico |
| All Weather (aprox.) | Bridgewater/Tony Robbins | Risco equilibrado; sofre com juros subindo |
| Dual Momentum (GEM) | Antonacci | Tática, 1 ativo por vez |
| GTAA / Ivy 5 | Faber | Tática, 5 classes com filtro de tendência |

A tela mostra a alocação-alvo de hoje (com equivalente UCITS) e compara as carteiras **em reais contra o CDI**, a régua honesta para quem mora no Brasil. Para fixar a sua, mude `padrao` no arquivo.

**7. Semáforo de prudência** (tela *Radar de mercado*)

Cada ativo recebe uma de cinco leituras, sempre com a postura prudente correspondente: 🟢 alta saudável, 🟡 esticado, 🔵 recuperando, 🔵 correção, 🔴 tendência de baixa. Combina os dois filtros clássicos de tendência (preço acima da média de 200 dias subindo, de Faber, e retorno de 12 meses positivo, de Antonacci) com um limite de esticamento. Para juros, compara a taxa de hoje com a própria história (percentil). Para o Brasil: juro real ex-ante (Selic vs. IPCA esperado do Focus), taxas do Tesouro Direto, inflação implícita e quanto o dólar precisa subir para o T-Bill empatar com o CDI.

**8. Filtro anti-hype das Zonas de entrada**

"Evitar" vence qualquer sinal quando o preço está mais de 40% acima da MM200, o RSI está em 75+ ou o P/L futuro passa de 80. "Forte Compra" só aparece com preço justo definido e margem de segurança de 20%.

## Laboratório de swing

Fica no Satélite, com dinheiro separado (padrão: US$ 5 mil em `config/swing.yaml`) e regras que não mudam com o humor do dia. A tela **Laboratório de swing** mostra a ficha e o histórico completo de cada regra (curvas, drawdown, distribuição, retorno por ano e comparação das 3). Os botões **Swing Trade**, **Cruzamento Média** e **Rompimento** na barra lateral trocam a estratégia do Terminal.

| Estratégia | Regra | Perfil histórico (35 ativos, 10 anos, com custos) | Base |
|---|---|---|---|
| **Swing Trade (Pullback)** | Preço > MM200 e RSI(2) < 10 → compra na abertura seguinte; sai quando fecha acima da MM5 | ~2.300 operações, acerto ~65%, ganho médio pequeno (+0,4%/op.), poucos dias por operação | Connors & Alvarez (2009); a vantagem encolheu após a publicação |
| **Cruzamento de Médias** | EMA20 cruza acima da EMA50 com preço > MM200; sai no cruzamento para baixo | ~500 operações, acerto ~42%, ganhos grandes e longos | Seguimento de tendência clássico |
| **Rompimento com Volume** | Fecha acima da máxima de 55 dias com volume > 1,5× a média; stop 2×ATR; sai abaixo da mínima de 20 dias | ~560 operações, acerto ~37%, muitas perdas pequenas e poucos ganhos grandes | Tartarugas / canal de Donchian |

**Como o Painel decide**
1. Roda a regra em todos os ativos do universo e classifica cada um: **COMPRA** (setup completo hoje), **SAIR** (regra de saída acionada), **EM POSIÇÃO**, **PERTO DO GATILHO**, **AGUARDAR** ou **EVITAR** (abaixo da MM200).
2. Avalia o **histórico da regra naquele ativo**: Bom (profit factor ≥ 1,5), Regular (≥ 1,1), Fraco (abaixo) ou Pouco histórico.
3. O **Sinal do dia** é a COMPRA com melhor histórico. Se o histórico for fraco, o card mostra "EVITAR" mesmo com o gatilho acionado.
4. O **plano** vem da regra de risco: stop = entrada − 2×ATR(14); alvos em 1,5R e 3R; quantidade = 1% do laboratório ÷ distância do stop, limitada a 25% do laboratório por posição.

**Leia com honestidade:** em quase todos os ativos, a estratégia rende menos por ano que simplesmente segurar o ativo (buy & hold), porque fica posicionada só parte do tempo. O valor do swing está em quedas máximas menores e em capital livre no resto do tempo, não em bater o índice. Por isso ele fica limitado ao Satélite. Execução sempre na abertura do dia seguinte ao sinal, com 0,10% de custo por lado; dados intradiários (1h/15m) não são usados porque o histórico grátis é curto demais para testar.

**Comitê de IA** (no Painel, com a IA ligada): três agentes analisam o ativo do gráfico (Técnico, Macro/Fundamentalista e Risco) e um juiz consolida a decisão (COMPRAR, AGUARDAR, MANTER, REDUZIR, VENDER ou EVITAR) com convicção baixa, média ou alta. Os agentes recebem só números calculados pelo app. Custo típico: ~US$ 0,02 por análise; modelos em `config/ai.yaml`.

## Rotina

**Diário (dias úteis, 5 min, depois das 18h)** — abra o *Painel*: veja o Sinal do dia, as saídas acionadas e os alertas. Ordens entram para a abertura do dia seguinte. Fora de casa, o `RADAR.md` no app do GitHub dá a visão geral.

**Semanal (sexta, 15 min)**
1. *Zonas de entrada*: algo entrou na zona? Algo virou "Evitar"?
2. *Scanner*: anote no máximo 1–2 nomes novos para estudar.

**Mensal (primeiro dia útil, 20 min)**
1. *Carteiras do Núcleo*: veja a alocação-alvo da sua carteira (e o sinal do GEM/GTAA, se usar uma tática). Mudou ou desviou mais de 5 pontos? Rebalanceie o Núcleo, de preferência com o aporte novo.
2. Confira os limites do Satélite (20% total, 5% por ação, 5% cripto). Passou? Reduza.
3. Leia o relatório mensal automático em `relatorios/` (se ativou o GitHub Actions).

**Trimestral (temporada de resultados — fim de jan, abr, jul e out)**
1. Para cada ação do Satélite: *Analista IA → Filings da SEC* → 10-Q (ou 8-K com o release).
2. *Ativo → Fundamentos → Saúde financeira*: o Piotroski piorou?
3. Releia a sua tese. Se o motivo da compra deixou de existir, venda — mesmo no prejuízo.

**Anual**
- Revise pesos e universo do scanner.
- Revise corretora, beneficiários (TOD) e o Protocolo de Emergência da família.
- Declaração do IR (ativos no exterior e cripto).

**Regra de ouro para o Satélite**: nenhuma compra sem (1) passar no Radar sem "Evitar", (2) ler a página Ativo e (3) escrever a tese em 3 linhas, incluindo o que a invalidaria.

## IA: opções

**Resposta curta:** a IA é a parte menos importante do PWASS. O que faz diferença é a IA receber números calculados e documentos reais (é o que o app faz). Dito isso, o conjunto sugerido é bom em custo-benefício, com três caminhos à escolha:

| Caminho | Como | Custo | Quando escolher |
|---|---|---|---|
| **A. OpenRouter** (recomendado) | Uma chave, todos os modelos | Centavos por análise | Quer o melhor modelo para cada tarefa sem várias contas |
| **B. Gemini grátis + OpenRouter** | Chave grátis do Google AI Studio para o dia a dia; OpenRouter só para Claude | Quase zero | Quer gastar o mínimo. Na camada grátis o Google pode usar o conteúdo: mande só dados de mercado |
| **C. Ollama local** | Modelo rodando no seu PC | Zero | Privacidade total; qualidade e velocidade menores |

Os três já funcionam no app: a chave da OpenRouter e a do Google ficam na barra lateral, e o prefixo do modelo escolhe o provedor (`gemini:` ou `ollama:`). A assinatura **Google AI Pro não inclui a API**; a chave do AI Studio é separada (e grátis no Gemini Flash).

**Qual modelo para quê** (US$ por milhão de tokens, entrada/saída, em 06/11/2026)

| Tarefa | Modelo | Preço | Por quê |
|---|---|---|---|
| Dia a dia: PDFs, prints, auditorias | Claude Haiku 5.5 | 0,10 / 0,50 | Barato, rápido, contexto de 1 milhão de tokens |
| Dia a dia sem custo | Gemini 3.8 Flash (AI Studio) | grátis | Camada gratuita do Google |
| 10-K inteiro, juiz do debate | Claude Sonnet 5.5 | 2 / 10 | Leitura longa e raciocínio cuidadoso |
| Decisão importante (raro) | Claude Opus 5.5 | 4 / 20 | Revisão final de uma tese antes de uma posição relevante |
| Segunda opinião | Gemini 4 Argon | 2 / 10 | Outro "cérebro", forte com documentos e tabelas |
| Terceira visão (debate) | GPT-6.1 Terra | 1 / 5 | Diversidade de modelos reduz viés |
| Notícias com fontes | Perplexity Sonar | 1 / 1 + busca | Busca na web e cita links |
| Triagem em massa | DeepSeek V4.1 Flash | 0,05 / 0,57 | Muito barato; nunca envie dados pessoais |
| Testar | Gemma 4 31B (free) | 0 | Limites diários |

Uma análise típica (10 mil tokens de entrada, 2 mil de saída) custa **menos de 1 centavo** no Haiku e cerca de **4 centavos** no Sonnet. Um 10-K inteiro no Sonnet: ~US$ 0,20–0,30.

**Passo a passo (caminho A)**
1. Crie a conta em **openrouter.ai** e coloque US$ 5–10 em **Credits** (dura meses).
2. Em **Keys**, crie uma chave com **limite de crédito** (ex.: US$ 5).
3. Em **Settings → Privacy**, desative provedores que treinam com seus dados.
4. Cole a chave na barra lateral (Configurações → Chaves de IA e modelos) ou defina `OPENROUTER_API_KEY`.

**Caminho B**: crie a chave em **aistudio.google.com/apikey** e cole no campo do Google (ou `GEMINI_API_KEY`). **Caminho C**: instale o **Ollama**, rode `ollama pull qwen3:8b` e escolha o preset *Local*.

**O que a IA faz bem aqui**: resumir relatórios longos, achar mudanças de linguagem no guidance, listar riscos de nota de rodapé, montar teses otimista e pessimista, ler prints de gráficos.

**O que ela faz mal**: prever preço, saber notícias que não recebeu, fazer contas longas sem errar. Por isso o app calcula os números em Python e manda prontos para a IA interpretar.

**Use o Google AI Pro que você já paga:**
- **NotebookLM**: suba 10-K, transcrições de teleconferência e cartas de gestores; pergunte e receba respostas com citação da página.
- **Gemini Deep Research**: relatórios sobre um setor ou empresa, com fontes.
- Divisão de trabalho: o PWASS faz a triagem e os números; o NotebookLM é a biblioteca de leitura da temporada de resultados.

**Privacidade**: nunca envie saldos, números de conta ou dados pessoais para a IA. O app só envia dados de mercado e os documentos que você escolher.

## Ferramentas avaliadas

Avaliação da lista de repositórios pesquisada, com o status conferido no PyPI em 06/11/2026. Critério: serve ao Núcleo-Satélite de longo prazo, é mantido e cabe num app pessoal de custo zero?

| Ferramenta | Veredito | Por quê |
|---|---|---|
| **awesome-quant** | 📚 Consultar | Índice de bibliotecas. Não se instala; use para achar algo específico. |
| **yfinance** | ✅ Em uso | Padrão para projeto pessoal. Limitação: não é fonte oficial e às vezes limita requisições. |
| **quantstats** | ✅ Adotado | Ativo (out/2026). O app gera o relatório completo na tela *Carteiras do Núcleo*. |
| **python-bcb** / API do BCB | ✅ Adotado (API direta) | O app consulta o SGS e o Focus do Banco Central direto, sem dependência extra. |
| **Tesouro Transparente** | ✅ Adotado | Taxas oficiais de todos os títulos do Tesouro Direto desde 2004. |
| **edgartools** | 🔜 Próxima fase | Ativo (out/2026). Traria fundamentos oficiais da SEC (XBRL) no lugar do Yahoo. |
| **OpenBB** (v5) | 🔜 Avaliar depois | Ativo e com servidor MCP, mas é uma plataforma grande, e vários provedores pedem chave. Faz sentido se o Yahoo virar gargalo. |
| **vectorbt** | ⏸️ Só se fizer swing trade | Ativo (out/2026). Para estratégias mensais, nosso backtest simples basta e é mais fácil de auditar. |
| **backtesting.py** | ⏸️ Só se fizer swing trade | Simples e ativo, mas licença AGPL: se publicar o app, o código precisa ficar aberto. |
| **pandas-ta** | ❌ Evitar | O pacote original parou em versão beta (set/2025) e exige Python 3.12+. Se precisar, use o fork **pandas-ta-classic** (ativo). O PWASS calcula seus poucos indicadores sozinho. |
| **ta** (bukosabino) | ❌ Evitar | Sem lançamentos desde 2023. |
| **backtrader** | ❌ Evitar | Abandonado (último lançamento em 2023). |
| **QuantConnect Lean** | ❌ Exagero | Feito para operar ao vivo com corretora; não é o seu caso. |
| **ziplime** | ❌ Cedo demais | Ativo, mas novo e imaturo; exige Python 3.12+. |
| **PKScreener** | ❌ Não serve | Feito para a bolsa da Índia (NSE/BSE). |
| **brapi.dev / brasa** | ❌ Fora do foco | Ações e FIIs da B3. A renda fixa brasileira já vem do BCB e do Tesouro. |
| **akshare / pandas-datareader** | ❌ Evitar | Foco na China / várias fontes quebradas. O FRED já vem direto por CSV. |
| **streamlit-lightweight-charts** | ❌ Evitar | Sem atualização desde 2023. O Plotly cobre os gráficos. |
| **qlib, FinRL, FinGPT** | ❌ Pesquisa | Machine learning e aprendizado por reforço para operar. Pesado, sem histórico real e contra a filosofia anti-emoção. |
| **PyPortfolioOpt / Riskfolio** | ⏸️ Com cuidado | Otimização "ótima" costuma ser frágil; carteiras-modelo simples são mais robustas. |
| **TradingAgents / FinRobot** | 💡 Ideia aproveitada | O Debate da página Ativo (otimista × pessimista × juiz) vem daí. Não use para operar. |

**Sobre swing trade**: a lista que você trouxe é voltada para operar no curto prazo. Isso conflita com a ideia central do PWASS (evitar decisões emocionais), e a evidência com pessoas físicas é dura. Barber & Odean ("Trading Is Hazardous to Your Wealth", 2000) mostraram que quem mais opera rende menos. No Brasil, Chague, De-Losso e Giovannetti (2019) acompanharam day traders de mini-índice, e quase todos que persistiram perderam dinheiro. Se ainda quiser testar, o caminho prudente é um módulo "laboratório": regras escritas, backtest obrigatório com `backtesting.py` e no máximo 5% do patrimônio, dentro do Satélite.

## Ferramentas externas

Gratuitas (ou com plano grátis útil), todas focadas no mercado externo:

| Ferramenta | Para quê |
|---|---|
| **TradingView** | Gráficos e alertas de preço no celular. Os prints vão para o Analista IA. |
| **Finviz** | Screener rápido e mapa de calor do S&P 500. |
| **Koyfin** | Painéis de fundamentos e comparação de múltiplos históricos. |
| **stockanalysis.com** | Demonstrativos de 10+ anos, de graça. |
| **Portfolio Visualizer** | Backtests de alocação (confira os resultados do app). |
| **justETF** | Comparar e achar ETFs UCITS (custos, domicílio, tamanho). |
| **OpenInsider** | Compras e vendas de executivos das empresas. |

## Publicar e consultar

**1. Subir para o GitHub**
```bash
cd pwass
git init && git add . && git commit -m "PWASS v3"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/pwass.git
git push -u origin main
```

**2. Publicar grátis no Streamlit Community Cloud**
1. Entre em **share.streamlit.io** com sua conta do GitHub.
2. *Create app* → escolha o repositório → arquivo `app.py` → *Deploy*.
3. Em *Settings → Secrets*, cole:
```toml
SEC_USER_AGENT = "Seu Nome seu@email.com"
# Só se o app for só seu (privado):
# OPENROUTER_API_KEY = "sk-or-..."
# PWASS_USAR_CHAVE_DO_SERVIDOR = "true"
```
4. O app "dorme" sem uso e acorda em ~30 s no próximo acesso.

**3. Privacidade**
- App de uso pessoal: no Streamlit Cloud, deixe o acesso só para o seu e-mail. Passo a passo completo em `docs/INSTALACAO.md`.
- O repositório não tem nenhum dado pessoal: só regras e listas de ativos. Posições reais e o Protocolo de Emergência nunca entram no GitHub (`.gitignore`).

**4. Onde consultar o radar sem abrir o app**

| Lugar | Como | Funciona em repositório privado? |
|---|---|---|
| **RADAR.md no GitHub** | O workflow `radar-diario.yml` atualiza em dias úteis às 19h37 (Brasília). Abra no app do GitHub no celular. | ✅ Sim |
| **Página web (site/index.html)** | Mesmo conteúdo, visual limpo, com modo escuro. Publique pelo GitHub Pages (variável `PUBLICAR_PAGES = true`) ou arraste a pasta `site/` para Cloudflare Pages/Netlify. | Pages grátis só em repositório público; Cloudflare/Netlify aceitam privado |
| **App Streamlit** | Tela *Radar de mercado*, com gráficos e leitura por IA. | ✅ Sim |

Para rodar na hora: *Actions → Radar diário → Run workflow*.

**5. Relatório mensal automático (opcional)**
- O arquivo `.github/workflows/relatorio-mensal.yml` roda no dia 1 de cada mês, gera `relatorios/AAAA-MM.md` com os sinais, o regime e o top do scanner, e faz commit no repositório.
- Ative em *Settings → Actions → General → Workflow permissions → Read and write*.
- Para incluir um comentário da IA, crie o secret `OPENROUTER_API_KEY` em *Settings → Secrets and variables → Actions*.

## Limites e cuidados

- **Yahoo Finance não é fonte oficial.** Pode ter atrasos, erros e limite de requisições. Para decidir, confira no relatório da empresa.
- **ADRs**: balanço em moeda local e preço em dólar distorcem FCF yield, EV/EBITDA e DCF. O app desliga essas métricas quando detecta a diferença.
- **Backtest não é promessa.** Não inclui custos, spread cambial, IOF nem impostos, e o futuro pode ser diferente do passado.
- **Fatores e tendência falham por anos.** A disciplina de seguir a regra é o que faz o método funcionar.
- **A IA erra.** Ela interpreta os números que recebe; não sabe o que não recebeu. Sempre leia a fonte.
- **A responsabilidade é sua.** O app recomenda com base em regras e IA; quem decide, aporta e assume o risco é você. Use-o para decidir com menos emoção, não para terceirizar a decisão.
