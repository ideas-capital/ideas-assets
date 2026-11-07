"""Configurações e fontes: IA, tema, faixa de mercado, parâmetros de risco, status das fontes, armazenamento e Sobre.

Somente leitura onde o valor vem de YAML (edite o arquivo: `config/*.yaml`). Chaves e modelos de IA se
editam na barra lateral (Configurações), porque dependem de estado da sessão.
"""
import tomllib

import pandas as pd
import streamlit as st

from pwass.data import status
from pwass.ui import cache, components as ds, settings, theme
from pwass.ui.theme import num, pct

ds.page_header("Configurações e fontes", "O que está ativo no app, de onde vêm os dados e onde mudar cada coisa.")
ai = cache.config("ai")
sw = cache.config("swing")

t_ia, t_vis, t_par, t_fontes, t_sobre = st.tabs(["IA", "Aparência e faixa", "Risco e estratégias", "Fontes e armazenamento", "Sobre"])

with t_ia:
    st.markdown("##### Chaves detectadas")
    st.caption("Chaves e modelo padrão se editam na barra lateral (Configurações → Chaves de IA e modelos). Nada é gravado em disco: "
               "a chave fica só na sessão do navegador, em variável de ambiente ou nos secrets do servidor.")
    rows = [{"Provedor": nome, "Chave": "detectada" if settings.api_key(p) else "ausente"}
            for p, nome in (("openrouter", "OpenRouter"), ("gemini", "Google AI Studio"))] + [{"Provedor": "Ollama (local)", "Chave": "não precisa"}]
    ds.data_table(pd.DataFrame(rows), key="cfg_chaves")
    st.markdown(f"**Modelo padrão em uso:** `{settings.selected_model()}`")
    pres = pd.DataFrame([{"Preset": v["label"], "Modelo": v["model"], "US$/1M tokens (entrada / saída)": v["preco"], "Uso": v["uso"]}
                         for v in ai["presets"].values()])
    ds.data_table(pres, key="cfg_presets", source="config/ai.yaml (preços conferidos na data do arquivo)",
                  column_config={"Uso": st.column_config.TextColumn(width="large")})

