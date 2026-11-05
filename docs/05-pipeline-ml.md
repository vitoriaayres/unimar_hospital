# Pipeline de ML

Prevê o **consumo total dos próximos 7 dias** de cada medicamento. O código fica em `backend/ml/`
e roda por script, a partir de `backend/`, com o Postgres no ar.

## Etapas

```mermaid
flowchart LR
    CFG[data_generation.yaml] --> GEN[generate_data.py<br/>base fictícia]
    GEN --> RESET[full_reset.py<br/>carrega no Postgres]
    RESET --> DB[(PostgreSQL)]
    DB --> FEAT[features.py<br/>97 variáveis]
    FEAT --> TRAIN[train.py<br/>LightGBM + validação]
    TRAIN --> MODEL[model_production.pkl<br/>+ relatório]
    MODEL --> PRED[predict.py<br/>previsão de 7 dias]
    DB --> PRED
    PRED --> DB
    MODEL --> API[API / telas]
    DB --> API
```

| # | Script | O que faz | Peso |
|---|---|---|---|
| 1 | `ml/generate_data.py` | Gera a base fictícia em `ml/data/synthetic/` (config: `ml/config/data_generation.yaml`) | médio |
| 2 | `ml/full_reset.py` | **Apaga o banco**, recria as tabelas (Alembic) e carrega a base fictícia; dá códigos de barras aos produtos | médio |
| 3 | `ml/ajustar_estoque.py --aplicar` | Recalcula níveis e saldos de estoque a partir do consumo | leve |
| 4 | `ml/run_pipeline.py` | Roda `features.py` → `train.py` → `predict.py` | **pesado** (treino) |
| 5 | `ml/ajustar_estoque.py --alertas` | Refaz os alertas de falta e de vencimento | leve |
| 6 | `ml/report.py` | Gera os gráficos do modelo em `docs/imagens/` | leve |

Atalhos que **não treinam** (servem depois de um `full_reset.py`, com o modelo já salvo):

| Script | O que faz |
|---|---|
| `ml/predict.py` | Refaz as previsões de 7 dias de todos os produtos (arquivo + tabela `predictions`) |
| `ml/build_report.py` | Refaz o relatório da tela **Modelo** a partir do modelo e do teste salvos |
| `ml/barcodes.py` | Atribui códigos EAN-13 fictícios (prefixo 789) aos produtos sem código |

## Base fictícia

- **500 medicamentos** em 10 categorias, 12 almoxarifados, consumo diário por setor (UTI,
  Emergência, Enfermaria, Ambulatório) de **jan/2021 a out/2026**.
- O consumo segue padrões realistas: sazonalidade anual por classe (ex.: broncodilatadores no
  inverno), feriados nacionais, fim de semana, ruído e picos ocasionais.
- Estoque, lotes, validades, pedidos de compra e alertas são simulados junto com o consumo.

