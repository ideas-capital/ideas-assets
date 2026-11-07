# Pendências

| Item | Motivo | Situação |
|---|---|---|
| Logo (`assets/logo.svg/png`) | Arquivo não existe no repositório; não inventar logo (§3.1). | `app.py` já usa `st.logo()` quando `assets/logo.svg` existir; até lá, marca "IC". |
| Troca de tema pelo menu nativo: persistência e rerun | No Chromium local, o menu ⋮ só mostrou "Rerun" (sem "Settings"), então não deu para exercitar a troca ao vivo. Verificado: a carga inicial segue o tema do sistema (claro/escuro) e aplica o `config.toml` corretamente. | **Verificar manualmente** no app publicado: trocar em ⋮ → Settings → Theme, ver se a página re-renderiza sem recarregar e se persiste. Se não houver rerun, o `?tema=` NÃO serve de fallback completo: ele só muda o CSS próprio, não o tema nativo (descoberto na Sessão 3); a alternativa seria um seletor próprio que grave `[theme]` por sessão — decidir só se a troca nativa falhar. |
| Fonte FRED indisponível neste ambiente de execução | HTTP 000 na sessão (rede). | Usar fixtures nos testes que dependam de FRED. |
| Screenshots em `screens/` | Fazer após as páginas migrarem (Sessão 6). Capturas de verificação da Sessão 1 foram só locais. | Pendente |
| Composição de ETF (aba Fundamentos) | O Yahoo gratuito não entrega; só taxa e AUM quando vierem. | Documentado na tela |
| Calendário de resultados e `.info`/notícias do Yahoo | Instáveis (HTTP 401/429 "crumb" observado neste ambiente). A UI mostra "—"/estado vazio com motivo, sem estimar. | Monitorar em produção |
| Mobile: gráfico TradingView e tabelas largas | Só o Painel foi conferido em 390 px (sidebar corrigida). Conferir Ativo/Scanner no celular. | Sessão 6 |
| Checagem de números da IA | `numeros_fora_dos_dados` tolera arredondamento e ×100/÷100; pode deixar passar número que coincida com algum valor do JSON. É um alerta, não garantia. | Limitação documentada |
| Zonas: retângulo | O Lightweight Charts não desenha retângulos; a zona é mostrada como duas linhas (mín/máx). | Decisão registrada |
| Workflows `radar-diario.yml` e `relatorio-mensal.yml` | O GUIA.md e o INSTALACAO.md os descrevem, mas **não existem em `.github/workflows/`** neste repositório (só `alertas.yml`, criado na Sessão 4). Ou nunca foram commitados ou foram perdidos. | Decidir se recriam (os scripts `gerar_radar.py` e `relatorio_mensal.py` existem). |
| Alertas por e-mail | Só Telegram foi implementado (prompt: "Telegram ou e-mail"). E-mail exigiria SMTP/secret extra. | Opcional, não feito |
| Alertas no Actions sem Supabase | O Actions não enxerga arquivos locais do app; sem `SUPABASE_URL/KEY` o job só informa e termina. Sem isso os alertas aparecem só no app/topbar. | Documentado na página e no workflow |
| Alertas "sinal de estratégia" no Actions | Usam `config/swing.yaml` do repositório e 5 anos de candles (a regra precisa de ~260 barras). | Ok |
| Casas decimais das tabelas nativas | `st.dataframe` formata números pelo locale do navegador (ponto decimal em navegador em inglês); o `format` printf do Streamlit não localiza. Cartões/KPI usam pt-BR. | Limitação do framework |
| Diário: custos e impostos | Resultado real é bruto (sem custos/IOF/impostos); o backtest inclui 0,10%/lado. Dito na tela. Módulo fiscal fica no roadmap. | Documentado |
| Supabase não testado contra servidor real | Backend testado com sessão HTTP simulada; o SQL (`supabase.sql`) não foi executado num projeto real. | Validar ao configurar |
