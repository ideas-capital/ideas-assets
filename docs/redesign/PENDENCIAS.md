# Pendências

| Item | Motivo | Situação |
|---|---|---|
| Logo (`assets/logo.svg/png`) | Arquivo não existe no repositório; não inventar logo (§3.1). | `app.py` já usa `st.logo()` quando `assets/logo.svg` existir; até lá, marca "IC". |
| Troca de tema pelo menu nativo: persistência e rerun | No Chromium local, o menu ⋮ só mostrou "Rerun" (sem "Settings"), então não deu para exercitar a troca ao vivo. Verificado: a carga inicial segue o tema do sistema (claro/escuro) e aplica o `config.toml` corretamente. | **Verificar manualmente** no app publicado: trocar em ⋮ → Settings → Theme, ver se a página re-renderiza sem recarregar e se persiste. Se não houver rerun, o `?tema=` NÃO serve de fallback completo: ele só muda o CSS próprio, não o tema nativo (descoberto na Sessão 3); a alternativa seria um seletor próprio que grave `[theme]` por sessão — decidir só se a troca nativa falhar. |
| Fonte FRED indisponível neste ambiente de execução | HTTP 000 na sessão (rede). | Usar fixtures nos testes que dependam de FRED. |
| Estratégia / ★ watchlist / alertas na topbar | Dependem do `store.py` (Sessão 4). | Não exibidos até existirem. |
| Screenshots em `screens/` | Fazer após as páginas migrarem (Sessão 6). Capturas de verificação da Sessão 1 foram só locais. | Pendente |
| Filtros salvos do Scanner (§7.3) | Dependem do `store.py` (Sessão 4). Controle não exibido. | Pendente |
| ★ favorito no Ativo | Depende da watchlist/`store.py` (Sessão 4). | Pendente |
| Composição de ETF (aba Fundamentos) | O Yahoo gratuito não entrega; só taxa e AUM quando vierem. | Documentado na tela |
| Calendário de resultados e `.info`/notícias do Yahoo | Instáveis (HTTP 401/429 "crumb" observado neste ambiente). A UI mostra "—"/estado vazio com motivo, sem estimar. | Monitorar em produção |
| Mobile: gráfico TradingView e tabelas largas | Só o Painel foi conferido em 390 px (sidebar corrigida). Conferir Ativo/Scanner no celular. | Sessão 6 |
| Operações reais no Laboratório | O diário de operações (Sessão 4) ainda não existe; o controle não é exibido. A página já rotula tudo como "Simulado / backtest". | Pendente |
| Análises da IA persistentes | Ficam só em `st.session_state` (somem ao fechar a aba). Persistência via `store.py` na Sessão 4. | Pendente |
| Checagem de números da IA | `numeros_fora_dos_dados` tolera arredondamento e ×100/÷100; pode deixar passar número que coincida com algum valor do JSON. É um alerta, não garantia. | Limitação documentada |
| Zonas: retângulo | O Lightweight Charts não desenha retângulos; a zona é mostrada como duas linhas (mín/máx). | Decisão registrada |