**Limitação conhecida:** o gerador define o estoque máximo como 2,5 dias de consumo
(`max_stock_multiplier: 2.5`), o que marcaria todos os produtos com risco de falta. Depois de
gerar os dados, rode `ml/ajustar_estoque.py` (veja [Política de estoque](#política-de-estoque)).

## Variáveis do modelo (97)

Montadas por `ml/features.py`, por produto e dia:

| Grupo | Exemplos |
|---|---|
| Consumo passado | consumo de 1, 2, 7, 14, 30 dias atrás; diferenças e razões entre eles |
| Médias móveis | média, desvio, mínimo e máximo de 7, 14 e 30 dias |
| Histórico total | média e desvio desde o início |
| Calendário | dia da semana, dia do mês, mês (também em seno/cosseno) |
| Eventos | feriados e janelas sazonais |
| Anomalias | pico em relação à média, volatilidade |
| Produto | categoria, custo, prazo de reposição |

## Treino

- **Algoritmo:** LightGBM, treinado em escala `log1p` (reduz o peso dos produtos de alto giro).
- **Divisão temporal, sem vazamento de futuro:** o teste é o último ~20% do período; a validação,
  os 180 dias anteriores ao teste. O modelo nunca vê datas posteriores às que prevê.
- **Parada antecipada** na validação (melhor iteração: 108).
- **Combinação com o método atual:** a previsão final é `0,75 × modelo + 0,25 × média de 7 dias`.
  O peso 0,75 foi escolhido na validação, não no teste.

## Resultados

Modelo treinado em 05/11/2026. Teste de **30/08/2025 a 22/10/2026** (209.497 previsões).
O **método atual** é o que a farmácia usa hoje: média de consumo dos últimos 7 dias × 7.

| Métrica | Modelo | Método atual |
|---|---|---|
| **WAPE** (erro total relativo) | **14,4%** | 19,1% |
| MAPE (erro médio por previsão) | 14,1% | 19,2% |

**O modelo erra 4,7 pontos percentuais a menos, 25% menos erro que o método atual.**

| Faixa de giro | WAPE do modelo |
|---|---|
| Baixo giro | 14,2% |
| Médio giro | 13,7% |
| Alto giro | 14,6% |

### Erro por categoria

O modelo ganha do método atual em **todas** as categorias.

| Categoria | Modelo | Método atual |
|---|---|---|
| Antitrombóticos | 13,5% | 17,7% |
| Analgésicos | 13,5% | 18,2% |
| Inibidores da ECA | 13,8% | 18,1% |
| Psicolépticos | 13,9% | 18,6% |
| Outros | 14,0% | 19,1% |
| Inibidores de bomba (IBP) | 14,2% | 19,5% |
| Betabloqueadores | 14,3% | 19,2% |
| Corticoides | 14,6% | 19,1% |
| Antibióticos | 15,1% | 19,6% |
| Broncodilatadores | 15,6% | 21,2% |

### Variáveis mais importantes

| Variável | Importância |
|---|---|
| Média móvel de 7 dias | 70,5% |
| Média móvel de 14 dias | 14,5% |
| Média móvel de 30 dias | 7,0% |
| Média histórica | 1,6% |
| Dia do mês | 0,7% |

O modelo aprendeu o que faz sentido: o consumo recente pesa mais, e o calendário ajusta os picos.

### Política de estoque

Os níveis de estoque do gerador sintético cobriam só cerca de 2 dias de consumo, o que
marcava 100% dos produtos com risco de falta. `ml/ajustar_estoque.py` recalcula esses níveis
a partir do consumo registrado, sem alterar o histórico:

- **Estoque mínimo (segurança):** `z × √(L × σd² + d² × σL²)`, com nível de serviço de 95%.
- **Ponto de pedido:** `d × L + estoque de segurança`.
- **Estoque máximo:** `ponto de pedido + d × 7 dias` (período de revisão).

Aqui, `d` é o consumo médio diário dos últimos 90 dias, `σd` o desvio desse consumo, `L` o prazo
de entrega e `σL` o desvio do prazo. O saldo atual vem da reprodução dos últimos 180 dias de
consumo real sob essa política, com prazos de entrega sorteados e semente fixa.

O gerador deixa todo o saldo em lotes de validade longa. Para a base simulada ter vencimentos
reais, o script dá validades de 12 a 85 dias a 8 produtos com estoque folgado.

Variáveis de estoque (mínimo, máximo, saldo, lotes e validade) não entram no modelo: são uma
foto de hoje, não descrevem o passado e vazariam o período de teste.

### Gráficos

Gerados por `ml/report.py` em `docs/imagens/` (os mesmos dados da tela **Modelo**):

| Arquivo | Mostra |
|---|---|
| `modelo-real-vs-previsto.png` | Curvas do consumo real, do modelo e do método atual no período de teste |
| `modelo-vs-metodo-atual.png` | Erro do modelo × método atual |
| `modelo-erro-por-categoria.png` | Erro por categoria |
| `modelo-importancia-variaveis.png` | Variáveis mais importantes |

No gráfico real × previsto, cada ponto soma os alvos de 7 dias de todos os produtos naquela
semana; serve para comparar as curvas entre si, não como consumo semanal absoluto.

![Real × previsto](imagens/modelo-real-vs-previsto.png)

![Erro por categoria](imagens/modelo-erro-por-categoria.png)

## Como a previsão chega ao sistema

1. `predict.py` calcula, para cada produto, a previsão dos próximos 7 dias a partir do último dia
   com dados e grava em `ml/data/predictions.parquet` e na tabela `predictions`.
2. A API usa essa previsão no Dashboard (risco de falta), na tela **Previsões** e no detalhe do
   produto, onde ela é distribuída por dia, com faixa esperada de ±20%.
3. O relatório da tela **Modelo** vem de `ml/data/model_report_production.json`.

Depois de recriar o banco (`full_reset.py`), os produtos ganham IDs novos: rode `predict.py` de
novo, senão as previsões não aparecem.
