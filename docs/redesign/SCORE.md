# Score de qualidade do sinal — metodologia e validação

Dados: Yahoo Finance, candles diários até 07/11/2026; universo do Laboratório (35 ativos), 3 estratégias, custo de 0,10% por lado, execução na abertura seguinte. Gerado em 07/11/2026 por `scripts/validar_score.py`.

## Metodologia
Cada operação do backtest recebe 7 componentes (0–1) calculados **só com dados até o fechamento do sinal**:
- **Tendência (preço vs MM200)**
- **Momento (retorno 63 dias)**
- **Volume relativo**
- **Volatilidade baixa (ATR %)**
- **Confirmação de outras estratégias**
- **Regime (SPY > MM200)**
- **Histórico da regra no ativo**

Calibração: peso de cada componente ∝ max(0, correlação de Spearman com o retorno da operação), usando só sinais **até 2019**. Faixas (baixa/média/alta) = tercis dos scores do treino. Teste: sinais **de 2020 em diante**, nunca vistos na calibração. Critérios para MOSTRAR o score: correlação fora da amostra > 0, p < 0,05 (permutação, 2000 sorteios), faixa alta com retorno médio maior que o da baixa e ≥ 30 operações em cada.

## Resultado
Operações: treino 772 · teste 2545.

Pesos calibrados: Tendência (preço vs MM200) 23%, Momento (retorno 63 dias) 52%, Volume relativo 0%, Volatilidade baixa (ATR %) 0%, Confirmação de outras estratégias 25%, Regime (SPY > MM200) 0%, Histórico da regra no ativo 0%.

Correlação (Spearman) fora da amostra: **+0,038** (p = 0,022); no treino: +0,029.

### Faixas no treino (2016–2019)
| Faixa | Operações | Taxa de acerto | Retorno médio | Profit factor |
|---|---|---|---|---|
| Baixa | 258 | 51% | +0,58% | 1,36 |
| Média | 257 | 47% | +0,15% | 1,10 |
| Alta | 257 | 53% | +3,20% | 2,65 |

### Faixas no TESTE (2020 em diante)
| Faixa | Operações | Taxa de acerto | Retorno médio | Profit factor |
|---|---|---|---|---|
| Baixa | 754 | 59% | +2,80% | 2,74 |
| Média | 633 | 58% | +3,16% | 3,07 |
| Alta | 1158 | 60% | +2,55% | 2,34 |

## Decisão
**O score NÃO é mostrado no app.** faixa alta não rendeu mais que a baixa no teste.
No lugar dele, o app mostra o checklist de fatores a favor e contra (regras determinísticas, `engine/fatores.py`).

## Limitações
- Universo atual com viés de sobrevivência; amostra de ~10 anos e poucos regimes (2020 e 2022 dominam o teste).
- Operações de um mesmo ativo/dia não são independentes; o p-valor é otimista.
- Resultado passado não garante resultado futuro. Rodar de novo com mais dados pode mudar a decisão.