with t_vis:
    cfg = tomllib.loads((cache.ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    st.markdown(f"**Tema ativo agora:** {theme.mode()}. Troque no menu ⋮ do topo → Settings → Theme (Light / Dark / Sistema). "
                "O padrão do app segue o sistema; cores em `pwass/ui/tokens.py` e `.streamlit/config.toml`.")
    st.markdown("##### Faixa de mercado do Painel")
    st.caption("Edite `config/painel.yaml` para trocar os itens. Classes de risco do regime: " + ", ".join(cache.config("painel")["classes_risco"]))
    ds.data_table(pd.DataFrame(cache.config("painel")["faixa"]), key="cfg_faixa", source="config/painel.yaml")

with t_par:
    r = sw["risco"]
    st.markdown("##### Parâmetros de risco do Laboratório (`config/swing.yaml`)")
    ds.kpi_row([ds.kpi("Capital do laboratório", f"US$ {num(r['capital_laboratorio_usd'], 0)}", source="config/swing.yaml"),
                ds.kpi("Risco por operação", pct(r["risco_por_operacao"], 1, False), source="config/swing.yaml"),
                ds.kpi("Stop inicial", f"{r['multiplo_atr_stop']:g}× ATR", source="config/swing.yaml"),
                ds.kpi("Posição máxima", pct(r["posicao_maxima"], 0, False), source="config/swing.yaml"),
                ds.kpi("Custo por lado", pct(r["custo_por_lado"], 2, False), source="config/swing.yaml")])
    st.caption(f"Alvos em R: {', '.join(f'{x:g}R' for x in r['alvos_em_r'])}. Estratégia padrão: {sw['padrao']}. "
               "Alterar esses números muda os backtests; a regressão numérica (`tests/test_regressao.py`) vai acusar.")
    s = cache.config("watchlist").get("strategy", {})
    st.markdown("##### Limites do Satélite (`config/watchlist.yaml`)")
    ds.kpi_row([ds.kpi("Núcleo-alvo", f"{s.get('core_target_pct', ['—'])[0]}–{s.get('core_target_pct', ['—', '—'])[-1]}%", source="config/watchlist.yaml"),
                ds.kpi("Teto do Satélite", f"{s.get('satellite_max_pct')}%", source="config/watchlist.yaml"),
                ds.kpi("Por ativo", f"{s.get('single_position_max_pct')}%", source="config/watchlist.yaml"),
                ds.kpi("Cripto", f"{s.get('crypto_max_pct')}%", source="config/watchlist.yaml"),
                ds.kpi("Margem de segurança", f"{s.get('margin_of_safety_pct')}%", source="config/watchlist.yaml")])
    sc = cache.config("score")["validacao"]
    st.markdown("##### Score de qualidade do sinal")
    st.markdown(f"Score **{'ativo' if sc['mostrar'] else 'desligado'}** — validação de {sc['data_dados']}: " + "; ".join(sc["motivos"]) +
                ". Detalhes em `docs/redesign/SCORE.md`; atualize com `python scripts/validar_score.py`.")

with t_fontes:
    st.markdown("##### Status das fontes")
    st.caption("Cada fonte recebe uma chamada curta. Falha de uma não afeta as outras. O resultado vale para este momento.")
    if st.button("Testar fontes agora", type="primary", icon=":material/network_check:", key="cfg_testar"):
        with st.spinner("Consultando as fontes..."):
            st.session_state["status_fontes"] = (status.checar(status.testes_padrao(settings.sec_user_agent())),
                                                 pd.Timestamp.now(tz=ds.BRT).strftime("%d/%m/%Y %H:%M BRT"))
    if "status_fontes" in st.session_state:
        res, quando = st.session_state["status_fontes"]
        df = pd.DataFrame(res).assign(Situação=lambda d: d["ok"].map({True: "ok", False: "falha"}))[["fonte", "Situação", "ultimo_dado", "latencia_s", "erro"]]
        ds.data_table(df.rename(columns={"fonte": "Fonte", "ultimo_dado": "Último dado", "latencia_s": "Latência (s)", "erro": "Erro"}),
                      key="cfg_status", source="teste ao vivo", asof=quando)
    else:
        ds.empty_state("Fontes ainda não testadas nesta sessão", "Clique em 'Testar fontes agora'.")
    st.markdown("##### Armazenamento de dados do usuário")
    stg = cache.store()
    ds.chips([f"Backend: {stg.backend}"])
    try:
        cont = pd.DataFrame([{"Coleção": c, "Itens": len(stg.list(c))} for c in ("watchlists", "alertas", "diario", "analises_ia", "filtros_salvos")])
        ds.data_table(cont, key="cfg_store")
    except Exception as e:  # noqa: BLE001
        ds.error_state("Não foi possível ler o armazenamento", str(e))
    if stg.backend == "local":
        st.caption("Local: arquivos em `data/*.local.json`, fora do git. Na nuvem somem a cada reinício; para persistir, configure "
                   "SUPABASE_URL e SUPABASE_KEY nos secrets (SQL em docs/redesign/supabase.sql).")

with t_sobre:
    ver = tomllib.loads((cache.ROOT / "pyproject.toml").read_text(encoding="utf-8")).get("project", {}).get("version", "?")
    st.markdown(f"**IDEAS CAPITAL assets** · versão {ver} · redesign v5")
    st.markdown("Ferramenta pessoal de Renan Cotta (uso exclusivo). Sinais e análises são gerados por regras e por IA para apoiar a leitura "
                "do mercado. **A decisão, o aporte e o risco são exclusivamente do usuário.** Resultados de backtest são simulações, "
                "têm viés de sobrevivência e não garantem resultado futuro. Dados do Yahoo Finance, FRED, Banco Central, Tesouro e SEC "
                "podem ter atraso ou erro.")
    st.markdown("Gráfico de preços: Lightweight Charts™ da TradingView (licença Apache-2.0).")
