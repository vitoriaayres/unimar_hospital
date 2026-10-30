# Planejamento original (histórico)

Estes três documentos foram escritos **antes** da implementação, como especificação inicial:

| Arquivo | Conteúdo |
|---|---|
| `SPEC.md` | Objetivo, stack, estrutura de pastas e critérios de sucesso planejados |
| `ARCHITECTURE.md` | Arquitetura alvo, modelo de dados e ADRs |
| `ML_PIPELINE.md` | Pipeline de ML planejado (dados sintéticos, features, treino, monitoramento) |

Eles ficam aqui como registro do planejamento. O que foi **realmente implementado** está em
[`docs/`](../), e alguns itens planejados ficaram de fora ou foram simplificados:

| Planejado | O que foi feito | Motivo |
|---|---|---|
| Celery + Redis para tarefas assíncronas | Pipeline de ML rodado por script (`ml/run_pipeline.py`) | Previsões são geradas em lote; não houve necessidade de fila |
| MLflow + MinIO para rastrear experimentos | Métricas e relatório salvos em JSON (`ml/data/*_production.json`) | Um único modelo em produção; JSON é suficiente e mais simples de rodar |
| Optuna para hiperparâmetros | Parâmetros fixos + early stopping + blend ajustado na validação | Ganho marginal frente ao custo de tempo/memória |
| Vários modelos (XGBoost, Prophet, LSTM) | LightGBM | Melhor relação acurácia × custo nos testes |
| Monitoramento de drift | Não implementado | Fora do escopo do semestre |
| Deploy em nuvem (Kubernetes/Terraform) | Docker Compose local | Projeto acadêmico, roda na máquina local |
