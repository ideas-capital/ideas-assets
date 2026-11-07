# Progresso do redesign v5

Branch de trabalho desta sessão: `claude/confident-euler-7jpavc` (o prompt cita `redesign-v5`; a plataforma designou esta branch e foi mantida).

## Sessão 1 — Auditoria, plano e Design System: **concluída**
Feito:
- `AUDITORIA.md`, `PLANO.md`, `DESIGN-SYSTEM.md`, `PENDENCIAS.md`.
- `pwass/ui/tokens.py` (tokens, séries, escalas) + `.streamlit/config.toml` com `[theme.light]`/`[theme.dark]` e sidebar; `theme.py` sem `st._config` (modo via `st.context.theme.type`, `?tema=` como override).
- `pwass/ui/components.py` (12 componentes com estados) e página oculta `/componentes`.
- `app.py`: menu em seções novas, topbar com busca global (abre Ativo), status NYSE/B3 (`pwass/engine/mercado.py`), seletor de estratégia só no Painel, dica de tema.
- Séries de `tvchart.py`/`charts.py` lidas de `tokens.SERIES`; hex removidos das páginas.
- `.gitignore` criado (não existia — ver AUDITORIA #2).

Testes: `pytest` 118 verdes (31 antigos + tokens/contraste, config, mercado, smoke `_componentes`, hex em páginas, badge). Smoke `AppTest` do `app.py` em todas as 9 páginas × 2 temas, sem exceção. Nenhum arquivo de cálculo existente foi alterado (regressão numérica preservada por construção; fixtures vêm na Sessão 2).

Checklist manual: busca global (selectbox renderiza; navegação testada só em AppTest) · troca de tema pelo menu **não verificada** (ver PENDENCIAS) · mobile e exportação não verificados nesta sessão.

## Sessão 2 — Painel + Ativo + Scanner: **concluída**
Feito:
- **Regressão numérica primeiro:** fixtures reais (`tests/fixtures/ohlcv_swing.parquet`, `precos_carteiras.parquet`: SPY, QQQ, AAPL, GLD até 05/11/2026 + 8 ETFs mensais) e `golden.json` (3 estratégias × 4 ativos, GEM e GTAA) gerados com o código ANTES de qualquer mudança; `tests/test_regressao.py` compara. Nenhum arquivo de cálculo existente (`swing.py`, `backtest.py`, `strategies.py`...) foi alterado.
- `indicators.py`: MACD, pivôs clássicos, pivôs de swing (com data de confirmação, sem olhar o futuro) e suporte/resistência, com testes.
- **Painel**, **Ativo** (6 abas) e **Scanner** (10 filtros, chips, CSV/Excel, clique abre o Ativo) refeitos no Design System; detalhes em `MUDANCAS.md`. `paginas/mercado.py` removida.
- Novos puros/testados: `engine/mercado.py` (+amplitude/percentil/novidades), `engine/ativo.py`, `engine/screener.py`.
- Verificação visual em Chromium (Painel dark/light desktop, Painel mobile, Ativo): ok; corrigidos 5A vazio no Ativo, sidebar cobrindo o conteúdo no celular, fonte duplicada no cabeçalho do Painel.

Testes: `pytest` **130 verdes**. Smoke `AppTest` das 9 páginas × 2 temas sem exceção com dados reais (`scripts/smoke_paginas.py`); Scanner exercitado com clique em "Rodar" (25 linhas, 22 colunas). Yahoo `.info`/calendário/notícias ficam intermitentes (401/429) neste ambiente: as telas mostram "—" com motivo.

Limitações conhecidas (ver PENDENCIAS.md): filtros salvos e ★ dependem do store (Sessão 4); troca de tema ao vivo ainda sem verificação manual; Ativo/Scanner não conferidos em 390 px; screenshots oficiais só na Sessão 6.

## Sessão 3 — Laboratório + Carteiras + Zonas + Analista IA: **concluída**
Feito (detalhes em `MUDANCAS.md`): Laboratório de swing (nova), Carteiras do Núcleo com aba Lado a lado, Zonas de entrada com plano e justificativa, Analista IA com formato fixo e validação. Menu atualizado (`estrategias.py` → `carteiras.py`).
Testes: `pytest` **143 verdes** (novos: lab, carteiras, zonas, estruturada). `scripts/smoke_paginas.py`: 10 páginas × 2 temas sem exceção, com dados reais. Fluxo da IA exercitado com resposta SIMULADA (sem chave aqui) — o detector pegou o número inventado de propósito. Verificação visual (Chromium): Laboratório dark e Zonas light ok; corrigidos: cores inconsistentes entre curva e drawdown, R/R com ponto decimal, linhas S/R em excesso.
Achado importante: `?tema=` só muda o CSS próprio (não o tema nativo) → não é fallback real para a troca de tema (ver PENDENCIAS).
Limitações: ver PENDENCIAS (operações reais, persistência da IA, checagem de números, mobile do Laboratório/Zonas/Carteiras não conferido).

## Sessão 4 — Persistência, watchlist, alertas, comparar e diário: **concluída**
Feito (detalhes em `MUDANCAS.md`): store local/Supabase, Alertas e watchlist, Comparar, Diário de operações, ★ e alerta no Ativo, topbar com contagem real, filtros salvos, análises da IA persistidas, workflow `alertas.yml` + Telegram opcional.
Testes: `pytest` **159 verdes** (novos: store, alertas, notify, comparar, diário). Smoke das 13 páginas × 2 temas sem exceção. Fluxos reais exercitados em AppTest com store em pasta temporária: favoritar → lista → adicionar NVDA (validado no Yahoo) → criar alerta → registrar operação → ler de volta; salvar e carregar filtro do Scanner; salvar análise da IA (resposta simulada). Visual (Chromium, dark): Comparar e Alertas ok; corrigida a paleta do drawdown em Comparar.
**Achado:** `radar-diario.yml` e `relatorio-mensal.yml` citados no GUIA/INSTALACAO não existem no repositório (ver PENDENCIAS). Telegram implementado; e-mail não. Supabase não foi testado contra um servidor real.
Limitações: PENDENCIAS.md (decimais das tabelas nativas seguem o locale do navegador; mobile das páginas novas não conferido).

## Sessão 5 — Relatórios, score, Configurações e Guia: **concluída**
Feito (detalhes em `MUDANCAS.md`): páginas **Relatórios** (PDF + Excel do mesmo dict da tela) e **Configurações e fontes**; checklist "Por que este sinal?" (Painel e Ativo); validação do score; Guia/README atualizados; `mercado.regime` extraído (Painel idêntico).
**Score: reprovado e NÃO exibido.** Calibrado com sinais até 2019 (772 operações) e testado de 2020 em diante (2.545): correlação fora da amostra +0,038 (p = 0,02), mas a faixa alta (+2,5%/op.) rendeu menos que a baixa (+2,9%/op.). Critério de exibição não atendido; tabela e motivos em `SCORE.md`, estado em `config/score.yaml` (gerado, não editar).
Dependências novas: `fpdf2` e `matplotlib` (justificativa em MUDANCAS).
Testes: `pytest` **172 verdes** (novos: fatores, score, relatório PDF/Excel com os mesmos valores do dict, status, regime). Smoke das 15 páginas × 2 temas sem exceção. Geração real do relatório exercitada em AppTest (PDF 79 KB, Excel 11 KB) e PDF inspecionado visualmente; teste ao vivo das 6 fontes: todas ok (Tesouro leva ~18 s). Visual: Configurações (dark) ok.
Limitações novas: PENDENCIAS.md (PDF em Helvetica; chaves de IA permanecem na barra lateral; e-mail de alertas e os workflows `radar-diario`/`relatorio-mensal` ainda ausentes do repositório).

## Próxima ação exata
**Sessão 6** (PROMPT §12/§13): (1) screenshots desktop 1440 px e mobile 390 px × dark e light das páginas principais em `docs/redesign/screens/` (Playwright; usar `colorScheme` do navegador para o tema, NÃO `?tema=`); conferir mobile do Ativo, Scanner, Laboratório, Carteiras, Zonas, Comparar, Alertas e Diário e corrigir o que quebrar (tabelas com scroll horizontal, gráfico com altura reduzida, colunas empilhadas). (2) Testes finais: regressão numérica verde, contraste, smoke AppTest, grep de hex em `paginas/`; adicionar teste que garante que `docs/GUIA.md` não cita nomes de telas antigos. (3) Checklist manual no PROGRESSO (navegação, busca, filtros, exportação, estados vazio/erro, mobile; troca de tema pelo menu segue pendente de verificação no app publicado). (4) Entregáveis finais em `docs/redesign/`: `PROXIMOS-PASSOS.md`, revisão de `MUDANCAS.md`/`PENDENCIAS.md`, `README.md`/`CLAUDE.md`/`GUIA.md` coerentes. (5) Abrir o PR para `main` SOMENTE se o usuário pedir explicitamente (a regra da plataforma proíbe criar PR sem pedido); caso contrário, deixar a branch pronta e informar.
