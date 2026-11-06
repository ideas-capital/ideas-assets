# Pendências

| Item | Motivo | Situação |
|---|---|---|
| Logo (`assets/logo.svg/png`) | Arquivo não existe no repositório; não inventar logo (§3.1). | `app.py` já usa `st.logo()` quando `assets/logo.svg` existir; até lá, marca "IC". |
| Troca de tema pelo menu nativo: persistência e rerun | No Chromium local, o menu ⋮ só mostrou "Rerun" (sem "Settings"), então não deu para exercitar a troca ao vivo. Verificado: a carga inicial segue o tema do sistema (claro/escuro) e aplica o `config.toml` corretamente. | **Verificar manualmente** no app publicado: trocar em ⋮ → Settings → Theme, ver se a página re-renderiza sem recarregar e se persiste. Se não houver rerun, usar `?tema=` como fallback documentado. |
| Fonte FRED indisponível neste ambiente de execução | HTTP 000 na sessão (rede). | Usar fixtures nos testes que dependam de FRED. |
| Estratégia / ★ watchlist / alertas na topbar | Dependem do `store.py` (Sessão 4). | Não exibidos até existirem. |
| Screenshots em `screens/` | Fazer após as páginas migrarem (Sessão 6). Capturas de verificação da Sessão 1 foram só locais. | Pendente |
