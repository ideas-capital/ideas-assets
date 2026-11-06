# Instalação, publicação e manutenção

## Onde rodar: decisão

| Opção | Para quê | Prós | Contras |
|---|---|---|---|
| **No seu computador** (recomendado como principal) | Uso diário | Rápido, privado, sem limites, nada dorme | Só funciona com o PC ligado |
| **Streamlit Community Cloud** (privado) | Abrir no celular ou fora de casa | Grátis, link fixo, acesso só por convite | "Dorme" após 12 h sem uso (acorda em ~30 s); 1 app privado por conta |
| **GitHub (RADAR.md)** | Consulta rápida no celular | Atualiza sozinho todo dia útil | Só leitura, sem gráficos interativos |

O recomendado é usar as três: o computador para trabalhar, a nuvem para consultar fora de casa e o RADAR.md para olhar rápido.

## 1. Rodar no computador (Windows)

1. Instale o **Python 3.12** em [python.org](https://www.python.org/downloads/) e marque *"Add Python to PATH"*.
2. Descompacte o projeto numa pasta (ex.: `C:\Projetos\ideas-capital`).
3. Dê duplo clique em **`rodar.bat`**. Na primeira vez ele cria o ambiente e instala tudo (~2 min).
4. O navegador abre em `http://localhost:8501`. Para fechar, feche a janela preta.

No Mac/Linux: `chmod +x rodar.sh && ./rodar.sh`.

**Chaves de IA no computador:** copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha. Esse arquivo fica só na sua máquina (está no `.gitignore`).

## 2. Chaves de IA (escolha uma ou as duas)

| Provedor | Onde criar | Custo | Uso no app |
|---|---|---|---|
| **OpenRouter** | openrouter.ai → *Keys* (coloque US$ 5–10 em *Credits* e defina um limite na chave) | Centavos por análise | Todos os modelos: Claude, Gemini, GPT, Perplexity |
| **Google AI Studio** | aistudio.google.com/apikey | Grátis no Gemini Flash | Modelos com prefixo `gemini:`. Na camada grátis o Google pode usar o conteúdo: mande só dados de mercado |
| **Ollama** (opcional) | ollama.com → `ollama pull qwen3:8b` | Grátis, local | Modelos com prefixo `ollama:` |

Os modelos de cada função ficam em `config/ai.yaml` (presets, debate e comitê).

## 3. Subir para o GitHub (repositório privado)

O projeto já vem com um commit inicial. Crie um repositório **privado** vazio no GitHub (ex.: `ideas-capital`) e rode, dentro da pasta:

```bash
git remote add origin https://github.com/SEU_USUARIO/ideas-capital.git
git branch -M main
git push -u origin main
```

Daqui em diante, cada mudança: `git add . && git commit -m "descrição" && git push`.

**Trabalhar com o Claude no repositório:** conecte o repositório numa sessão do Claude (Claude Code na web ou no desktop). O arquivo `CLAUDE.md` na raiz explica a arquitetura e as convenções, para qualquer sessão continuar de onde parou.

## 4. Publicar na web só para você (Streamlit Community Cloud)

1. Entre em **share.streamlit.io** com a conta do GitHub.
2. *Create app* → escolha o repositório → branch `main` → arquivo `app.py`.
3. Em *Advanced settings*, escolha **Python 3.12**.
4. Em *Settings → Secrets*, cole o conteúdo do seu `secrets.toml` (chaves, `PWASS_USAR_CHAVE_DO_SERVIDOR = "true"` e `SEC_USER_AGENT`).
5. Em *Settings → Sharing*, deixe **"Only specific people can view this app"** e convide só o seu e-mail. Com o repositório privado, o app já nasce privado.
6. Salve o link nos favoritos do celular.

## 5. Automação no GitHub Actions

Ative em *Settings → Actions → General → Workflow permissions →* **Read and write**.

| Workflow | Quando | O que faz |
|---|---|---|
| `radar-diario.yml` | Dias úteis, 19h37 (Brasília) | Atualiza `RADAR.md` e `site/index.html` |
| `relatorio-mensal.yml` | Dia 1, 10h17 | Grava `relatorios/AAAA-MM.md` com sinais, regime e scanner |

Para o relatório mensal incluir comentário da IA, crie o secret `OPENROUTER_API_KEY` em *Settings → Secrets and variables → Actions*. Para rodar na hora: *Actions → escolha o workflow → Run workflow*.

## 6. Configurar sem mexer em código

| Arquivo | O que muda |
|---|---|
| `config/swing.yaml` | Capital do laboratório, risco por operação (1%), custos, stop em ATR, alvos, regras das 3 estratégias, universo do radar de sinais |
| `config/estrategias.yaml` | Carteiras-modelo do Núcleo e qual é a padrão |
| `config/radar.yaml` | Ativos e limites do Radar de ativos |
| `config/universe.yaml` | Universo e pesos do Scanner QVM |
| `config/watchlist.yaml` | Zonas de entrada (ex.: NVDA 180–195) e limites do Satélite |
| `config/ai.yaml` | Modelos de IA por função e o comitê |

## 7. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| "Sem dados para …" ou tabela vazia | Yahoo limitou requisições | Espere alguns minutos; o app guarda em cache por 1 h |
| Erro 401 na IA | Chave errada ou sem créditos | Confira a chave e os créditos no provedor |
| Gráfico não aparece | Componente não instalado | `pip install -r requirements.txt` de novo |
| App na nuvem demora | Estava "dormindo" | Normal: ~30 s na primeira abertura do dia |
| Tema não troca | Cache do navegador | Recarregue a página (F5) |

## 8. Testes

```bash
pytest
```
31 testes cobrem o motor de swing (execução na abertura seguinte, custos, stop), estratégias, backtests, valuation, radar e roteamento de IA.
